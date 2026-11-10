<#-- Inscription (maquette 02) : gabarit « base » de Keycloak, mise en page XPASS, lien retour sous le bouton. -->
<#import "template.ftl" as layout>
<#import "user-profile-commons.ftl" as userProfileCommons>
<#import "register-commons.ftl" as registerCommons>
<@layout.registrationLayout bodyClass="xp-register" displayMessage=messagesPerField.exists('global') displayRequiredFields=true; section>
    <#if section = "header">
        <#if messageHeader??>
            ${kcSanitize(msg("${messageHeader}"))?no_esc}
        <#else>
            ${msg("registerTitle")}
        </#if>
    <#elseif section = "form">
        <form id="kc-register-form" class="${properties.kcFormClass!}" action="${url.registrationAction}" method="post">

            <@userProfileCommons.userProfileFormFields; callback, attribute>
                <#if callback = "afterField">
                <#-- render password fields just under the username or email (if used as username) -->
                    <#if passwordRequired?? && (attribute.name == 'username' || (attribute.name == 'email' && realm.registrationEmailAsUsername))>
                        <div class="${properties.kcFormGroupClass!}">
                            <div class="${properties.kcLabelWrapperClass!}">
                                <label for="password" class="${properties.kcLabelClass!}">${msg("password")}</label> *
                            </div>
                            <div class="${properties.kcInputWrapperClass!}">
                                <div class="${properties.kcInputGroup!}" dir="ltr">
                                    <input type="password" id="password" class="${properties.kcInputClass!}" name="password"
                                           autocomplete="new-password"
                                           aria-invalid="<#if messagesPerField.existsError('password','password-confirm')>true</#if>"
                                    />
                                    <button class="${properties.kcFormPasswordVisibilityButtonClass!}" type="button" aria-label="${msg('showPassword')}"
                                            aria-controls="password"  data-password-toggle
                                            data-icon-show="${properties.kcFormPasswordVisibilityIconShow!}" data-icon-hide="${properties.kcFormPasswordVisibilityIconHide!}"
                                            data-label-show="${msg('showPassword')}" data-label-hide="${msg('hidePassword')}">
                                        <i class="${properties.kcFormPasswordVisibilityIconShow!}" aria-hidden="true"></i>
                                    </button>
                                </div>
                                <div class="xp-strength" id="xp-strength" data-level="0"
                                     data-labels="${msg('xpStrength1')}|${msg('xpStrength2')}|${msg('xpStrength3')}|${msg('xpStrength4')}">
                                    <div class="xp-strength-bars" aria-hidden="true"><span></span><span></span><span></span><span></span></div>
                                    <span class="xp-strength-text" aria-live="polite">${msg("xpStrengthHint")}</span>
                                </div>

                                <#if messagesPerField.existsError('password')>
                                    <span id="input-error-password" class="${properties.kcInputErrorMessageClass!}" aria-live="polite">
		                                ${kcSanitize(messagesPerField.get('password'))?no_esc}
		                            </span>
                                </#if>
                            </div>
                        </div>

                        <div class="${properties.kcFormGroupClass!}">
                            <div class="${properties.kcLabelWrapperClass!}">
                                <label for="password-confirm"
                                       class="${properties.kcLabelClass!}">${msg("passwordConfirm")}</label> *
                            </div>
                            <div class="${properties.kcInputWrapperClass!}">
                                <div class="${properties.kcInputGroup!}" dir="ltr">
                                    <input type="password" id="password-confirm" class="${properties.kcInputClass!}"
                                           name="password-confirm" autocomplete="new-password"
                                           aria-invalid="<#if messagesPerField.existsError('password-confirm')>true</#if>"
                                    />
                                    <button class="${properties.kcFormPasswordVisibilityButtonClass!}" type="button" aria-label="${msg('showPassword')}"
                                            aria-controls="password-confirm"  data-password-toggle
                                            data-icon-show="${properties.kcFormPasswordVisibilityIconShow!}" data-icon-hide="${properties.kcFormPasswordVisibilityIconHide!}"
                                            data-label-show="${msg('showPassword')}" data-label-hide="${msg('hidePassword')}">
                                        <i class="${properties.kcFormPasswordVisibilityIconShow!}" aria-hidden="true"></i>
                                    </button>
                                </div>

                                <#if messagesPerField.existsError('password-confirm')>
                                    <span id="input-error-password-confirm" class="${properties.kcInputErrorMessageClass!}" aria-live="polite">
		                                ${kcSanitize(messagesPerField.get('password-confirm'))?no_esc}
		                            </span>
                                </#if>
                            </div>
                        </div>
                    </#if>
                </#if>
            </@userProfileCommons.userProfileFormFields>

            <@registerCommons.termsAcceptance/>

            <#if recaptchaRequired?? && (recaptchaVisible!false)>
                <div class="form-group">
                    <div class="${properties.kcInputWrapperClass!}">
                        <div class="g-recaptcha" data-size="compact" data-sitekey="${recaptchaSiteKey}" data-action="${recaptchaAction}"></div>
                    </div>
                </div>
            </#if>

            <div class="${properties.kcFormGroupClass!}">
                <#if recaptchaRequired?? && !(recaptchaVisible!false)>
                    <script>
                        function onSubmitRecaptcha(token) {
                            document.getElementById("kc-register-form").requestSubmit();
                        }
                    </script>
                    <div id="kc-form-buttons" class="${properties.kcFormButtonsClass!}">
                        <button class="${properties.kcButtonClass!} ${properties.kcButtonPrimaryClass!} ${properties.kcButtonBlockClass!} ${properties.kcButtonLargeClass!} g-recaptcha" 
                            data-sitekey="${recaptchaSiteKey}" data-callback='onSubmitRecaptcha' data-action='${recaptchaAction}' type="submit">
                            ${msg("doRegister")}
                        </button>
                    </div>
                <#else>
                    <div id="kc-form-buttons" class="${properties.kcFormButtonsClass!}">
                        <input class="${properties.kcButtonClass!} ${properties.kcButtonPrimaryClass!} ${properties.kcButtonBlockClass!} ${properties.kcButtonLargeClass!}" type="submit" value="${msg("doRegister")}"/>
                    </div>
                </#if>
                <p class="xp-back">${msg("xpHaveAccount")} <a class="xp-link" href="${url.loginUrl}">${msg("xpSignIn")}</a></p>
            </div>
        </form>
        <script type="module" src="${url.resourcesPath}/js/passwordVisibility.js"></script>
        <script>
            (function () {
                var input = document.getElementById("password"), box = document.getElementById("xp-strength");
                if (!input || !box) return;
                var labels = box.getAttribute("data-labels").split("|"), text = box.querySelector(".xp-strength-text");
                var hint = text.textContent, prefix = "${msg('xpStrength')?js_string} : ";
                input.addEventListener("input", function () {
                    var v = input.value, s = 0;
                    if (v.length >= 8) s++;
                    if (/[a-z]/.test(v) && /[A-Z]/.test(v)) s++;
                    if (/\d/.test(v) && /[^A-Za-z0-9]/.test(v)) s++;
                    if (v.length >= 12) s++;
                    if (v && s === 0) s = 1;
                    box.setAttribute("data-level", String(s));
                    text.textContent = v ? prefix + labels[s - 1] : hint;
                });
            })();
        </script>
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
