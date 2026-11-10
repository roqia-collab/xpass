import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:xpass_mobile/core/l10n.dart';

import 'package:xpass_mobile/core/theme.dart';
import 'package:xpass_mobile/features/account/employer_invitations.dart';
import 'package:xpass_mobile/features/booking/booking_repository.dart';

class _Repo extends BookingRepository {
  _Repo() : super(Dio(), Dio());
  final accepted = <String>[];

  @override
  Future<void> acceptEmployerInvitation(String id) async => accepted.add(id);
}

void main() {
  setUpAll(() => useGoogleFonts = false);

  testWidgets('invitation employeur : affichée puis acceptée via l’API', (tester) async {
    final repo = _Repo();
    await tester.pumpWidget(ProviderScope(
      overrides: [
        bookingRepositoryProvider.overrideWithValue(repo),
        employerInvitationsProvider.overrideWith((ref) async => [('e1', 'Entreprise Démo Horizon')]),
      ],
      child: const MaterialApp(
          locale: Locale('fr'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: Scaffold(body: SingleChildScrollView(child: EmployerInvitations()))),
    ));
    await tester.pumpAndSettle();
    expect(find.textContaining('Entreprise Démo Horizon vous invite'), findsOneWidget);
    expect(find.textContaining('ne voit pas le détail'), findsOneWidget);
    await tester.tap(find.text('Accepter l’invitation'));
    await tester.pumpAndSettle();
    expect(repo.accepted, ['e1']);
  });
}
