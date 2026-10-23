<%--
  AERIS login page (replaces the upstream login box). Standalone: no layout, no external files.
  Layout follows the Ebola response's teleconsultation platform: brand panel with the DRC flag stripe, white form.
  Microsoft 365 sign-in (microsoftAuth/signIn) when enabled; the local username/password form posts the same
  fields as upstream to auth/handleLogin: username, password, targetUri, browserTimezone.
--%>
<%-- Same source as warehouse:message (session, then user, then default locale), not the browser locale --%>
<g:set var="lang" value="${grailsApplication.mainContext.getBean('localeManager').currentLocale?.language ?: 'en'}"/>
<g:set var="locales" value="${grailsApplication.config.openboxes.locale.supportedLocales ?: ['en', 'fr']}"/>
<g:set var="microsoftEnabled" value="${grailsApplication.mainContext.getBean('microsoftAuthService').enabled}"/>
<g:set var="showFormSetting" value="${grailsApplication.config.openboxes.auth.local.showForm}"/>
<g:set var="localOpen" value="${!microsoftEnabled || showFormSetting == true || showFormSetting?.toString() == 'true' || userInstance?.hasErrors()}"/>
<!doctype html>
<html lang="${lang}">
<head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>AERIS – ${warehouse.message(code: 'auth.title', default: 'Login')}</title>
    <asset:link rel="icon" href="favicon.ico" type="image/x-ico"/>
    <link rel="stylesheet" href="${request.contextPath}/static/vendor/fonts.googleapis.com/css2__family_Inter_wght_400_500_600_700_800.css"/>
    <script src="${resource(dir: 'js/', file: 'detect_timezone.js')}" type="text/javascript"></script>
    <style>
        /* Sized in rem; the root size follows the window so the card fits with a margin around it. */
        html { font-size: clamp(11px, min(0.9vw, 1.45vh), 16px); }
        :root {
            --maroon: #911936; --maroon-2: #7A1430; --maroon-3: #5C0F24; --gold: #BCA053;
            --drc-blue: #007FFF; --drc-yellow: #F7D618; --drc-red: #CE1021;
            --bg: #EEF1F5; --card: #FFFFFF; --text: #14202E; --muted: #5B6676; --line: #DCE2EA; --field: #FFFFFF;
            --error-bg: #FDEEEF; --error-line: #F3C6CC; --note-bg: #F7F1E4; --note-line: #E6D7B0;
        }
        * { box-sizing: border-box; }
        html, body { margin: 0; }
        body {
            font-family: Inter, "Segoe UI", Roboto, Arial, sans-serif; background: var(--bg); color: var(--text);
            min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 2rem;
        }
        .card {
            display: grid; grid-template-columns: 1fr 1fr; width: min(100%, 86rem); min-height: min(49rem, calc(100vh - 4rem));
            background: var(--card); border-radius: 1.6rem; overflow: hidden;
            box-shadow: 0 1.5rem 3.5rem -2rem rgba(20, 32, 46, .35), 0 0 0 1px rgba(20, 32, 46, .04);
        }
        /* Brand panel */
        .brand {
            position: relative; color: #fff; padding: 4rem 3.5rem; text-align: center;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            background: radial-gradient(110% 80% at 50% 0%, var(--maroon) 0%, transparent 70%),
                        linear-gradient(170deg, var(--maroon-2) 0%, var(--maroon-3) 100%);
        }
        .flag { position: absolute; top: 0; left: 0; right: 0; height: .5rem; display: grid; grid-template-columns: 1fr 1fr 1fr; }
        .flag i:nth-child(1) { background: var(--drc-blue); }
        .flag i:nth-child(2) { background: var(--drc-yellow); }
        .flag i:nth-child(3) { background: var(--drc-red); }
        .country { margin: 0; font-size: 1.05rem; letter-spacing: .28rem; text-transform: uppercase; color: rgba(255,255,255,.85); font-weight: 500; }
        .brand h1 { margin: 1.4rem 0 0; font-size: 4.6rem; line-height: 1; font-weight: 800; letter-spacing: .1rem; }
        .headline { margin: .9rem 0 0; font-size: 2rem; line-height: 1.25; font-weight: 700; max-width: 30rem; }
        .rule { width: 3.5rem; height: .25rem; border-radius: .2rem; background: var(--gold); margin: 1.6rem auto 0; }
        .outbreak { margin: 1.4rem 0 0; font-size: 1.3rem; color: rgba(255,255,255,.92); }
        .logo-card {
            margin-top: 3rem; background: #fff; border-radius: .9rem; padding: .9rem 1.4rem;
            box-shadow: 0 .6rem 1.6rem -.8rem rgba(0,0,0,.45);
        }
        .logo-card img { display: block; width: 15.5rem; max-width: 100%; height: auto; }
        /* Form panel */
        .form { padding: 4rem 4.2rem 3rem; display: flex; flex-direction: column; justify-content: center; }
        .form h2 { font-size: 2.6rem; margin: 0 0 1.8rem; font-weight: 600; letter-spacing: -.03rem; }
        .intro { color: var(--muted); font-size: 1.2rem; margin: -1.1rem 0 1.6rem; }
        .ms {
            width: 100%; height: 4.4rem; border-radius: 1rem; border: 1px solid var(--line); background: var(--card); color: var(--text);
            font: 600 1.25rem Inter, sans-serif; display: flex; align-items: center; justify-content: center; gap: .9rem; text-decoration: none;
        }
        .ms:hover { background: #F7F9FB; border-color: #B9C3CF; }
        .ms svg { width: 1.5rem; height: 1.5rem; }
        details.local { margin-top: 1.4rem; border-top: 1px solid var(--line); padding-top: 1rem; }
        details.local summary { cursor: pointer; color: var(--muted); font-size: 1.1rem; font-weight: 600; list-style: none; }
        details.local summary::-webkit-details-marker { display: none; }
        details.local summary::before { content: "\203A"; display: inline-block; margin-right: .5rem; transition: transform .15s; }
        details.local[open] summary::before { transform: rotate(90deg); }
        details.local.always { border-top: 0; padding-top: 0; margin-top: 0; }
        details.local.always summary { display: none; }
        .local-body { padding-top: 1rem; }
        details.local.always .local-body { padding-top: 0; }
        label { display: block; font-weight: 500; font-size: 1.3rem; margin: 0 0 .6rem; }
        .field { position: relative; margin-bottom: 1.5rem; }
        .field input {
            width: 100%; height: 4.4rem; border-radius: .9rem; border: 1px solid var(--line); background: var(--field); color: var(--text);
            font: 400 1.3rem Inter, sans-serif; padding: 0 1.4rem; outline: none; transition: border-color .15s, box-shadow .15s;
        }
        .field input[type="password"], .field input.pwd { padding-right: 3.8rem; }
        .field input::placeholder { color: #9AA4B2; }
        .field input:focus { border-color: var(--maroon); box-shadow: 0 0 0 .2rem rgba(145, 25, 54, .14); }
        .field.has-error input { border-color: var(--maroon); }
        .reveal { position: absolute; right: .7rem; top: 50%; transform: translateY(-50%); background: none; border: 0; padding: .5rem; cursor: pointer; color: var(--text); border-radius: .6rem; }
        .reveal svg { width: 1.5rem; height: 1.5rem; stroke: currentColor; fill: none; stroke-width: 1.8; display: block; }
        .forgot-row { display: flex; justify-content: flex-end; margin: -.4rem 0 1.4rem; }
        .forgot { background: none; border: 0; padding: 0; cursor: pointer; color: var(--maroon); font: 600 1.25rem Inter, sans-serif; }
        .forgot:hover { text-decoration: underline; }
        .note {
            display: none; margin: -.6rem 0 1.4rem; background: var(--note-bg); border: 1px solid var(--note-line);
            border-radius: .9rem; padding: .9rem 1.1rem; color: var(--muted); font-size: 1.1rem; line-height: 1.5;
        }
        .note.show { display: block; }
        .submit {
            width: 100%; height: 4.6rem; border: 0; border-radius: 1rem; cursor: pointer; color: #fff;
            font: 700 1.4rem Inter, sans-serif; background: var(--maroon);
            box-shadow: 0 .7rem 1.4rem -.8rem rgba(122, 20, 48, .8);
        }
        .submit:hover { background: var(--maroon-2); }
        .alert { border-radius: .9rem; padding: .9rem 1.2rem; margin: 0 0 1.4rem; font-size: 1.15rem; line-height: 1.5; background: var(--error-bg); border: 1px solid var(--error-line); }
        .alert ul { margin: 0; padding-left: 1.2rem; }
        .lang { display: flex; justify-content: center; margin-top: 2rem; }
        .lang-box {
            position: relative; display: inline-flex; align-items: center; gap: .6rem; border: 1px solid var(--line); border-radius: .9rem;
            padding: 0 1rem; height: 3.6rem; background: var(--card);
        }
        .lang-box svg { width: 1.4rem; height: 1.4rem; stroke: var(--muted); fill: none; stroke-width: 1.7; flex: none; }
        .lang-box select {
            appearance: none; -webkit-appearance: none; border: 0; background: transparent; color: var(--text);
            font: 500 1.2rem Inter, sans-serif; padding-right: 1.6rem; cursor: pointer; outline: none;
        }
        .lang-box .chev { position: absolute; right: .9rem; pointer-events: none; width: 1.1rem; height: 1.1rem; }
        .submit:focus-visible, .reveal:focus-visible, .ms:focus-visible, .forgot:focus-visible, summary:focus-visible, .lang-box:focus-within {
            outline: 3px solid var(--gold); outline-offset: 2px;
        }
        @media (max-width: 760px) {
            html { font-size: 14px; }
            body { padding: 1rem; align-items: flex-start; }
            .card { grid-template-columns: 1fr; min-height: 0; }
            .brand { padding: 2.2rem 1.5rem 1.8rem; }
            .brand h1 { font-size: 3rem; margin-top: 1rem; }
            .headline { font-size: 1.4rem; }
            .country { font-size: .8rem; letter-spacing: .18rem; }
            .outbreak { font-size: 1rem; margin-top: 1rem; }
            .logo-card { margin-top: 1.4rem; padding: .6rem 1rem; }
            .logo-card img { width: 11rem; }
            .form { padding: 1.8rem 1.4rem 1.6rem; }
            .form h2 { font-size: 2rem; margin-bottom: 1.2rem; }
        }
    </style>
</head>
<body>
<main class="card">
    <section class="brand" aria-label="AERIS">
        <div class="flag" aria-hidden="true"><i></i><i></i><i></i></div>
        <p class="country">${warehouse.message(code: 'aeris.login.country', default: 'Democratic Republic of the Congo')}</p>
        <h1>AERIS</h1>
        <p class="headline">${warehouse.message(code: 'aeris.login.headline', default: 'Ebola response stock management')}</p>
        <div class="rule" aria-hidden="true"></div>
        <p class="outbreak">${warehouse.message(code: 'aeris.login.outbreak', default: '17th Ebola Virus Disease outbreak')}</p>
        <div class="logo-card">
            <img src="${assetPath(src: 'africacdc_logo.png')}" alt="Africa CDC – Centres for Disease Control and Prevention" width="304" height="84"/>
        </div>
    </section>

    <section class="form">
        <h2>${warehouse.message(code: 'aeris.login.heading', default: 'Sign in')}</h2>
        <g:if test="${microsoftEnabled}">
            <p class="intro">${warehouse.message(code: 'aeris.login.microsoft.intro', default: 'Use your Africa CDC Microsoft 365 account.')}</p>
        </g:if>

        <g:if test="${flash.message}">
            <div class="alert" role="alert" aria-label="message">${flash.message}</div>
        </g:if>
        <g:hasErrors bean="${userInstance}">
            <div class="alert" role="alert" aria-label="error-message"><g:renderErrors bean="${userInstance}" as="list"/></div>
        </g:hasErrors>

        <g:if test="${microsoftEnabled}">
            <a class="ms" id="microsoftSignIn" href="${createLink(controller: 'microsoftAuth', action: 'signIn')}">
                <svg viewBox="0 0 21 21" aria-hidden="true"><rect x="1" y="1" width="9" height="9" fill="#F25022"/><rect x="11" y="1" width="9" height="9" fill="#7FBA00"/><rect x="1" y="11" width="9" height="9" fill="#00A4EF"/><rect x="11" y="11" width="9" height="9" fill="#FFB900"/></svg>
                ${warehouse.message(code: 'aeris.login.microsoft.button', default: 'Sign in with Microsoft')}
            </a>
        </g:if>

        <details class="local ${microsoftEnabled ? '' : 'always'}" ${localOpen ? 'open' : ''}>
            <summary>${warehouse.message(code: 'aeris.login.local.toggle', default: 'Local account (administrator)')}</summary>
            <div class="local-body">
                <g:form controller="auth" action="handleLogin" method="post" autocomplete="on">
                    <g:hiddenField name="targetUri" value="${params?.targetUri}"/>
                    <g:hiddenField id="browserTimezone" name="browserTimezone"/>

                    <label for="username">${warehouse.message(code: 'aeris.login.username.label', default: 'Username')}</label>
                    <div class="field ${hasErrors(bean: userInstance, field: 'username', 'has-error')}">
                        <input type="text" id="username" name="username" autocomplete="username" required
                               value="${userInstance?.username ?: params.username}"
                               placeholder="${warehouse.message(code: 'aeris.login.username.placeholder', default: 'e.g. firstname.lastname')}"/>
                    </div>

                    <label for="password">${warehouse.message(code: 'aeris.login.password.label', default: 'Password')}</label>
                    <div class="field ${hasErrors(bean: userInstance, field: 'password', 'has-error')}">
                        <input type="password" class="pwd" id="password" name="password" autocomplete="current-password" required
                               placeholder="••••••••"/>
                        <button type="button" class="reveal" id="reveal" aria-pressed="false"
                                aria-label="${warehouse.message(code: 'aeris.login.showPassword', default: 'Show password')}">
                            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>
                        </button>
                    </div>

                    <div class="forgot-row">
                        <button type="button" class="forgot" id="forgot" aria-expanded="false" aria-controls="forgotNote">
                            ${warehouse.message(code: 'aeris.login.forgot', default: 'Forgot password?')}
                        </button>
                    </div>
                    <div class="note" id="forgotNote" role="note">
                        <g:if test="${microsoftEnabled}">${warehouse.message(code: 'aeris.login.microsoft.help', default: "First time? Sign in with Microsoft once, then ask your team's AERIS focal point to activate your account.")}</g:if>
                        <g:else>${warehouse.message(code: 'aeris.login.help', default: "No account or forgotten password? Ask your team's AERIS focal point.")}</g:else>
                    </div>

                    <button type="submit" class="submit" id="loginButton">${warehouse.message(code: 'aeris.login.submit', default: 'Sign in')}</button>
                </g:form>
            </div>
        </details>

        <div class="lang">
            <label class="lang-box">
                <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z"/></svg>
                <span class="visually-hidden" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">${warehouse.message(code: 'aeris.login.language', default: 'Language')}</span>
                <select id="langSelect">
                    <g:each in="${locales}" var="l">
                        <option value="${createLink(controller: 'auth', action: 'login', params: [lang: l, targetUri: params.targetUri])}"
                                lang="${l}" ${l == lang ? 'selected' : ''}>${l == 'fr' ? 'Français' : l == 'en' ? 'English' : l}</option>
                    </g:each>
                </select>
                <svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
            </label>
        </div>
    </section>
</main>

<script>
    (function () {
        var tz = '';
        try { tz = jzTimezoneDetector.determine_timezone().timezone.olson_tz; } catch (e) {}
        var tzField = document.getElementById('browserTimezone');
        if (tzField) { tzField.value = tz; }
        var ms = document.getElementById('microsoftSignIn');
        if (ms && tz) { ms.href += (ms.href.indexOf('?') < 0 ? '?' : '&') + 'tz=' + encodeURIComponent(tz); }

        var reveal = document.getElementById('reveal'), pwd = document.getElementById('password');
        reveal.addEventListener('click', function () {
            var show = pwd.type === 'password';
            pwd.type = show ? 'text' : 'password';
            reveal.setAttribute('aria-pressed', String(show));
        });

        var forgot = document.getElementById('forgot'), note = document.getElementById('forgotNote');
        forgot.addEventListener('click', function () {
            var open = note.classList.toggle('show');
            forgot.setAttribute('aria-expanded', String(open));
        });

        document.getElementById('langSelect').addEventListener('change', function () { window.location.href = this.value; });

        // Focus the first useful control
        var local = document.querySelector('details.local');
        if (local && local.open) { document.getElementById('username').focus(); } else if (ms) { ms.focus(); }
        if (local) { local.addEventListener('toggle', function () { if (local.open) { document.getElementById('username').focus(); } }); }

        // Same housekeeping as the upstream login page: drop locally cached requisitions older than 7 days.
        try {
            if (localStorage.openboxesManager) {
                var manager = JSON.parse(localStorage.openboxesManager), now = new Date();
                for (var key in manager) {
                    var expires = new Date(manager[key]);
                    expires.setDate(expires.getDate() + 7);
                    if (now > expires) { delete localStorage[key]; }
                }
            }
        } catch (e) {}
    })();
</script>
</body>
</html>
