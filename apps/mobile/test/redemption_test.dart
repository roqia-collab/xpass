import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:xpass_mobile/core/l10n.dart';
import 'package:qr_flutter/qr_flutter.dart';

import 'package:xpass_mobile/core/theme.dart';
import 'package:xpass_mobile/features/booking/booking_detail_screen.dart';
import 'package:xpass_mobile/features/booking/booking_repository.dart';
import 'package:xpass_mobile/features/booking/models.dart';
import 'package:xpass_mobile/features/booking/receipt_screen.dart';

class _FakeRepo extends BookingRepository {
  _FakeRepo() : super(Dio(), Dio());
  int issued = 0;

  @override
  Future<PassInfo> issuePass(String id) async {
    issued++;
    return const PassInfo(qrPayload: 'XPASS1:opaque-token', manualCode: 'K7Q2-M9XP', expiresIn: 60);
  }
}

ReceiptInfo _receipt({String? reviewUrl}) => ReceiptInfo(
      reference: 'XP-10482',
      locationName: 'Atelier Belle venue',
      offerTitle: 'Coupe et coiffage',
      cityName: 'Paris',
      coverImageKey: null,
      localRedeemedAt: DateTime(2026, 11, 12, 16, 32),
      creditsTotal: 18,
      funding: const [Funding('employer', 12), Funding('personal', 6)],
      reviewUrl: reviewUrl,
    );

void main() {
  setUpAll(() => useGoogleFonts = false);

  testWidgets('le QR et le code manuel viennent du serveur', (tester) async {
    final repo = _FakeRepo();
    await tester.pumpWidget(ProviderScope(
      overrides: [bookingRepositoryProvider.overrideWithValue(repo)],
      child: const MaterialApp(
          locale: Locale('fr'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: Scaffold(body: SingleChildScrollView(child: PassPanel(bookingId: 'b1')))),
    ));
    await tester.pump();
    await tester.pump();
    expect(repo.issued, 1);
    expect(find.byType(QrImageView), findsOneWidget);
    expect(find.text('Code : K7Q2-M9XP'), findsOneWidget);
    expect(find.text('À présenter au partenaire'), findsOneWidget);
    await tester.pumpWidget(const SizedBox()); // arrête les minuteries
  });

  for (final url in [null, 'https://g.page/r/exemple/review']) {
    testWidgets('reçu : lien d’avis ${url == null ? 'absent' : 'présent'}', (tester) async {
      tester.view.physicalSize = const Size(1080, 3200);
      tester.view.devicePixelRatio = 2.5;
      addTearDown(tester.view.reset);
      await tester.pumpWidget(ProviderScope(
        overrides: [receiptProvider.overrideWith((ref, id) async => _receipt(reviewUrl: url))],
        child: const MaterialApp(
            locale: Locale('fr'),
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: ReceiptScreen(bookingId: 'b1')),
      ));
      await tester.pumpAndSettle();
      expect(find.text('XP-10482'), findsOneWidget);
      expect(find.text('Crédits Employeur'), findsOneWidget);
      expect(find.text('Donner mon avis sur Google'), url == null ? findsNothing : findsOneWidget);
    });
  }
}
