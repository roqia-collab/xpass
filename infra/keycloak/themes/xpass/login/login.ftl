<#--
  Connexion (maquette 02) : onglets E-mail / Téléphone, champs à icône, « Mot de passe oublié ? »,
  bouton corail, séparateur « ou », « Créer un compte » et « Explorer sans compte ».
  La connexion par téléphone n'existe pas encore : l'onglet est affiché désactivé, marqué « Bientôt ».
-->
<#import "template.ftl" as layout>
<@layout.registrationLayout bodyClass="xp-login" displayMessage=!messagesPerField.existsError('username','password') displayInfo=realm.password && realm.registrationAllowed && !registrationDisabled??; section>
    <#if section = "header">
        ${msg("xpLoginTitle")}
    <#elseif section = "form">
        <#if realm.password>
            <div class="xp-tabs" role="group" aria-label="${msg("xpLoginMethod")}">
                <span class="xp-tab xp-tab-active" aria-current="true">
                    <span class="xp-icon xp-icon-mail" aria-hidden="true"></span>${msg("xpTabEmail")}
                </span>
                <span class="xp-tab xp-tab-disabled" aria-disabled="true" title="${msg("xpPhoneSoon")}">
                    <span class="xp-icon xp-icon-phone" aria-hidden="true"></span>${msg("xpTabPhone")}
                    <small>${msg("xpSoon")}</small>
                </span>
            </div>

            <form id="kc-form-login" class="xp-form" onsubmit="login.disabled = true; return true;" action="${url.loginAction}" method="post" novalidate>
                <#if !usernameHidden??>
                    <div class="xp-group">
                        <label for="username" class="xp-sr-only">${msg("email")}</label>
                        <div class="xp-field<#if messagesPerField.existsError('username','password')> xp-field-error</#if>">
                            <span class="xp-icon xp-icon-mail" aria-hidden="true"></span>
                            <input tabindex="2" id="username" name="username" value="${(login.username!'')}" type="email"
                                   placeholder="${msg("xpEmailPlaceholder")}" autofocus autocomplete="username" dir="ltr"
                                   aria-invalid="<#if messagesPerField.existsError('username','password')>true</#if>"
                                   <#if messagesPerField.existsError('username','password')>aria-describedby="input-error"</#if> />
                        </div>
                    </div>
                </#if>

                <div class="xp-group">
                    <label for="password" class="xp-sr-only">${msg("password")}</label>
                    <div class="xp-field<#if messagesPerField.existsError('username','password')> xp-field-error</#if>" dir="ltr">
                        <span class="xp-icon xp-icon-lock" aria-hidden="true"></span>
                        <input tabindex="3" id="password" name="password" type="password" placeholder="${msg("password")}"
                               autocomplete="current-password"
                               aria-invalid="<#if messagesPerField.existsError('username','password')>true</#if>"
                               <#if messagesPerField.existsError('username','password')>aria-describedby="input-error"</#if> />
                        <button class="xp-eye-btn" type="button" aria-label="${msg("showPassword")}" aria-controls="password"
                                data-password-toggle tabindex="4"
                                data-icon-show="xp-icon xp-icon-eye" data-icon-hide="xp-icon xp-icon-eye-off"
                                data-label-show="${msg('showPassword')}" data-label-hide="${msg('hidePassword')}">
                            <i class="xp-icon xp-icon-eye" aria-hidden="true"></i>
                        </button>
                    </div>
                    <#if messagesPerField.existsError('username','password')>
                        <p id="input-error" class="xp-error" aria-live="polite">
                            ${kcSanitize(messagesPerField.getFirstError('username','password'))?no_esc}
                        </p>
                    </#if>
                </div>

                <div class="xp-row">
                    <#if realm.rememberMe && !usernameHidden??>
                        <label class="xp-remember">
                            <input tabindex="5" id="rememberMe" name="rememberMe" type="checkbox" <#if login.rememberMe??>checked</#if>>
                            ${msg("rememberMe")}
                        </label>
                    </#if>
                    <#if realm.resetPasswordAllowed>
                        <a class="xp-link xp-forgot" tabindex="6" href="${url.loginResetCredentialsUrl}">${msg("doForgotPassword")}</a>
                    </#if>
                </div>

                <input type="hidden" id="id-hidden-input" name="credentialId" <#if auth.selectedCredential?has_content>value="${auth.selectedCredential}"</#if>/>
                <button tabindex="7" class="xp-btn xp-btn-primary xp-btn-block" name="login" id="kc-login" type="submit">
                    <span>${msg("xpSignIn")}</span>
                    <span class="xp-icon xp-icon-arrow" aria-hidden="true"></span>
                </button>
            </form>
        </#if>
        <script type="module" src="${url.resourcesPath}/js/passwordVisibility.js"></script>
    <#elseif section = "info">
        <div class="xp-divider"><span>${msg("xpOr")}</span></div>
        <a class="xp-btn xp-btn-outline xp-btn-block" tabindex="8" href="${url.registrationUrl}">${msg("xpCreateAccount")}</a>
        <#if client?? && client.baseUrl?has_content>
            <a class="xp-link xp-explore" href="${client.baseUrl}">${msg("xpExploreWithoutAccount")}</a>
        </#if>
    <#elseif section = "socialProviders">
        <#if realm.password && social?? && social.providers?has_content>
            <div class="xp-social">
                <#list social.providers as p>
                    <a id="social-${p.alias}" class="xp-btn xp-btn-social xp-btn-block" href="${p.loginUrl}">
                        <#if p.providerId == "google">
                            <svg class="xp-google" viewBox="0 0 48 48" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/><path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>
                        </#if>
                        <span>${msg("xpContinueWith", p.displayName!p.alias)}</span>
                    </a>
                </#list>
                <div class="xp-divider"><span>${msg("xpOrEmail")}</span></div>
            </div>
        </#if>
    </#if>
</@layout.registrationLayout>
