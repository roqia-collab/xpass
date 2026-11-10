import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:xpass_mobile/core/l10n.dart';

import 'package:xpass_mobile/core/theme.dart';
import 'package:xpass_mobile/features/booking/booking_repository.dart';
import 'package:xpass_mobile/features/booking/dispute_sheet.dart';
import 'package:xpass_mobile/features/booking/models.dart';

class _Repo extends BookingRepository {
  _Repo() : super(Dio(), Dio());
  final sent = <String>[];

  @override
  Future<void> openDispute(String bookingId, String reason) async => sent.add('$bookingId:$reason');
}

void main() {
  setUpAll(() => useGoogleFonts = false);

  testWidgets('réclamation envoyée à l’API', (tester) async {
    final repo = _Repo();
    await tester.pumpWidget(ProviderScope(
      overrides: [
        bookingRepositoryProvider.overrideWithValue(repo),
        disputesProvider.overrideWith((ref, id) async => const <DisputeInfo>[]),
      ],
      child: const MaterialApp(
          locale: Locale('fr'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: Scaffold(body: DisputeForm(bookingId: 'b1'))),
    ));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Atelier différent de l’annonce');
    await tester.tap(find.text('Envoyer la réclamation'));
    await tester.pumpAndSettle();
    expect(repo.sent, ['b1:Atelier différent de l’annonce']);
  });

  test('résumé d’une réclamation close', () {
    const d = DisputeInfo(reference: 'L-1001', status: 'resolved_refund', creditsRestored: 18);
    expect(d.isOpen, isFalse);
    expect(d.summary, 'Réclamation L-1001 : 18 crédits vous ont été restitués.');
  });
}
