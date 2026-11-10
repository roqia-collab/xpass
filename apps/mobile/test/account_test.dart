import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:xpass_mobile/core/l10n.dart';

import 'package:xpass_mobile/core/auth.dart';
import 'package:xpass_mobile/core/oidc.dart';
import 'package:xpass_mobile/core/theme.dart';
import 'package:xpass_mobile/features/account/account_repository.dart';
import 'package:xpass_mobile/features/account/profile_screen.dart';
import 'package:xpass_mobile/features/booking/booking_repository.dart';

class _SignedIn extends AuthController {
  @override
  Future<AuthSession?> build() async => const AuthSession(
      token: 't', displayName: 'Camille Martin', email: 'cm@exemple.fr', emailVerified: true, isOidc: true);
}

class _SignedOut extends AuthController {
  @override
  Future<AuthSession?> build() async => null;
}

void main() {
  setUpAll(() => useGoogleFonts = false);

  test('PKCE : défi S256 conforme (base64url sans remplissage)', () {
    expect(pkceChallenge('xpass-test-verifier-0123456789-abcdefghijklmnopqrstuvwxyz'),
        'fS-r1vJELKCHm0HUzacnAQETR8zLMlkoOiWL9iTd3Zw');
  });

  test('URL d’autorisation : code + PKCE, jamais de secret', () {
    final client = OidcClient(Dio());
    final pending = client.newLogin('http://localhost:5173/');
    final url = client.authorizeUrl(pending, register: true, locale: 'en');
    expect(url.path, endsWith('/protocol/openid-connect/registrations'));
    expect(url.queryParameters['response_type'], 'code');
    expect(url.queryParameters['code_challenge_method'], 'S256');
    expect(url.queryParameters['code_challenge'], pkceChallenge(pending.verifier));
    expect(url.queryParameters['state'], pending.state);
    expect(url.queryParameters['ui_locales'], 'en');
    expect(url.queryParameters.containsKey('client_secret'), isFalse);
    expect(pending.verifier.length, greaterThanOrEqualTo(43));
  });

  test('jetons : renouvellement 30 s avant expiration, refresh conservé', () {
    final t = TokenSet.fromTokenResponse({'access_token': 'a', 'expires_in': 20}, previousRefresh: 'r');
    expect(t.expiresSoon, isTrue);
    expect(t.refreshToken, 'r');
    expect(TokenSet.fromJson(t.toJson()).accessToken, 'a');
  });

  testWidgets('paramètres (écran 16) : espace, aide, compte, e-mail vérifié', (tester) async {
    tester.view.physicalSize = const Size(1080, 9000);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(ProviderScope(
      overrides: [
        authProvider.overrideWith(_SignedIn.new),
        employerInvitationsProvider.overrideWith((ref) async => const []),
        supportRequestsProvider.overrideWith((ref) async => const []),
      ],
      child: const MaterialApp(
          locale: Locale('fr'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: ProfileScreen()),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Paramètres'), findsWidgets);
    expect(find.text('Adresse e-mail vérifiée'), findsOneWidget);
    // Titres de section affichés en capitales (style éditorial).
    for (final s in ['Mon espace', 'Aide', 'Compte']) {
      expect(find.text(s.toUpperCase()), findsOneWidget);
    }
    expect(find.text('Mes favoris'), findsOneWidget);
    expect(find.text('Réalisée par Alystra'), findsOneWidget);
  });

  testWidgets('paramètres : compte, préférences, notifications, confidentialité, zone sensible', (tester) async {
    tester.view.physicalSize = const Size(1080, 9000);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(ProviderScope(
      overrides: [authProvider.overrideWith(_SignedIn.new)],
      child: const MaterialApp(
          locale: Locale('fr'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: SettingsScreen()),
    ));
    await tester.pumpAndSettle();
    for (final s in ['Compte', 'Préférences', 'Notifications', 'Confidentialité', 'À propos', 'Zone sensible']) {
      expect(find.text(s.toUpperCase()), findsOneWidget);
    }
    expect(find.text('Exporter mes données'), findsOneWidget);
    expect(find.text('Supprimer mon compte'), findsOneWidget);
    expect(find.text('Se déconnecter'), findsOneWidget);
  });

  testWidgets('non connecté : écran 02 avec exploration sans compte', (tester) async {
    tester.view.physicalSize = const Size(1080, 2600);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(ProviderScope(
      overrides: [authProvider.overrideWith(_SignedOut.new)],
      child: const MaterialApp(
          locale: Locale('fr'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: ProfileScreen()),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Un pass, toutes vos envies'), findsOneWidget);
    expect(find.text('Explorer sans compte'), findsOneWidget);
  });

  for (final (locale, title, section) in [('ar', 'الإعدادات', 'مساحتي'), ('en', 'Settings', 'My space')]) {
    testWidgets('profil en $locale : textes traduits, sens de lecture, aucun débordement', (tester) async {
      tester.view.physicalSize = const Size(1080, 4200);
      tester.view.devicePixelRatio = 2.5;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(ProviderScope(
        overrides: [
          authProvider.overrideWith(_SignedIn.new),
          employerInvitationsProvider.overrideWith((ref) async => const []),
          supportRequestsProvider.overrideWith((ref) async => const []),
        ],
        child: MaterialApp(
          locale: Locale(locale),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: const ProfileScreen(),
        ),
      ));
      await tester.pumpAndSettle();
      expect(find.text(title), findsOneWidget);
      expect(find.text(section.toUpperCase()), findsOneWidget);
      final direction = Directionality.of(tester.element(find.text(title)));
      expect(direction, locale == 'ar' ? TextDirection.rtl : TextDirection.ltr);
    });
  }

  testWidgets('grands textes (×1,6) : écran 02 sans débordement', (tester) async {
    tester.view.physicalSize = const Size(1080, 3000);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(ProviderScope(
      overrides: [authProvider.overrideWith(_SignedOut.new)],
      child: MaterialApp(
        locale: const Locale('fr'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context).copyWith(textScaler: const TextScaler.linear(1.6)),
          child: child!,
        ),
        home: const ProfileScreen(),
      ),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Un pass, toutes vos envies'), findsOneWidget);
    expect(find.text('Explorer sans compte'), findsOneWidget);
  });
}
