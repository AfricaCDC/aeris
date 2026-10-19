"""Make AERIS work without internet: copy every CDN script/stylesheet the GSP views use into the app.

For each external .js/.css referenced in grails-app/views, download it (and the fonts/images its CSS
points to) under src/main/webapp/vendor/<host>/<path>, then rewrite the view to load
${request.contextPath}/static/vendor/<host>/<path> instead. Safe to re-run (e.g. after an upstream upgrade).

Usage, from the repository root:
    python -I aeris/tools/vendor_cdn.py            # download + rewrite
    python -I aeris/tools/vendor_cdn.py --check    # list remaining external asset references, exit 1 if any
"""
import pathlib
import re
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path.cwd()
VIEWS = ROOT / "grails-app" / "views"
VENDOR = ROOT / "src" / "main" / "webapp" / "vendor"
LOCAL_PREFIX = "${request.contextPath}/static/vendor/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# Asset references: scripts and stylesheets on CDNs (http:, https: or protocol-relative).
ASSET = re.compile(
    r"""(?:https?:)?//(?P<host>(?:cdnjs\.cloudflare\.com|cdn\.jsdelivr\.net|code\.jquery\.com|netdna\.bootstrapcdn\.com|"""
    r"""use\.fontawesome\.com|ajax\.googleapis\.com|ajax\.aspnetcdn\.com|cdn\.datatables\.net|yui\.yahooapis\.com|"""
    r"""fonts\.googleapis\.com))(?P<path>/[^"'\s<>)]+)""")
CSS_URL = re.compile(r"""url\(\s*(['"]?)(?P<ref>[^'")]+)\1\s*\)""")


def local_rel(host: str, path_and_query: str) -> str:
    """vendor-relative path; query strings (combo loaders, font css) become part of a safe file name."""
    parsed = urllib.parse.urlsplit(path_and_query)
    path = parsed.path.lstrip("/")
    if parsed.query:
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", parsed.query)[:80]
        ext = ".css" if ("css" in path or "css" in parsed.query and "fonts.googleapis" in host) else ".js"
        if host == "fonts.googleapis.com":
            ext = ".css"
        path = f"{path.rstrip('/') or 'index'}__{stem}{ext}"
    return f"{host}/{path}"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def download(url: str, rel: str, seen: set) -> None:
    if rel in seen:
        return
    seen.add(rel)
    dest = VENDOR / rel
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = fetch(url)
        dest.write_bytes(data)
        print(f"  got {rel} ({len(data):,} B)")
    if dest.suffix == ".css":
        localize_css(url, dest, seen)


def localize_css(css_url: str, dest: pathlib.Path, seen: set) -> None:
    """Fetch what a stylesheet points to; rewrite absolute URLs to relative local paths."""
    text = dest.read_text(encoding="utf-8", errors="surrogateescape")

    def repl(m):
        ref = m.group("ref").strip()
        if ref.startswith(("data:", "#")):
            return m.group(0)
        target = urllib.parse.urljoin(css_url, ref)
        parts = urllib.parse.urlsplit(target)
        if not parts.netloc:
            return m.group(0)
        target_rel = f"{parts.netloc}/{parts.path.lstrip('/')}"
        try:
            download(urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")), target_rel, seen)
        except Exception as e:  # a missing legacy font variant should not stop the whole run
            print(f"  ! {target}: {e}")
            return m.group(0)
        if ref.startswith(("http:", "https:", "//")):
            new = pathlib.PurePosixPath(
                *([".."] * (len(pathlib.PurePosixPath(dest.relative_to(VENDOR).as_posix()).parent.parts)))
            ) / target_rel
            suffix = (f"?{parts.query}" if parts.query else "") + (f"#{parts.fragment}" if parts.fragment else "")
            return f"url({m.group(1)}{new.as_posix()}{suffix}{m.group(1)})"
        return m.group(0)

    new_text = CSS_URL.sub(repl, text)
    if new_text != text:
        dest.write_text(new_text, encoding="utf-8", errors="surrogateescape")


def views():
    return sorted(VIEWS.rglob("*.gsp"))


def check() -> int:
    left = [(p, m.group(0)) for p in views() for m in ASSET.finditer(p.read_text(encoding="utf-8", errors="ignore"))]
    for p, u in left:
        print(f"{p.relative_to(ROOT)}: {u}")
    print(f"{len(left)} external asset reference(s) left")
    return 1 if left else 0


def main() -> int:
    seen: set = set()
    for gsp in views():
        raw = gsp.read_bytes()
        text = raw.decode("utf-8")
        if not ASSET.search(text):
            continue
        print(gsp.relative_to(ROOT))

        def to_local(m):
            rel = local_rel(m.group("host"), m.group("path"))
            try:
                download(f"https://{m.group('host')}{m.group('path')}", rel, seen)
            except Exception as e:  # dead upstream link: leave it, --check reports it
                print(f"  ! not available, left as is: {m.group(0)} ({e})")
                return m.group(0)
            return LOCAL_PREFIX + rel

        gsp.write_bytes(ASSET.sub(to_local, text).encode("utf-8"))
    return check()


if __name__ == "__main__":
    sys.exit(check() if "--check" in sys.argv else main())
