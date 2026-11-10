import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:xpass_mobile/core/l10n.dart';

import 'package:xpass_mobile/core/auth.dart';
import 'package:xpass_mobile/core/theme.dart';
import 'package:xpass_mobile/features/booking/booking_repository.dart';
import 'package:xpass_mobile/features/booking/calendar_screen.dart';
import 'package:xpass_mobile/features/booking/credits_screen.dart';
import 'package:xpass_mobile/features/booking/models.dart';
import 'package:xpass_mobile/features/catalog/catalog_repository.dart';

class _MemoryTokens implements TokenStore {
  String? token;
  @override
  Future<void> clear() async => token = null;
  @override
  Future<String?> read() async => token;
  @override
  Future<void> write(String t) async => token = t;
}

class _SignedIn extends AuthController {
  @override
  Future<AuthSession?> build() async => const AuthSession(token: 't', displayName: 'Camille', email: 'c@x.demo');
}

final _bookingJson = {
  'id': 'b1',
  'status': 'held',
  'location': {
    'slug': 'atelier-belle-venue',
    'name': 'Atelier Belle venue',
    'kind_label': 'Salon de coiffure',
    'district_label': 'Paris 11e',
    'address': '12 rue Oberkampf, 75011 Paris',
    'category_slug': 'beaute',
    'category_name': 'Beauté',
    'cover_image_key': null,
  },
  'offer_id': 'o1',
  'offer_title': 'Coupe et coiffage',
  'duration_min': 30,
  'resource_name': 'Sarah',
  'starts_at': '2026-11-12T15:00:00Z',
  'local_start': '2026-11-12T16:00:00',
  'timezone': 'Europe/Paris',
  'party_size': 1,
  'price_credits_per_person': 18,
  'total_credits': 18,
  'funding': [
    {'source': 'employer', 'credits': 12},
    {'source': 'personal', 'credits': 6},
  ],
  'hold_expires_at': '2026-11-01T10:05:00Z',
  'hold_seconds_remaining': 272,
  'free_cancellation_until': '2026-11-11T15:00:00Z',
  'local_free_cancellation_until': '2026-11-11T16:00:00',
  'late_cancellation': false,
  'created_at': '2026-11-01T10:00:00Z',
  'confirmed_at': null,
  'cancelled_at': null,
};

Availability _availability() => const Availability(
      offerId: 'o1',
      offerTitle: 'Coupe et coiffage',
      bookingMode: 'resource_slot',
      durationMin: 30,
      priceCredits: 18,
      participantsMin: 1,
      participantsMax: 1,
      locationName: 'Atelier Belle venue',
      cityName: 'Paris',
      date: '2026-11-12',
      days: [('2026-11-12', true), ('2026-11-15', false)],
      resources: [
        BookableResource(id: 'r1', name: 'Sarah', roleLabel: 'Coiffeuse'),
        BookableResource(id: 'r2', name: 'Lina', roleLabel: 'Coloriste'),
      ],
      slots: [
        Slot(startsAt: '2026-11-12T14:00:00+01:00', localTime: '14:00', available: true, freeResourceIds: ['r1', 'r2'], priceCredits: 18),
        Slot(startsAt: '2026-11-12T15:00:00+01:00', localTime: '15:00', available: false, freeResourceIds: [], priceCredits: 18),
        Slot(startsAt: '2026-11-12T16:00:00+01:00', localTime: '16:00', available: true, freeResourceIds: ['r2'], priceCredits: 22, priceAdjustments: ['peak']),
      ],
    );

void main() {
  setUpAll(() => useGoogleFonts = false);

  test('parse une réservation et sa répartition par source', () {
    final b = Booking.fromJson(_bookingJson);
    expect(b.isHeld, isTrue);
    expect(b.localStart, DateTime(2026, 11, 12, 16));
    expect(b.funding.map((f) => (f.label, f.credits)), [('Crédits Employeur', 12), ('Crédits Personnel', 6)]);
    expect(b.holdSecondsRemaining, 272);
  });

  testWidgets('calendrier : créneaux libres, complets et filtre professionnel', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(ProviderScope(
      overrides: [
        tokenStoreProvider.overrideWithValue(_MemoryTokens()),
        availabilityProvider.overrideWith((ref, key) async => _availability()),
        locationDetailProvider.overrideWith((ref, slug) => Future.error('hors ligne')),
      ],
      child: const MaterialApp(
          locale: Locale('fr'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: CalendarScreen(locationSlug: 'atelier-belle-venue', offerId: 'o1')),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Choisir mon créneau'), findsOneWidget);
    expect(find.text('Complet'), findsOneWidget);
    expect(find.text('Continuer · 18 crédits'), findsOneWidget);
    // Bouton inactif tant qu'aucun horaire n'est choisi.
    final button = tester.widget<FilledButton>(find.byType(FilledButton));
    expect(button.onPressed, isNull);

    await tester.tap(find.text('16:00'));
    await tester.pump();
    // Créneau en heure de pointe : le prix du créneau (22) remplace le prix de base (18).
    expect(find.text('Continuer · 22 crédits'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Avec Lina · 1 personne'), 200,
        scrollable: find.byWidgetPredicate((w) => w is Scrollable && w.axisDirection == AxisDirection.down).first);
    expect(find.text('Avec Lina · 1 personne'), findsOneWidget);
  });

  testWidgets('mes crédits : soldes réels de l’API, aucun chiffre inventé', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);

    final wallet = WalletSummary(
      available: 122,
      reserved: 18,
      bySource: const {'personal': (50, 0), 'employer': (70, 0), 'promotional': (2, 18)},
      lots: [
        CreditLot(
            source: 'promotional',
            label: 'Promo',
            available: 2,
            reserved: 18,
            expiresAt: DateTime(2026, 11, 30),
            isDemo: true)
      ],
    );
    await tester.pumpWidget(ProviderScope(
      overrides: [
        authProvider.overrideWith(_SignedIn.new),
        walletProvider.overrideWith((ref) async => wallet),
        walletHistoryProvider.overrideWith((ref) async => const []),
      ],
      child: const MaterialApp(
          locale: Locale('fr'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: CreditsScreen()),
    ));
    await tester.pumpAndSettle();

    expect(find.text('122'), findsOneWidget);
    expect(find.text('18'), findsOneWidget);
    expect(find.text('52'), findsOneWidget); // personnel 50 + promotionnel 2
    expect(find.text('70'), findsOneWidget);
    expect(find.textContaining('démonstration'), findsOneWidget);
  });
}
