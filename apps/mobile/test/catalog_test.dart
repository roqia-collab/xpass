import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:xpass_mobile/core/l10n.dart';

import 'package:xpass_mobile/core/auth.dart';
import 'package:xpass_mobile/core/format.dart' as fmt;
import 'package:xpass_mobile/core/theme.dart';
import 'package:xpass_mobile/features/account/account_repository.dart';
import 'package:xpass_mobile/features/catalog/catalog_repository.dart';
import 'package:xpass_mobile/features/catalog/models.dart';
import 'package:xpass_mobile/features/explore/home_screen.dart';

Map<String, dynamic> _offer({String mode = 'resource_slot', Map<String, dynamic>? slot}) => {
      'id': 'o1',
      'version_id': 'v1',
      'title': 'Coupe et coiffage',
      'summary': '',
      'includes': 'coupe et coiffage',
      'language': null,
      'duration_min': 30,
      'price_credits': 18,
      'booking_mode': mode,
      'participants_min': 1,
      'participants_max': 1,
      'capacity': null,
      'free_cancellation_hours': 24,
      'external_ticket_note': null,
      'image_key': null,
      'next_slot': slot,
    };

Map<String, dynamic> _card() => {
      'id': 'l1',
      'slug': 'atelier-belle-venue',
      'name': 'Atelier Belle venue',
      'kind_label': 'Salon de coiffure',
      'category_slug': 'beaute',
      'category_name': 'Beauté',
      'subcategory_slug': 'coiffure',
      'subcategory_name': 'Coiffure',
      'city_slug': 'paris',
      'district_label': 'Paris 11e',
      'cover_image_key': null,
      'distance_m': 812,
      'wheelchair_accessible': true,
      'meeting_point': null,
      'featured_offer': _offer(slot: {
        'starts_at': '2026-11-12T16:00:00+01:00',
        'local_start': '2026-11-12T16:00:00',
        'resource_name': 'Sarah',
        'indicative': true
      }),
      'is_demo': true,
    };

void main() {
  setUpAll(() => useGoogleFonts = false);

  test('parse une carte établissement', () {
    final card = LocationCard.fromJson(_card());
    expect(card.name, 'Atelier Belle venue');
    expect(card.featuredOffer!.priceCredits, 18);
    expect(card.featuredOffer!.nextSlot!.indicative, isTrue);
    expect(card.featuredOffer!.nextSlot!.resourceName, 'Sarah');
  });

  test('formats français', () {
    final now = DateTime(2026, 11, 12, 9);
    expect(fmt.slotLabel(DateTime(2026, 11, 12, 18, 30), now: now), "Aujourd'hui à 18:30");
    expect(fmt.slotLabel(DateTime(2026, 11, 13, 10), now: now), 'Demain à 10:00');
    expect(fmt.slotLabel(DateTime(2026, 11, 19, 16), now: now), 'jeudi 19 novembre à 16:00');
    expect(fmt.credits(1), '1 crédit');
    expect(fmt.credits(18), '18 crédits');
    expect(fmt.duration(90), '1 h 30');
    expect(fmt.distance(812), '800 m');
    expect(fmt.distance(1520), '1,5 km');
    expect(fmt.distance(976), '1,0 km');
    expect(fmt.shortDate(DateTime(2026, 11, 30)), '30 nov. 2026');
    expect(fmt.money(10000, 'EUR'), '100,00 €');
    expect(fmt.money(-1250, 'EUR'), '−12,50 €');
    expect(fmt.money(123456789, 'EUR'), '1 234 567,89 €');
    expect(fmt.shortDate(DateTime(2026, 7, 3)), '3 juil. 2026');
    expect(fmt.weekdayShortDay(DateTime(2026, 11, 6)), 'ven. 6');
    expect(fmt.dateOnly(DateTime(2026, 11, 6, 18, 30)), DateTime(2026, 11, 6));
  });

  testWidgets('accueil : univers et établissements venant de l’API', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);

    final categories = [
      for (final (slug, name) in [
        ('divertissement', 'Divertissement'),
        ('sport', 'Activité sportive'),
        ('culture', 'Activité culturelle'),
        ('beaute', 'Beauté')
      ])
        Category(
          slug: slug,
          name: name,
          eyebrow: name.toUpperCase(),
          headline: name,
          tagline: '',
          ctaLabel: 'Voir',
          tileImageKey: null,
          heroImageKey: null,
          subcategories: const [],
        ),
    ];
    final page = LocationPage(items: [LocationCard.fromJson(_card())], total: 1);

    await tester.pumpWidget(ProviderScope(
      overrides: [
        authProvider.overrideWith(_SignedOut.new),
        categoriesProvider.overrideWith((ref) async => categories),
        locationSearchProvider.overrideWith((ref, query) async => page),
        unreadNotificationCountProvider.overrideWithValue(0),
      ],
      child: const MaterialApp(
          locale: Locale('fr'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: HomeScreen()),
    ));
    await tester.pump();
    await tester.pump();

    expect(find.text('Divertissement'), findsWidgets);
    expect(find.text('Beauté'), findsWidgets);
    expect(find.text('À réserver près de vous'), findsOneWidget);
    expect(find.text("Aujourd'hui"), findsOneWidget);
    expect(find.text('Tout'), findsOneWidget);
    expect(find.text('Atelier Belle venue'), findsOneWidget);
    // Aucun solde inventé sans compte connecté.
    expect(find.textContaining('120'), findsNothing);
  });
}

class _SignedOut extends AuthController {
  @override
  Future<AuthSession?> build() async => null;
}
