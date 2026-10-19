<%--
  AERIS login page (replaces the upstream login box). Standalone: no layout, no external files.
  Microsoft 365 sign-in (microsoftAuth/signIn) when enabled; the local username/password form posts the same
  fields as upstream to auth/handleLogin: username, password, targetUri, browserTimezone.
--%>
<%-- Same source as warehouse:message (session, then user, then default locale), not the browser locale --%>
<g:set var="lang" value="${grailsApplication.mainContext.getBean('localeManager').currentLocale?.language ?: 'fr'}"/>
<g:set var="locales" value="${grailsApplication.config.openboxes.locale.supportedLocales ?: ['fr', 'en']}"/>
<g:set var="deploymentLabel" value="${grailsApplication.config.openboxes.logo.label ?: ''}"/>
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
    <script>
        // Apply the saved or system theme before first paint, to avoid a light flash in dark mode.
        (function () {
            var t = null;
            try { t = localStorage.getItem('aeris-theme'); } catch (e) {}
            if (!t) { t = window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'; }
            document.documentElement.setAttribute('data-theme', t);
        })();
    </script>
    <style>
        :root {
            --green: #237348; --green-2: #0F7A47; --green-3: #0A5C36; --olive: #3F5E26;
            --gold: #BCA053; --gold-ink: #8A5F10; --maroon: #911936;
            --bg: #EEF1F4; --card: #FFFFFF; --text: #0F1B2D; --muted: #4A5566; --line: #DCE2EA;
            --field: #F7F9FB; --help-bg: #EDF8F2; --help-line: #CFEBDD; --error-bg: #FDEEEF; --error-line: #F3C6CC;
            --seg-bg: #F1F4F7;
        }
        [data-theme="dark"] {
            --bg: #0D1117; --card: #161B22; --text: #E6EDF3; --muted: #9AA6B2; --line: #2D3742;
            --field: #0F141A; --help-bg: #12261C; --help-line: #1F4A33; --error-bg: #2A1418; --error-line: #5C2630;
            --gold-ink: #D9B860; --seg-bg: #0F141A;
        }
        * { box-sizing: border-box; }
        html, body { margin: 0; }
        body {
            font-family: Inter, "Segoe UI", Roboto, Arial, sans-serif; background: var(--bg); color: var(--text);
            min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 40px 16px;
        }
        /* Compact card, centred with room around it */
        .card {
            display: grid; grid-template-columns: 0.95fr 1fr; width: 100%; max-width: 900px;
            background: var(--card); border-radius: 20px; overflow: hidden; position: relative;
            box-shadow: 0 24px 48px -28px rgba(15, 27, 45, .35), 0 0 0 1px var(--line);
        }
        .card::before {
            content: ""; position: absolute; top: 0; left: 0; width: 49%; height: 3px; z-index: 2;
            background: linear-gradient(90deg, var(--gold), #9BBF3A 60%, var(--green-2));
        }
        /* Brand panel */
        .brand {
            color: #fff; padding: 32px 32px 28px; display: flex; flex-direction: column;
            background: radial-gradient(120% 90% at 0% 0%, #17995A 0%, transparent 60%),
                        linear-gradient(165deg, var(--green-2) 0%, var(--green-3) 55%, var(--olive) 100%);
        }
        .logo-card { background: #fff; border-radius: 12px; padding: 10px 14px; width: fit-content; box-shadow: 0 8px 22px -12px rgba(0,0,0,.35); }
        .logo-card img { display: block; width: 190px; max-width: 100%; height: auto; }
        .brand h1 { font-size: 36px; line-height: 1; margin: 26px 0 6px; font-weight: 800; letter-spacing: -1px; }
        .brand .subtitle { font-size: 15px; font-weight: 600; margin: 0; }
        .brand .tagline { font-size: 15px; line-height: 1.55; margin: 18px 0 0; color: rgba(255,255,255,.92); }
        .features { list-style: none; padding: 26px 0 0; margin: auto 0 0; display: grid; gap: 14px; }
        .features li { display: grid; grid-template-columns: 22px 1fr; gap: 10px; align-items: start; }
        .features svg { width: 18px; height: 18px; stroke: #E6CF7A; fill: none; stroke-width: 1.8; margin-top: 2px; }
        .features b { display: block; font-size: 14px; font-weight: 700; }
        .features span { display: block; font-size: 13px; line-height: 1.45; color: rgba(255,255,255,.86); margin-top: 1px; }
        /* Form panel */
        .form { padding: 28px 36px 24px; display: flex; flex-direction: column; }
        .toolbar { display: flex; justify-content: flex-end; align-items: center; gap: 8px; }
        .seg { display: inline-flex; background: var(--seg-bg); border: 1px solid var(--line); border-radius: 10px; padding: 3px; }
        .seg a {
            min-width: 40px; height: 30px; padding: 0 10px; border-radius: 7px; display: inline-flex; align-items: center; justify-content: center;
            font: 700 13px Inter, sans-serif; color: var(--muted); text-decoration: none;
        }
        .seg a[aria-current="true"] { background: var(--card); color: var(--text); box-shadow: 0 1px 2px rgba(0,0,0,.12); }
        .seg a:not([aria-current="true"]):hover { color: var(--text); }
        .tool {
            width: 38px; height: 38px; border-radius: 10px; border: 1px solid var(--line); background: var(--card);
            color: var(--text); display: inline-flex; align-items: center; justify-content: center; cursor: pointer; padding: 0;
        }
        .tool:hover { background: var(--field); }
        .tool svg { width: 18px; height: 18px; stroke: currentColor; fill: none; stroke-width: 1.8; }
        .eyebrow { margin: 18px 0 0; color: var(--gold-ink); font-weight: 800; letter-spacing: 1.3px; font-size: 12px; text-transform: uppercase; }
        .form h2 { font-size: 28px; margin: 8px 0 4px; font-weight: 800; letter-spacing: -.5px; }
        .intro { color: var(--muted); font-size: 14px; margin: 0 0 20px; }
        .ms {
            width: 100%; height: 48px; border-radius: 12px; border: 1px solid var(--line); background: var(--card); color: var(--text);
            font: 600 15px Inter, sans-serif; display: flex; align-items: center; justify-content: center; gap: 12px; text-decoration: none;
            box-shadow: 0 1px 2px rgba(15,27,45,.08);
        }
        .ms:hover { background: var(--field); border-color: #B9C3CF; }
        .ms svg { width: 20px; height: 20px; }
        details.local { margin-top: 16px; border-top: 1px solid var(--line); padding-top: 12px; }
        details.local summary { cursor: pointer; color: var(--muted); font-size: 13px; font-weight: 600; list-style: none; }
        details.local summary::-webkit-details-marker { display: none; }
        details.local summary::before { content: "›"; display: inline-block; margin-right: 6px; transition: transform .15s; }
        details.local[open] summary::before { transform: rotate(90deg); }
        details.local.always { border-top: 0; padding-top: 0; margin-top: 0; }
        details.local.always summary { display: none; }
        .local-body { padding-top: 14px; }
        label { display: block; font-weight: 700; font-size: 13px; margin: 0 0 6px; }
        .field { position: relative; margin-bottom: 14px; }
        .field > svg { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); width: 17px; height: 17px; stroke: var(--muted); fill: none; stroke-width: 1.8; pointer-events: none; }
        .field input {
            width: 100%; height: 44px; border-radius: 11px; border: 1.5px solid var(--line); background: var(--field); color: var(--text);
            font: 400 15px Inter, sans-serif; padding: 0 44px 0 42px; outline: none; transition: border-color .15s, box-shadow .15s;
        }
        .field input::placeholder { color: #8893A2; }
        .field input:focus { border-color: var(--green); box-shadow: 0 0 0 3px rgba(35,115,72,.15); }
        .field.has-error input { border-color: var(--maroon); }
        .reveal { position: absolute; right: 6px; top: 50%; transform: translateY(-50%); background: none; border: 0; padding: 6px; cursor: pointer; color: var(--muted); border-radius: 8px; }
        .reveal svg { width: 18px; height: 18px; stroke: currentColor; fill: none; stroke-width: 1.8; display: block; }
        .submit {
            width: 100%; height: 46px; border: 0; border-radius: 12px; margin-top: 4px; cursor: pointer; color: #fff;
            font: 700 15px Inter, sans-serif; background: linear-gradient(180deg, #158A52, var(--green-3));
            box-shadow: 0 10px 20px -12px rgba(10, 92, 54, .8);
        }
        .submit:hover { filter: brightness(1.06); }
        .submit:focus-visible, .tool:focus-visible, .reveal:focus-visible, .ms:focus-visible, .seg a:focus-visible, summary:focus-visible {
            outline: 3px solid var(--gold); outline-offset: 2px;
        }
        .alert { border-radius: 11px; padding: 10px 14px; margin: 0 0 16px; font-size: 13.5px; line-height: 1.5; background: var(--error-bg); border: 1px solid var(--error-line); }
        .alert ul { margin: 0; padding-left: 18px; }
        .help {
            display: grid; grid-template-columns: 20px 1fr; gap: 10px; align-items: start; margin-top: 18px;
            background: var(--help-bg); border: 1px solid var(--help-line); border-radius: 12px; padding: 12px 14px; color: var(--muted); font-size: 13px; line-height: 1.5;
        }
        .help svg { width: 18px; height: 18px; stroke: var(--green); fill: none; stroke-width: 1.8; margin-top: 1px; }
        .help a { color: var(--green); font-weight: 600; }
        .foot { margin-top: auto; padding-top: 18px; color: var(--muted); font-size: 12px; display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
        .status { display: inline-flex; align-items: center; gap: 6px; font-family: ui-monospace, Consolas, monospace; }
        .dot { width: 7px; height: 7px; border-radius: 50%; background: #2DA160; box-shadow: 0 0 0 3px rgba(45,161,96,.2); }
        @media (max-width: 760px) {
            body { padding: 16px; align-items: flex-start; }
            .card { grid-template-columns: 1fr; }
            .card::before { width: 100%; }
            .brand { padding: 22px; }
            .brand h1 { font-size: 30px; margin-top: 18px; }
            .features { display: none; }
            .form { padding: 22px; }
        }
    </style>
</head>
<body>
<main class="card">
    <section class="brand" aria-label="AERIS">
        <div class="logo-card">
            <img src="${assetPath(src: 'africacdc_logo.png')}" alt="Africa CDC – Centres for Disease Control and Prevention" width="190" height="53"/>
        </div>
        <h1>AERIS</h1>
        <p class="subtitle">${warehouse.message(code: 'aeris.login.subtitle', default: 'Emergency Response Inventory System')}</p>
        <p class="tagline">${warehouse.message(code: 'aeris.login.tagline', default: 'Response commodities tracked lot by lot, from donor receipt to signed release note.')}</p>
        <ul class="features">
            <li>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7l9-4 9 4-9 4-9-4z"/><path d="M3 7v10l9 4 9-4V7"/><path d="M12 11v10"/></svg>
                <div><b>${warehouse.message(code: 'aeris.login.feature1.title', default: 'Every lot, every expiry')}</b>
                    <span>${warehouse.message(code: 'aeris.login.feature1.text', default: 'Stock received by lot and expiry; earliest expiry leaves first.')}</span></div>
            </li>
            <li>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5"/><path d="M8.5 14.5l2 2 4-4.5"/></svg>
                <div><b>${warehouse.message(code: 'aeris.login.feature2.title', default: 'Signed release notes')}</b>
                    <span>${warehouse.message(code: 'aeris.login.feature2.text', default: 'Each issue traces to a signed bon de sortie.')}</span></div>
            </li>
            <li>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/></svg>
                <div><b>${warehouse.message(code: 'aeris.login.feature3.title', default: 'Hosted by Africa CDC')}</b>
                    <span>${warehouse.message(code: 'aeris.login.feature3.text', default: 'Stock data stays on Africa CDC servers.')}</span></div>
            </li>
        </ul>
    </section>

    <section class="form">
        <div class="toolbar">
            <nav class="seg" aria-label="${warehouse.message(code: 'aeris.login.language', default: 'Language')}">
                <g:each in="${locales}" var="l">
                    <a href="${createLink(controller: 'auth', action: 'login', params: [lang: l, targetUri: params.targetUri])}"
                       lang="${l}" hreflang="${l}" aria-current="${l == lang}"
                       title="${l == 'fr' ? 'Français' : l == 'en' ? 'English' : l}">${l.toUpperCase()}</a>
                </g:each>
            </nav>
            <button class="tool" type="button" id="themeToggle" aria-label="${warehouse.message(code: 'aeris.login.theme', default: 'Switch light or dark mode')}">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg>
            </button>
        </div>

        <p class="eyebrow">Africa CDC<g:if test="${deploymentLabel}"> · ${deploymentLabel}</g:if></p>
        <h2>${warehouse.message(code: 'aeris.login.title', default: 'Sign in')}</h2>
        <p class="intro">
            <g:if test="${microsoftEnabled}">${warehouse.message(code: 'aeris.login.microsoft.intro', default: 'Use your Africa CDC Microsoft 365 account.')}</g:if>
            <g:else>${warehouse.message(code: 'aeris.login.intro', default: 'Use your AERIS account.')}</g:else>
        </p>

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
                        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>
                        <input type="text" id="username" name="username" autocomplete="username" required
                               value="${userInstance?.username ?: params.username}"
                               placeholder="${warehouse.message(code: 'aeris.login.username.placeholder', default: 'e.g. firstname.lastname')}"/>
                    </div>

                    <label for="password">${warehouse.message(code: 'aeris.login.password.label', default: 'Password')}</label>
                    <div class="field ${hasErrors(bean: userInstance, field: 'password', 'has-error')}">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>
                        <input type="password" id="password" name="password" autocomplete="current-password" required
                               placeholder="${warehouse.message(code: 'aeris.login.password.placeholder', default: 'Your AERIS password')}"/>
                        <button type="button" class="reveal" id="reveal" aria-pressed="false"
                                aria-label="${warehouse.message(code: 'aeris.login.showPassword', default: 'Show password')}">
                            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>
                        </button>
                    </div>

                    <button type="submit" class="submit" id="loginButton">${warehouse.message(code: 'aeris.login.submit', default: 'Sign in')}</button>
                </g:form>
            </div>
        </details>

        <div class="help">
            <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6"/><circle cx="12" cy="17" r=".6"/></svg>
            <div>
                <g:if test="${microsoftEnabled}">${warehouse.message(code: 'aeris.login.microsoft.help', default: "First time? Sign in with Microsoft once, then ask your team's AERIS focal point to activate your account.")}</g:if>
                <g:else>${warehouse.message(code: 'aeris.login.help', default: "No account or forgotten password? Ask your team's AERIS focal point.")}</g:else>
                <g:if test="${grailsApplication.config.openboxes.signup.enabled}">
                    <br/><g:link controller="auth" action="signup">${warehouse.message(code: 'auth.signup.label', default: 'Signup')}</g:link>
                </g:if>
            </div>
        </div>

        <div class="foot">
            <span>Africa CDC · ${warehouse.message(code: 'aeris.login.footer', default: 'Emergency logistics')}</span>
            <span class="status"><span class="dot" aria-hidden="true"></span>AERIS <g:meta name="info.app.version"/></span>
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

        document.getElementById('themeToggle').addEventListener('click', function () {
            var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            try { localStorage.setItem('aeris-theme', next); } catch (e) {}
        });

        var reveal = document.getElementById('reveal'), pwd = document.getElementById('password');
        reveal.addEventListener('click', function () {
            var show = pwd.type === 'password';
            pwd.type = show ? 'text' : 'password';
            reveal.setAttribute('aria-pressed', String(show));
        });

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
