import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';

import 'api_client.dart';
import 'config.dart';

/// Jetons OIDC. Le mot de passe n'est jamais saisi dans l'application : la connexion et l'inscription se
/// font sur la page du fournisseur d'identité (Authorization Code + PKCE, client public).
class TokenSet {
  const TokenSet({required this.accessToken, required this.expiresAt, this.refreshToken, this.idToken});

  final String accessToken;
  final DateTime expiresAt;
  final String? refreshToken;
  final String? idToken;

  bool get expiresSoon => DateTime.now().isAfter(expiresAt.subtract(const Duration(seconds: 30)));

  Map<String, dynamic> toJson() => {
        'access_token': accessToken,
        'expires_at': expiresAt.toIso8601String(),
        'refresh_token': refreshToken,
        'id_token': idToken,
      };

  factory TokenSet.fromJson(Map<String, dynamic> j) => TokenSet(
        accessToken: j['access_token'] as String,
        expiresAt: DateTime.parse(j['expires_at'] as String),
        refreshToken: j['refresh_token'] as String?,
        idToken: j['id_token'] as String?,
      );

  factory TokenSet.fromTokenResponse(Map<String, dynamic> j, {String? previousRefresh}) => TokenSet(
        accessToken: j['access_token'] as String,
        expiresAt: DateTime.now().add(Duration(seconds: (j['expires_in'] as num?)?.toInt() ?? 300)),
        refreshToken: j['refresh_token'] as String? ?? previousRefresh,
        idToken: j['id_token'] as String?,
      );
}

/// Paramètres d'une connexion en cours (conservés pendant la redirection).
class PendingLogin {
  const PendingLogin({required this.state, required this.verifier, required this.redirectUri});
  final String state;
  final String verifier;
  final String redirectUri;

  Map<String, String> toJson() => {'state': state, 'verifier': verifier, 'redirect_uri': redirectUri};

  factory PendingLogin.fromJson(Map<String, dynamic> j) => PendingLogin(
      state: j['state'] as String, verifier: j['verifier'] as String, redirectUri: j['redirect_uri'] as String);
}

String _random(int bytes) {
  final r = Random.secure();
  return base64UrlEncode(List.generate(bytes, (_) => r.nextInt(256))).replaceAll('=', '');
}

String pkceChallenge(String verifier) =>
    base64UrlEncode(sha256.convert(ascii.encode(verifier)).bytes).replaceAll('=', '');

class OidcClient {
  OidcClient(this._dio);
  final Dio _dio;

  static bool get configured => AppConfig.oidcIssuer.isNotEmpty;
  String get _base => '${AppConfig.oidcIssuer}/protocol/openid-connect';

  PendingLogin newLogin(String redirectUri) =>
      PendingLogin(state: _random(16), verifier: _random(48), redirectUri: redirectUri);

  /// Page de connexion (ou d'inscription) du fournisseur d'identité.
  Uri authorizeUrl(PendingLogin p, {bool register = false, String? locale}) =>
      Uri.parse('$_base/${register ? 'registrations' : 'auth'}').replace(queryParameters: {
        'client_id': AppConfig.oidcClientId,
        'response_type': 'code',
        'scope': 'openid profile email',
        'redirect_uri': p.redirectUri,
        'state': p.state,
        'code_challenge': pkceChallenge(p.verifier),
        'code_challenge_method': 'S256',
        if (locale != null) 'ui_locales': locale,
        'kc_idp_hint': 'google',
      });

  Future<TokenSet> exchange({required String code, required PendingLogin pending}) => _token({
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': pending.redirectUri,
        'client_id': AppConfig.oidcClientId,
        'code_verifier': pending.verifier,
      });

  Future<TokenSet> refresh(TokenSet current) => _token({
        'grant_type': 'refresh_token',
        'refresh_token': current.refreshToken!,
        'client_id': AppConfig.oidcClientId,
      }, previousRefresh: current.refreshToken);

  Uri logoutUrl(TokenSet tokens, String postLogoutRedirect) => Uri.parse('$_base/logout').replace(queryParameters: {
        'client_id': AppConfig.oidcClientId,
        if (tokens.idToken != null) 'id_token_hint': tokens.idToken!,
        'post_logout_redirect_uri': postLogoutRedirect,
      });

  Future<TokenSet> _token(Map<String, String> form, {String? previousRefresh}) async {
    try {
      final res = await _dio.post<Map<String, dynamic>>('$_base/token',
          data: form, options: Options(contentType: Headers.formUrlEncodedContentType));
      return TokenSet.fromTokenResponse(res.data!, previousRefresh: previousRefresh);
    } on DioException catch (e) {
      throw ApiException(
        e.type == DioExceptionType.badResponse
            ? 'Connexion refusée ou expirée. Reconnectez-vous.'
            : 'Fournisseur d’identité injoignable. Vérifiez votre réseau.',
        statusCode: e.response?.statusCode,
        isNetwork: e.type != DioExceptionType.badResponse,
      );
    }
  }
}
