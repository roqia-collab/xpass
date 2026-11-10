import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/auth.dart';
import 'core/l10n.dart';
import 'core/oidc_platform.dart';
import 'core/router.dart';
import 'core/theme.dart';
import 'features/account/login_sheet.dart' show preferredLocaleProvider;
import 'features/account/notifications_screen.dart';

void main() {
  // Erreurs non interceptées : journalisées avec leur message (un service de suivi pourra s'y brancher).
  PlatformDispatcher.instance.onError = (error, stack) {
    debugPrint('XPASS erreur non interceptée : $error');
    return true;
  };
  // Retour de la page de connexion (web) : traité avant que le routeur ne lise l'adresse.
  OidcPlatform.captureCallback();
  runApp(const ProviderScope(child: XpassApp()));
}

class XpassApp extends ConsumerWidget {
  const XpassApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => NotificationBridge(
        child: MaterialApp.router(
          title: 'XPASS',
          debugShowCheckedModeBanner: false,
          theme: buildTheme(),
          routerConfig: appRouter,
          // Langue du compte, sinon celle choisie avant connexion. L'arabe passe l'interface de droite à gauche.
          locale: Locale(ref.watch(authProvider).valueOrNull?.locale ?? ref.watch(preferredLocaleProvider)),
          supportedLocales: AppLocalizations.supportedLocales,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
        ),
      );
}
