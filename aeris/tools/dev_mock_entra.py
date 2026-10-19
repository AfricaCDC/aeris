"""DEVELOPMENT ONLY - a stand-in for Microsoft Entra ID, to test AERIS "Sign in with Microsoft" locally.
Never point a production AERIS at it: it signs in whoever types an email.

It speaks the same OpenID Connect as Entra (discovery, authorize with PKCE, token, JWKS; RS256 ID tokens
with tid/oid/email claims), so the AERIS code runs unchanged. Needs: pip install pyjwt cryptography

    python -I aeris/tools/dev_mock_entra.py            # listens on :8099

Then start AERIS (aeris/docker) with, in .env:
    AERIS_ENTRA_ENABLED=true
    AERIS_ENTRA_TENANT_ID=00000000-0000-0000-0000-0000000000aa
    AERIS_ENTRA_CLIENT_ID=aeris-dev
    AERIS_ENTRA_CLIENT_SECRET=dev-secret
    AERIS_ENTRA_AUTHORITY=http://host.docker.internal:8099/aeris-dev/v2.0
    AERIS_ENTRA_ALLOW_HTTP=true
"""
import base64
import hashlib
import html
import json
import secrets
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

PORT = 8099
TENANT = "00000000-0000-0000-0000-0000000000aa"
CLIENT_ID, CLIENT_SECRET = "aeris-dev", "dev-secret"
SERVER_HOST = f"http://host.docker.internal:{PORT}"   # what the AERIS container calls
BROWSER_HOST = f"http://localhost:{PORT}"             # what the user's browser opens
ISSUER = f"{SERVER_HOST}/aeris-dev/v2.0"

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
KID = "aeris-dev-1"
CODES = {}  # code -> request details


def b64u(n: int) -> str:
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def jwks():
    pub = KEY.public_key().public_numbers()
    return {"keys": [{"kty": "RSA", "use": "sig", "alg": "RS256", "kid": KID, "n": b64u(pub.n), "e": b64u(pub.e)}]}


FORM = """<!doctype html><meta charset="utf-8"><title>Mock Entra ID</title>
<body style="font-family:Segoe UI,Arial;max-width:420px;margin:60px auto">
<p style="color:#a00"><b>DEVELOPMENT ONLY</b> - stand-in for Microsoft sign-in</p>
<form method="post" action="/authorize">
{hidden}
<p><label>Email<br><input name="email" value="{email}" size="40"></label></p>
<p><label>Full name<br><input name="name" value="{name}" size="40"></label></p>
<p><button name="decision" value="approve">Sign in</button> <button name="decision" value="deny">Cancel</button></p>
</form>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json", headers=None):
        data = body if isinstance(body, bytes) else (json.dumps(body) if not isinstance(body, str) else body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _form(self):
        n = int(self.headers.get("Content-Length") or 0)
        return {k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(n).decode()).items()}

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
        if url.path == "/aeris-dev/v2.0/.well-known/openid-configuration":
            return self._send(200, {
                "issuer": ISSUER,
                "authorization_endpoint": f"{BROWSER_HOST}/authorize",
                "token_endpoint": f"{SERVER_HOST}/token",
                "jwks_uri": f"{SERVER_HOST}/keys",
                "response_types_supported": ["code"], "id_token_signing_alg_values_supported": ["RS256"],
            })
        if url.path == "/keys":
            return self._send(200, jwks())
        if url.path == "/authorize":
            if q.get("client_id") != CLIENT_ID or q.get("code_challenge_method") != "S256":
                return self._send(400, "bad client_id or missing PKCE", "text/plain")
            keep = ["client_id", "redirect_uri", "state", "nonce", "code_challenge"]
            hidden = "".join(f'<input type="hidden" name="{k}" value="{html.escape(q.get(k, ""))}">' for k in keep)
            return self._send(200, FORM.format(hidden=hidden, email="prenom.nom@africacdc.org", name="Prenom Nom"), "text/html")
        self._send(404, {"error": "not_found"})

    def do_POST(self):
        f = self._form()
        if self.path == "/authorize":
            target = f["redirect_uri"]
            if f.get("decision") != "approve":
                params = {"error": "access_denied", "error_description": "User cancelled", "state": f["state"]}
            else:
                code = secrets.token_urlsafe(24)
                CODES[code] = {**f, "at": time.time()}
                params = {"code": code, "state": f["state"]}
            sep = "&" if "?" in target else "?"
            return self._send(302, b"", headers={"Location": target + sep + urllib.parse.urlencode(params)})
        if self.path == "/token":
            req = CODES.pop(f.get("code", ""), None)
            if not req or time.time() - req["at"] > 300:
                return self._send(400, {"error": "invalid_grant", "error_description": "unknown or expired code"})
            if f.get("client_id") != CLIENT_ID or f.get("client_secret") != CLIENT_SECRET:
                return self._send(401, {"error": "invalid_client"})
            if f.get("redirect_uri") != req["redirect_uri"]:
                return self._send(400, {"error": "invalid_grant", "error_description": "redirect_uri mismatch"})
            challenge = base64.urlsafe_b64encode(hashlib.sha256(f.get("code_verifier", "").encode()).digest()).rstrip(b"=").decode()
            if challenge != req["code_challenge"]:
                return self._send(400, {"error": "invalid_grant", "error_description": "PKCE verification failed"})
            now = int(time.time())
            name = req.get("name") or req["email"]
            parts = name.split(" ", 1)
            claims = {
                "iss": ISSUER, "aud": CLIENT_ID, "sub": hashlib.sha1(req["email"].encode()).hexdigest(),
                "iat": now, "nbf": now, "exp": now + 3600, "nonce": req["nonce"], "tid": TENANT,
                "oid": str(hashlib.md5(req["email"].encode()).hexdigest()), "email": req["email"],
                "preferred_username": req["email"], "name": name, "given_name": parts[0],
                "family_name": parts[1] if len(parts) > 1 else "",
            }
            token = jwt.encode(claims, KEY, algorithm="RS256", headers={"kid": KID})
            return self._send(200, {"token_type": "Bearer", "id_token": token, "access_token": "unused", "expires_in": 3600})
        self._send(404, {"error": "not_found"})

    def log_message(self, fmt, *args):
        print("mock-entra:", fmt % args)


if __name__ == "__main__":
    print(f"Mock Entra ID (DEVELOPMENT ONLY) on :{PORT}, issuer {ISSUER}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
