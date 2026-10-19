/**
 * AERIS: sign-in with Africa CDC Microsoft 365 accounts (see MicrosoftAuthService).
 *
 * Active AERIS user  -> signed in, same session set-up as AuthController.handleLogin.
 * Unknown email      -> pending (inactive) account created from the Microsoft profile, admins notified.
 * Inactive user      -> "awaiting approval" message.
 * Privileges always come from the roles an AERIS admin assigns; Microsoft grants none.
 **/
package org.pih.warehouse.user

import org.pih.warehouse.auth.MicrosoftAuthService
import org.pih.warehouse.auth.MicrosoftAuthService.MicrosoftAuthException
import org.pih.warehouse.auth.UserSignupEvent
import org.pih.warehouse.core.User

class MicrosoftAuthController {

    static final long MAX_FLOW_AGE_MS = 10 * 60 * 1000L

    static allowedMethods = [signIn: "GET", callback: "GET"]

    MicrosoftAuthService microsoftAuthService
    def grailsApplication

    def signIn() {
        if (!microsoftAuthService.enabled) {
            flash.message = warehouse.message(code: 'aeris.login.microsoft.unavailable')
            redirect(controller: 'auth', action: 'login')
            return
        }
        try {
            Map authRequest = microsoftAuthService.buildAuthorizationRequest(callbackUrl())
            session.microsoftSignIn = [state: authRequest.state, nonce: authRequest.nonce, verifier: authRequest.verifier,
                                       issuedAt: authRequest.issuedAt, browserTimezone: params.tz]
            redirect(url: authRequest.url)
        } catch (MicrosoftAuthException e) {
            log.error("Microsoft sign-in could not start: ${e.message}", e)
            flash.message = warehouse.message(code: 'aeris.login.microsoft.unavailable')
            redirect(controller: 'auth', action: 'login')
        }
    }

    def callback() {
        Map pending = session.microsoftSignIn as Map
        session.removeAttribute('microsoftSignIn')  // one use only

        if (params.error) {
            log.warn("Microsoft sign-in returned ${params.error}: ${params.error_description}")
            flash.message = warehouse.message(code: 'aeris.login.microsoft.cancelled')
            redirect(controller: 'auth', action: 'login')
            return
        }
        if (!pending || !params.state || params.state != pending.state ||
                System.currentTimeMillis() - (pending.issuedAt as long) > MAX_FLOW_AGE_MS) {
            log.warn("Microsoft sign-in callback with missing, mismatched or expired state")
            flash.message = warehouse.message(code: 'aeris.login.microsoft.expired')
            redirect(controller: 'auth', action: 'login')
            return
        }

        Map identity
        try {
            identity = microsoftAuthService.completeSignIn(params.code as String, callbackUrl(), pending)
        } catch (MicrosoftAuthException e) {
            log.warn("Microsoft sign-in refused (${e.reason}): ${e.message}")
            flash.message = e.reason == 'domain' ?
                    warehouse.message(code: 'aeris.login.microsoft.domain', args: [microsoftAuthService.allowedEmailDomains.join(', ')]) :
                    warehouse.message(code: 'aeris.login.microsoft.failed')
            redirect(controller: 'auth', action: 'login')
            return
        }

        User user = User.find("from User u where lower(u.email) = :email or lower(u.username) = :email",
                [email: identity.email])
        if (!user) {
            if (!microsoftAuthService.createPendingAccounts) {
                flash.message = warehouse.message(code: 'aeris.login.microsoft.noAccount', args: [identity.email])
                redirect(controller: 'auth', action: 'login')
                return
            }
            user = createPendingUser(identity)
            flash.message = user ?
                    warehouse.message(code: 'aeris.login.microsoft.pending', args: [identity.email]) :
                    warehouse.message(code: 'aeris.login.microsoft.failed')
            redirect(controller: 'auth', action: 'login')
            return
        }
        if (!user.active) {
            flash.message = warehouse.message(code: 'auth.accountRequestUnderReview.message')
            redirect(controller: 'auth', action: 'login')
            return
        }

        // Signed in. New session id against session fixation, then the same set-up as a password login.
        Object targetUri = session.targetUri
        request.changeSessionId()
        String tz = user.timezone ?: pending.browserTimezone
        session.timezone = TimeZone.getTimeZone(tz ?: "UTC")
        session.user = user
        session.userName = user.username
        if (user.warehouse && user.rememberLastLocation) {
            session.warehouse = user.warehouse
        }
        log.info("User ${user.username} signed in with Microsoft")
        if (targetUri) {
            session.targetUri = null
            redirect(uri: targetUri)
            return
        }
        redirect(controller: 'dashboard', action: 'index')
    }

    private String callbackUrl() {
        String configured = microsoftAuthService.redirectUri
        return configured ?: createLink(controller: 'microsoftAuth', action: 'callback', absolute: true).toString()
    }

    private User createPendingUser(Map identity) {
        User.withTransaction { status ->
            // Unusable random password: these accounts sign in through Microsoft only.
            String password = (UUID.randomUUID().toString() + UUID.randomUUID().toString()).encodeAsPassword()
            User user = new User(username: identity.email, email: identity.email,
                    firstName: identity.firstName, lastName: identity.lastName,
                    password: password, passwordConfirm: password, active: Boolean.FALSE)
            if (!user.save(flush: true)) {
                log.error("Could not create pending account for ${identity.email}: ${user.errors}")
                status.setRollbackOnly()
                return null
            }
            log.info("Pending AERIS account created for ${identity.email} after Microsoft sign-in")
            // Same notifications as a signup: AERIS admins are told an account awaits approval.
            grailsApplication.mainContext.publishEvent(new UserSignupEvent(user, [:]))
            return user
        }
    }
}
