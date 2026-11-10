/// Ouverture de la page du fournisseur d'identité, selon la plateforme :
/// - web : redirection pleine page, les paramètres PKCE restent en `sessionStorage` le temps du retour ;
/// - mobile : navigateur système (onglet sécurisé) qui revient sur `xpass://auth/callback`.
library;

export 'oidc_platform_native.dart' if (dart.library.js_interop) 'oidc_platform_web.dart';
