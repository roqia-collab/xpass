<#--
  Mise en page XPASS (maquette 02) : photo d'accueil, logo, choix de la langue, puis carte crème
  contenant le formulaire. Même signature de macro que le gabarit « base » : toutes les pages
  (connexion, inscription, mot de passe oublié, erreurs…) en héritent.
-->
<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<!DOCTYPE html>
<html class="${properties.kcHtmlClass!}"<#if realm.internationalizationEnabled> lang="${locale.currentLanguageTag}" dir="${(locale.rtl)?then('rtl','ltr')}"</#if>>
<head>
    <meta charset="utf-8">
    <meta name="robots" content="noindex, nofollow">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>${msg("loginTitle",(realm.displayName!'XPASS'))}</title>
    <link rel="icon" href="${url.resourcesPath}/img/favicon.png" />
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&display=swap" rel="stylesheet">
    <#if properties.styles?has_content>
        <#list properties.styles?split(' ') as style>
            <link href="${url.resourcesPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>
    <script type="importmap">
        { "imports": { "rfc4648": "${url.resourcesCommonPath}/vendor/rfc4648/rfc4648.js" } }
    </script>
    <#if scripts??>
        <#list scripts as script>
            <script src="${script}" type="text/javascript"></script>
        </#list>
    </#if>
    <script type="module">
        import { startSessionPolling } from "${url.resourcesPath}/js/authChecker.js";
        startSessionPolling("${url.ssoLoginInOtherTabsUrl?no_esc}");
    </script>
</head>

<body class="${properties.kcBodyClass!} ${bodyClass}">
<a class="xp-skip" href="#kc-content">${msg("xpSkipToForm")}</a>
<div class="xp-page">
    <header class="xp-hero">
        <img class="xp-hero-img" src="${url.resourcesPath}/img/hero.jpg" alt="" />
        <div class="xp-hero-top">
            <img class="xp-logo" src="${url.resourcesPath}/img/logo.png" alt="XPASS" />
            <#if realm.internationalizationEnabled && locale.supported?size gt 1>
                <details class="xp-locale">
                    <summary aria-label="${msg("languages")}">
                        <span class="xp-icon xp-icon-globe" aria-hidden="true"></span>
                        <span>${locale.currentLanguageTag?upper_case}</span>
                        <span class="xp-icon xp-icon-chevron" aria-hidden="true"></span>
                    </summary>
                    <ul>
                        <#list locale.supported as l>
                            <li><a href="${l.url}" lang="${l.languageTag}"<#if l.languageTag == locale.currentLanguageTag> aria-current="true"</#if>>${l.label}</a></li>
                        </#list>
                    </ul>
                </details>
            </#if>
        </div>
        <div class="xp-hero-text">
            <p class="xp-hero-title">${msg("xpHeroTitle")}</p>
            <p class="xp-hero-sub">${msg("xpHeroSubtitle")}</p>
            <#if bodyClass == "xp-register">
                <ul class="xp-benefits">
                    <#list ["xpBenefit1", "xpBenefit2", "xpBenefit3"] as b>
                        <li><span class="xp-benefit-dot" aria-hidden="true"><span class="xp-icon xp-icon-check"></span></span>${msg(b)}</li>
                    </#list>
                </ul>
            </#if>
        </div>
    </header>

    <main class="xp-card" id="kc-content">
        <#if bodyClass == "xp-register"><p class="xp-eyebrow">${msg("xpRegisterEyebrow")}</p></#if>
        <h1 id="kc-page-title" class="xp-page-title<#if bodyClass == 'xp-login'> xp-sr-only</#if>"><#nested "header"></h1>
        <#if bodyClass == "xp-register"><p class="xp-page-sub">${msg("xpRegisterSub")}</p></#if>

        <#if auth?has_content && auth.showUsername() && !auth.showResetCredentials()>
            <#nested "show-username">
            <div id="kc-username" class="xp-username">
                <span id="kc-attempted-username">${auth.attemptedUsername}</span>
                <a id="reset-login" href="${url.loginRestartFlowUrl}">${msg("restartLoginTooltip")}</a>
            </div>
        </#if>

        <#if displayRequiredFields>
            <p class="xp-required"><span class="required">*</span> ${msg("requiredFields")}</p>
        </#if>

        <#-- Les actions déclenchées par l'application ne doivent pas voir l'avertissement d'action requise. -->
        <#if displayMessage && message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
            <div class="xp-alert xp-alert-${message.type}" role="<#if message.type = 'error'>alert<#else>status</#if>">
                <span class="xp-alert-text">${kcSanitize(message.summary)?no_esc}</span>
            </div>
        </#if>

        <#nested "socialProviders">

        <#nested "form">

        <#if auth?has_content && auth.showTryAnotherWayLink()>
            <form id="kc-select-try-another-way-form" action="${url.loginAction}" method="post">
                <input type="hidden" name="tryAnotherWay" value="on"/>
                <a href="#" id="try-another-way"
                   onclick="document.forms['kc-select-try-another-way-form'].requestSubmit();return false;">${msg("doTryAnotherWay")}</a>
            </form>
        </#if>

        <#if displayInfo>
            <div id="kc-info" class="xp-info">
                <#nested "info">
            </div>
        </#if>

        <p class="xp-legal">${msg("xpLegal")}</p>
    </main>
</div>
</body>
</html>
</#macro>
