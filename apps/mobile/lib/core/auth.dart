import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'api_client.dart';
import 'oidc.dart';
import 'oidc_platform.dart';

class AuthSession {
  const AuthSession({
    required this.token,
    required this.displayName,
    required this.email,
    this.emailVerified = false,
    this.locale = 'fr',
    this.notifyEmail = true,
    this.isOidc = false,
  });

  /// Jeton d'accès courant (renouvelé automatiquement pour une session OIDC).
  final String token;
  final String displayName;
  final String email;
  final bool emailVerified;
  final String locale;
  final bool notifyEmail;
  final bool isOidc;

  AuthSession copyWith({String? token, String? displayName, String? locale, bool? notifyEmail}) => AuthSession(
        token: token ?? this.token,
        displayName: displayName ?? this.displayName,
        email: email,
        emailVerified: emailVerified,
        locale: locale ?? this.locale,
        notifyEmail: notifyEmail ?? this.notifyEmail,
        isOidc: isOidc,
      );
}

/// Stockage chiffré des jetons (trousseau / Keystore ; stockage du navigateur sur le web), remplaçable dans les tests.
abstract class TokenStore {
  Future<String?> read();
  Future<void> write(String value);
  Future<void> clear();
}

class SecureTokenStore implements TokenStore {
  static const _key = 'xpass_access_token';
  final _storage = const FlutterSecureStorage();

  @override
  Future<String?> read() => _storage.read(key: _key);
  @override
  Future<void> write(String value) => _storage.write(key: _key, value: value);
  @override
  Future<void> clear() => _storage.delete(key: _key);
}

final tokenStoreProvider = Provider<TokenStore>((ref) => SecureTokenStore());
final oidcClientProvider = Provider<OidcClient>((ref) => OidcClient(Dio()));

/// Session du client.
/// - Production : OIDC (écran 02) — connexion et inscription sur la page du fournisseur d'identité.
/// - Développement : connexion de démonstration sans mot de passe (`*@xpass.demo`, refusée en production).
class AuthController extends AsyncNotifier<AuthSession?> {
  TokenSet? _tokens;
  Future<TokenSet>? _refreshing;

  @override
  Future<AuthSession?> build() async {
    final store = ref.read(tokenStoreProvider);
    final callback = OidcPlatform.takePendingCallback();
    if (callback != null) {
      final (uri, pending) = callback;
      await _completeLogin(uri, pending);
    }
    final raw = await store.read();
    if (raw == null) return null;
    try {
      if (raw.startsWith('{')) {
        _tokens = TokenSet.fromJson(jsonDecode(raw) as Map<String, dynamic>);
        return await _me(await validToken(), isOidc: true);
      }
      return await _me(raw);
    } on ApiException catch (e) {
      if (e.statusCode == 401 || e.statusCode == 400) await _clearLocal();
      return null;
    }
  }

  Future<void> _completeLogin(Uri uri, PendingLogin pending) async {
    if (uri.queryParameters['state'] != pending.state || uri.queryParameters['code'] == null) {
      return; // retour inattendu (annulation, erreur, ou tentative de rejeu) : rien n'est enregistré
    }
    final tokens = await ref.read(oidcClientProvider).exchange(code: uri.queryParameters['code']!, pending: pending);
    await _saveTokens(tokens);
  }

  Future<void> _saveTokens(TokenSet tokens) async {
    _tokens = tokens;
    await ref.read(tokenStoreProvider).write(jsonEncode(tokens.toJson()));
  }

  Future<AuthSession> _me(String token, {bool isOidc = false}) async {
    try {
      final res = await ref.read(rawDioProvider).get<Map<String, dynamic>>(
            '/me',
            options: Options(headers: {'Authorization': 'Bearer $token'}),
          );
      final d = res.data!;
      return AuthSession(
        token: token,
        displayName: d['display_name'] as String,
        email: d['email'] as String,
        emailVerified: d['email_verified'] as bool? ?? false,
        locale: d['locale'] as String? ?? 'fr',
        notifyEmail: d['notify_email'] as bool? ?? true,
        isOidc: isOidc,
      );
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  /// Jeton d'accès valide : renouvelé (une seule fois en parallèle) s'il expire dans moins de 30 s.
  Future<String> validToken() async {
    final t = _tokens;
    if (t == null) return state.valueOrNull?.token ?? '';
    if (!t.expiresSoon || t.refreshToken == null) return t.accessToken;
    _refreshing ??= ref.read(oidcClientProvider).refresh(t).whenComplete(() => _refreshing = null);
    final fresh = await _refreshing!;
    await _saveTokens(fresh);
    final current = state.valueOrNull;
    if (current != null) state = AsyncData(current.copyWith(token: fresh.accessToken));
    return fresh.accessToken;
  }

  /// Ouvre la connexion (ou l'inscription) du fournisseur d'identité. Sur le web, la page est remplacée.
  Future<void> signIn({bool register = false, String? locale, String identity = 'google'}) async {
    if (!OidcClient.configured) {
      throw ApiException('La connexion sécurisée n’est pas configurée sur cette version.');
    }
    final client = ref.read(oidcClientProvider);
    final pending = client.newLogin(OidcPlatform.redirectUri());
    final result = await OidcPlatform.authenticate(
        client.authorizeUrl(pending, register: register, locale: locale, identity: identity), pending);
    if (result == null) return; // web : la suite se fait au retour sur l'application
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      await _completeLogin(result, pending);
      if (_tokens == null) return null;
      return _me(_tokens!.accessToken, isOidc: true);
    });
  }

  Future<void> devLogin(String email) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      try {
        final res =
            await ref.read(rawDioProvider).post<Map<String, dynamic>>('/auth/dev/login', data: {'email': email});
        final token = res.data!['access_token'] as String;
        final session = await _me(token);
        _tokens = null;
        await ref.read(tokenStoreProvider).write(token);
        return session;
      } on DioException catch (e) {
        throw ApiException.fromDio(e);
      }
    });
  }

  void applyProfile({String? displayName, String? locale, bool? notifyEmail}) {
    final current = state.valueOrNull;
    if (current != null) {
      state = AsyncData(current.copyWith(displayName: displayName, locale: locale, notifyEmail: notifyEmail));
    }
  }

  Future<void> _clearLocal() async {
    _tokens = null;
    await ref.read(tokenStoreProvider).clear();
  }

  /// Ferme la session locale ; `remote` ferme aussi la session chez le fournisseur d'identité.
  Future<void> logout({bool remote = true}) async {
    final tokens = _tokens;
    await _clearLocal();
    state = const AsyncData(null);
    if (remote && tokens != null) {
      await OidcPlatform.openLogout(ref.read(oidcClientProvider).logoutUrl(tokens, OidcPlatform.redirectUri()));
    }
  }
}

final authProvider = AsyncNotifierProvider<AuthController, AuthSession?>(AuthController.new);

/// Client authentifié : ajoute un jeton valide (renouvelé au besoin) ; un 401 ferme la session locale.
final authDioProvider = Provider<Dio>((ref) {
  final dio = Dio(ref.read(rawDioProvider).options);
  dio.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) async {
      if (ref.read(authProvider).valueOrNull != null) {
        try {
          options.headers['Authorization'] = 'Bearer ${await ref.read(authProvider.notifier).validToken()}';
        } on ApiException {
          await ref.read(authProvider.notifier).logout(remote: false);
        }
      }
      handler.next(options);
    },
    onError: (e, handler) {
      // Seul un jeton refusé ferme la session (pas une requête partie avant sa restauration).
      final sentToken = e.requestOptions.headers['Authorization'] != null;
      if (e.response?.statusCode == 401 && sentToken) ref.read(authProvider.notifier).logout(remote: false);
      handler.next(e);
    },
  ));
  return dio;
});
