import 'package:flutter_web_auth_2/flutter_web_auth_2.dart';

import 'oidc.dart';

const nativeRedirectUri = 'xpass://auth/callback';

class OidcPlatform {
  static const isWeb = false;

  static String redirectUri() => nativeRedirectUri;

  /// Ouvre la page du fournisseur et attend le retour. Retourne l'URL de retour (avec `code` et `state`).
  static Future<Uri?> authenticate(Uri url, PendingLogin pending) async {
    final result = await FlutterWebAuth2.authenticate(url: url.toString(), callbackUrlScheme: 'xpass');
    return Uri.parse(result);
  }

  /// Sur mobile, pas de retour par rechargement de page.
  static void captureCallback() {}

  static (Uri, PendingLogin)? takePendingCallback() => null;

  static Future<void> openLogout(Uri url) async {
    try {
      await FlutterWebAuth2.authenticate(url: url.toString(), callbackUrlScheme: 'xpass');
    } catch (_) {
      // L'utilisateur a pu fermer l'onglet : la session locale est déjà effacée.
    }
  }
}
