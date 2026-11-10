import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:xpass_mobile/core/l10n.dart';

import 'package:xpass_mobile/core/auth.dart';
import 'package:xpass_mobile/core/theme.dart';
import 'package:xpass_mobile/features/account/subscription_screen.dart';
import 'package:xpass_mobile/features/booking/booking_repository.dart';
import 'package:xpass_mobile/features/booking/models.dart';

class _SignedIn extends AuthController {
  @override
  Future<AuthSession?> build() async => const AuthSession(token: 't', displayName: 'Camille', email: 'c@x.demo');
}

const _plan = Plan(
    code: 'essentiel',
    name: 'XPASS Essentiel',
    priceMinor: 10000,
    currency: 'EUR',
    creditsPerPeriod: 100,
    isDemo: true);

Future<void> _pump(WidgetTester tester, SubscriptionInfo info, {String? retour}) async {
  tester.view.physicalSize = const Size(1080, 2600);
  tester.view.devicePixelRatio = 2.5;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(ProviderScope(
    overrides: [
      authProvider.overrideWith(_SignedIn.new),
      subscriptionProvider.overrideWith((ref) async => info),
      plansProvider.overrideWith((ref) async => [_plan]),
    ],
    child: MaterialApp(
        locale: const Locale('fr'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: SubscriptionScreen(returnedFrom: retour)),
  ));
  if (retour == 'paiement') {
    await tester.pump();
    await tester.pump();
  } else {
    await tester.pumpAndSettle();
  }
}

void main() {
  setUpAll(() => useGoogleFonts = false);

  testWidgets('sans abonnement : offre, bac à sable signalé, aucun prélèvement', (tester) async {
    await _pump(
        tester, const SubscriptionInfo(paymentsEnabled: true, sandbox: true, cancelAtPeriodEnd: false, invoices: []));
    expect(find.textContaining('S’abonner · 100,00 € / mois'), findsOneWidget);
    expect(find.textContaining('aucun argent réel'), findsOneWidget);
    expect(find.text('Formule illustrative'), findsOneWidget);
    expect(find.text('Aucun prélèvement pour le moment.'), findsOneWidget);
  });

  testWidgets('retour de paiement : attente de confirmation, pas de succès affiché', (tester) async {
    await _pump(
        tester, const SubscriptionInfo(paymentsEnabled: true, sandbox: false, cancelAtPeriodEnd: false, invoices: []),
        retour: 'paiement');
    expect(find.textContaining('Paiement en cours de confirmation'), findsOneWidget);
    expect(find.text('Actif'), findsNothing);
    await tester.pumpWidget(const SizedBox()); // arrête l'interrogation périodique
  });

  testWidgets('abonnement actif : renouvellement et prélèvements', (tester) async {
    await _pump(
        tester,
        SubscriptionInfo(
          paymentsEnabled: true,
          sandbox: false,
          status: 'active',
          plan: _plan,
          currentPeriodEnd: DateTime(2026, 12, 1),
          cancelAtPeriodEnd: false,
          invoices: [
            InvoiceLine(
                paidAt: DateTime(2026, 11, 1),
                planName: 'XPASS Essentiel',
                amountMinor: 10000,
                currency: 'EUR',
                livemode: true),
          ],
        ));
    expect(find.text('Actif'), findsOneWidget);
    expect(find.text('Prochain renouvellement'), findsOneWidget);
    expect(find.text('1 décembre 2026'), findsOneWidget);
    expect(find.byType(Switch), findsOneWidget);
    // Report des crédits non utilisés, puis prélèvements plus bas dans la page.
    await tester.scrollUntilVisible(find.text('Crédits non utilisés'), 300);
    expect(find.textContaining('sont reportés au mois suivant'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('100,00 €'), 300);
    expect(find.text('100,00 €'), findsOneWidget);
  });
}
