/**
 * AERIS: sign-in with Africa CDC Microsoft 365 (Entra ID) accounts, using OpenID Connect
 * (authorization code flow with PKCE). Microsoft only proves who the person is; what they may do
 * stays in AERIS (roles assigned by an AERIS admin).
 *
 * Settings: openboxes.auth.microsoft.* in application.yml, normally fed by AERIS_ENTRA_* environment variables.
 **/
package org.pih.warehouse.auth

import com.nimbusds.jose.JWSAlgorithm
import com.nimbusds.jose.jwk.source.JWKSource
import com.nimbusds.jose.jwk.source.RemoteJWKSet
import com.nimbusds.jose.proc.JWSVerificationKeySelector
import com.nimbusds.jose.proc.SecurityContext
import com.nimbusds.jwt.JWTClaimsSet
import com.nimbusds.jwt.proc.DefaultJWTClaimsVerifier
import com.nimbusds.jwt.proc.DefaultJWTProcessor
import grails.core.GrailsApplication
import groovy.json.JsonSlurper

import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.security.SecureRandom

class MicrosoftAuthService {

    static transactional = false

    static final int TIMEOUT_MS = 15000
    static final long METADATA_TTL_MS = 60 * 60 * 1000L

    GrailsApplication grailsApplication

    private final SecureRandom random = new SecureRandom()
    private Map metadata
    private long metadataFetchedAt
    private DefaultJWTProcessor<SecurityContext> processor

    /** Thrown for any sign-in failure; the message is safe to log, not to show verbatim. */
    static class MicrosoftAuthException extends RuntimeException {
        final String reason
        MicrosoftAuthException(String reason, String message, Throwable cause = null) {
            super(message, cause)
            this.reason = reason
        }
    }

    boolean isEnabled() {
        return asBoolean(settings.enabled) && clientId && (tenantId || settings.authority)
    }

    String getClientId() { (settings.clientId ?: '').toString().trim() }

    String getTenantId() { (settings.tenantId ?: '').toString().trim() }

    String getRedirectUri() { (settings.redirectUri ?: '').toString().trim() }

    List<String> getAllowedEmailDomains() {
        def value = settings.allowedEmailDomains
        List<String> domains = (value instanceof Collection ? value : value?.toString()?.split(',')) as List<String>
        return domains*.toString()*.trim()*.toLowerCase().findAll { it }
    }

    boolean isCreatePendingAccounts() {
        def value = settings.createPendingAccounts
        // Missing keys come back as an empty config map: default to true
        return (value == null || value instanceof Map) ? true : asBoolean(value)
    }

    /**
     * Start of the flow: returns the Microsoft URL to send the browser to, and the values
     * the callback must find again in the session.
     */
    Map buildAuthorizationRequest(String redirectUri) {
        Map md = getMetadata()
        String state = randomToken()
        String nonce = randomToken()
        String verifier = randomToken() + randomToken()
        String challenge = base64Url(MessageDigest.getInstance("SHA-256").digest(verifier.getBytes(StandardCharsets.US_ASCII)))
        Map query = [
                client_id            : clientId,
                response_type        : 'code',
                redirect_uri         : redirectUri,
                response_mode        : 'query',
                scope                : 'openid profile email',
                state                : state,
                nonce                : nonce,
                code_challenge       : challenge,
                code_challenge_method: 'S256',
                prompt               : 'select_account',
        ]
        String url = md.authorization_endpoint + '?' + formEncode(query)
        return [url: url, state: state, nonce: nonce, verifier: verifier, issuedAt: System.currentTimeMillis()]
    }

    /**
     * End of the flow: exchanges the code, verifies the ID token and returns the person's identity.
     * @return [email, firstName, lastName, objectId]
     */
    Map completeSignIn(String code, String redirectUri, Map pending) {
        Map md = getMetadata()
        Map tokenResponse = postForm(md.token_endpoint as String, [
                client_id    : clientId,
                client_secret: (settings.clientSecret ?: '').toString(),
                grant_type   : 'authorization_code',
                code         : code,
                redirect_uri : redirectUri,
                code_verifier: pending.verifier,
                scope        : 'openid profile email',
        ])
        String idToken = tokenResponse.id_token
        if (!idToken) {
            throw new MicrosoftAuthException('token', "No id_token in token response: ${tokenResponse.error ?: ''} ${tokenResponse.error_description ?: ''}")
        }

        JWTClaimsSet claims
        try {
            claims = getProcessor(md).process(idToken, null)
        } catch (Exception e) {
            throw new MicrosoftAuthException('token', "ID token rejected: ${e.message}", e)
        }
        if (claims.getStringClaim('nonce') != pending.nonce) {
            throw new MicrosoftAuthException('token', 'ID token nonce does not match this sign-in')
        }
        String tid = claims.getStringClaim('tid')
        if (tenantId && tid && !tenantId.equalsIgnoreCase(tid)) {
            throw new MicrosoftAuthException('tenant', "Token from tenant ${tid}, expected ${tenantId}")
        }

        String email = (claims.getStringClaim('email') ?: claims.getStringClaim('preferred_username') ?: '').trim().toLowerCase()
        if (!email.contains('@')) {
            throw new MicrosoftAuthException('email', 'The Microsoft account has no email address')
        }
        String domain = email.substring(email.lastIndexOf('@') + 1)
        if (allowedEmailDomains && !allowedEmailDomains.contains(domain)) {
            throw new MicrosoftAuthException('domain', "Email domain ${domain} is not allowed")
        }

        String fullName = claims.getStringClaim('name') ?: email.substring(0, email.indexOf('@'))
        String firstName = claims.getStringClaim('given_name') ?: fullName.tokenize(' ').first()
        String lastName = claims.getStringClaim('family_name') ?: (fullName.tokenize(' ').size() > 1 ? fullName.tokenize(' ').drop(1).join(' ') : '-')
        return [email: email, firstName: firstName, lastName: lastName, objectId: claims.getStringClaim('oid')]
    }

    // ---- internals ----

    private Map getSettings() {
        return (grailsApplication.config.openboxes.auth.microsoft ?: [:]) as Map
    }

    private String getAuthority() {
        String authority = (settings.authority ?: '').toString().trim()
        if (!authority) {
            authority = "https://login.microsoftonline.com/${tenantId}/v2.0"
        }
        if (!authority.startsWith('https://') && !asBoolean(settings.allowInsecureAuthority)) {
            throw new MicrosoftAuthException('config', "Authority must use https: ${authority}")
        }
        return authority.replaceAll('/+$', '')
    }

    private synchronized Map getMetadata() {
        if (metadata && System.currentTimeMillis() - metadataFetchedAt < METADATA_TTL_MS) {
            return metadata
        }
        Map md = getJson(getAuthority() + '/.well-known/openid-configuration')
        ['issuer', 'authorization_endpoint', 'token_endpoint', 'jwks_uri'].each {
            if (!md[it]) throw new MicrosoftAuthException('config', "OpenID metadata has no ${it}")
        }
        metadata = md
        metadataFetchedAt = System.currentTimeMillis()
        processor = null
        return metadata
    }

    private synchronized DefaultJWTProcessor<SecurityContext> getProcessor(Map md) {
        if (!processor) {
            JWKSource<SecurityContext> keys = new RemoteJWKSet<>(new URL(md.jwks_uri as String))
            DefaultJWTProcessor<SecurityContext> p = new DefaultJWTProcessor<>()
            p.setJWSKeySelector(new JWSVerificationKeySelector<>(JWSAlgorithm.RS256, keys))
            p.setJWTClaimsSetVerifier(new DefaultJWTClaimsVerifier<>(
                    clientId,
                    new JWTClaimsSet.Builder().issuer(md.issuer as String).build(),
                    ['sub', 'iat', 'exp', 'nonce'] as Set))
            processor = p
        }
        return processor
    }

    private Map getJson(String url) {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection()
        c.connectTimeout = TIMEOUT_MS
        c.readTimeout = TIMEOUT_MS
        c.setRequestProperty('Accept', 'application/json')
        try {
            if (c.responseCode != 200) {
                throw new MicrosoftAuthException('network', "GET ${url} returned ${c.responseCode}")
            }
            return new JsonSlurper().parse(c.inputStream, 'UTF-8') as Map
        } catch (MicrosoftAuthException e) {
            throw e
        } catch (IOException e) {
            throw new MicrosoftAuthException('network', "GET ${url} failed: ${e.message}", e)
        } finally {
            c.disconnect()
        }
    }

    private Map postForm(String url, Map form) {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection()
        c.connectTimeout = TIMEOUT_MS
        c.readTimeout = TIMEOUT_MS
        c.requestMethod = 'POST'
        c.doOutput = true
        c.setRequestProperty('Content-Type', 'application/x-www-form-urlencoded')
        c.setRequestProperty('Accept', 'application/json')
        try {
            c.outputStream.withStream { it.write(formEncode(form).getBytes(StandardCharsets.UTF_8)) }
            InputStream body = c.responseCode < 400 ? c.inputStream : c.errorStream
            Map json = body ? new JsonSlurper().parse(body, 'UTF-8') as Map : [:]
            if (c.responseCode >= 400) {
                throw new MicrosoftAuthException('token', "Token endpoint returned ${c.responseCode}: ${json.error ?: ''} ${json.error_description ?: ''}")
            }
            return json
        } catch (MicrosoftAuthException e) {
            throw e
        } catch (IOException e) {
            throw new MicrosoftAuthException('network', "POST ${url} failed: ${e.message}", e)
        } finally {
            c.disconnect()
        }
    }

    private static String formEncode(Map params) {
        params.findAll { it.value != null }.collect { k, v ->
            URLEncoder.encode(k as String, 'UTF-8') + '=' + URLEncoder.encode(v as String, 'UTF-8')
        }.join('&')
    }

    private String randomToken() {
        byte[] bytes = new byte[32]
        random.nextBytes(bytes)
        return base64Url(bytes)
    }

    private static String base64Url(byte[] bytes) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes)
    }

    private static boolean asBoolean(Object value) {
        // Values from ${ENV:default} placeholders arrive as strings: "false" must stay false.
        return value instanceof Boolean ? value : value?.toString()?.trim()?.equalsIgnoreCase('true')
    }
}
