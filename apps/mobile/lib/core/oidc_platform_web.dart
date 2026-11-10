import 'dart:convert';

import 'package:web/web.dart' as web;

import 'oidc.dart';

const _pendingKey = 'xpass_oidc_pending';

class OidcPlatform {
  static const isWeb = true;

  /// Retour sur la base de l'application (le routage par fragment `#/…` reprend ensuite).
  static String redirectUri() => web.document.baseURI;

  /// Redirection pleine page : la suite se fait au rechargement (voir [takePendingCallback]).
  static Future<Uri?> authenticate(Uri url, PendingLogin pending) async {
    web.window.sessionStorage.setItem(_pendingKey, jsonEncode(pending.toJson()));
    web.window.location.assign(url.toString());
    return null;
  }

  static (Uri, PendingLogin)? _captured;

  /// À appeler AVANT le démarrage du routeur : si l'URL est un retour de connexion (`code`, `state`), le
  /// mémorise et nettoie l'adresse (le code ne reste ni dans l'historique ni à l'écran), puis ouvre les Paramètres.
  static void captureCallback() {
    final uri = Uri.parse(web.window.location.href);
    final hasCallback = uri.queryParameters.containsKey('state') &&
        (uri.queryParameters.containsKey('code') || uri.queryParameters.containsKey('error'));
    if (!hasCallback) return;
    final raw = web.window.sessionStorage.getItem(_pendingKey);
    web.window.sessionStorage.removeItem(_pendingKey);
    web.window.history.replaceState(null, '', '${web.document.baseURI}#/profil');
    if (raw != null) _captured = (uri, PendingLogin.fromJson(jsonDecode(raw) as Map<String, dynamic>));
  }

  static (Uri, PendingLogin)? takePendingCallback() {
    final c = _captured;
    _captured = null;
    return c;
  }

  static Future<void> openLogout(Uri url) async => web.window.location.assign(url.toString());
}
