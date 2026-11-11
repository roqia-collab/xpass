/// Modèles du catalogue, alignés sur contracts/openapi.json.
library;

class Subcategory {
  const Subcategory({required this.slug, required this.name, required this.icon});
  final String slug;
  final String name;
  final String icon;

  factory Subcategory.fromJson(Map<String, dynamic> j) =>
      Subcategory(slug: j['slug'] as String, name: j['name'] as String, icon: j['icon'] as String);
}

class Category {
  const Category({
    required this.slug,
    required this.name,
    required this.eyebrow,
    required this.headline,
    required this.tagline,
    required this.ctaLabel,
    required this.tileImageKey,
    required this.heroImageKey,
    required this.subcategories,
  });

  final String slug;
  final String name;
  final String eyebrow;
  final String headline;
  final String tagline;
  final String ctaLabel;
  final String? tileImageKey;
  final String? heroImageKey;
  final List<Subcategory> subcategories;

  factory Category.fromJson(Map<String, dynamic> j) => Category(
        slug: j['slug'] as String,
        name: j['name'] as String,
        eyebrow: j['eyebrow'] as String,
        headline: j['headline'] as String,
        tagline: j['tagline'] as String,
        ctaLabel: j['cta_label'] as String,
        tileImageKey: j['tile_image_key'] as String?,
        heroImageKey: j['hero_image_key'] as String?,
        subcategories:
            (j['subcategories'] as List).map((e) => Subcategory.fromJson(e as Map<String, dynamic>)).toList(),
      );
}

class City {
  const City({required this.slug, required this.name, this.latitude, this.longitude});
  final String slug;
  final String name;
  final double? latitude;
  final double? longitude;

  factory City.fromJson(Map<String, dynamic> j) => City(
        slug: j['slug'] as String,
        name: j['name'] as String,
        latitude: (j['latitude'] as num?)?.toDouble(),
        longitude: (j['longitude'] as num?)?.toDouble(),
      );
}

class NextSlot {
  const NextSlot({required this.startsAt, required this.localStart, this.resourceName, required this.indicative});

  /// Instant absolu (UTC).
  final DateTime startsAt;

  /// Heure murale dans le fuseau de l'établissement, à afficher telle quelle.
  final DateTime localStart;
  final String? resourceName;

  /// Vrai tant que le moteur de disponibilité réel (lot 2) n'est pas en place.
  final bool indicative;

  factory NextSlot.fromJson(Map<String, dynamic> j) => NextSlot(
        startsAt: DateTime.parse(j['starts_at'] as String),
        localStart: DateTime.parse(j['local_start'] as String),
        resourceName: j['resource_name'] as String?,
        indicative: j['indicative'] as bool? ?? true,
      );
}

class Offer {
  const Offer({
    required this.id,
    required this.title,
    required this.summary,
    required this.includes,
    required this.language,
    required this.durationMin,
    required this.priceCredits,
    required this.bookingMode,
    required this.participantsMax,
    required this.capacity,
    required this.freeCancellationHours,
    required this.externalTicketNote,
    required this.imageKey,
    required this.nextSlot,
  });

  final String id;
  final String title;
  final String summary;
  final String? includes;
  final String? language;
  final int durationMin;
  final int priceCredits;
  final String bookingMode;
  final int participantsMax;
  final int? capacity;
  final int freeCancellationHours;
  final String? externalTicketNote;
  final String? imageKey;
  final NextSlot? nextSlot;

  bool get isExternalTicket => bookingMode == 'external_ticket';
  bool get isOpenAccess => bookingMode == 'open_access';

  factory Offer.fromJson(Map<String, dynamic> j) => Offer(
        id: j['id'] as String,
        title: j['title'] as String,
        summary: j['summary'] as String? ?? '',
        includes: j['includes'] as String?,
        language: j['language'] as String?,
        durationMin: j['duration_min'] as int,
        priceCredits: j['price_credits'] as int,
        bookingMode: j['booking_mode'] as String,
        participantsMax: j['participants_max'] as int? ?? 1,
        capacity: j['capacity'] as int?,
        freeCancellationHours: j['free_cancellation_hours'] as int? ?? 24,
        externalTicketNote: j['external_ticket_note'] as String?,
        imageKey: j['image_key'] as String?,
        nextSlot: j['next_slot'] == null ? null : NextSlot.fromJson(j['next_slot'] as Map<String, dynamic>),
      );
}

class LocationCard {
  const LocationCard({
    required this.id,
    required this.slug,
    required this.name,
    required this.kindLabel,
    required this.categorySlug,
    required this.subcategorySlug,
    required this.subcategoryName,
    required this.districtLabel,
    required this.coverImageKey,
    required this.distanceM,
    required this.wheelchairAccessible,
    required this.meetingPoint,
    required this.featuredOffer,
    this.latitude,
    this.longitude,
  });

  final String id;
  final String slug;
  final String name;
  final String kindLabel;
  final String categorySlug;
  final String subcategorySlug;
  final String subcategoryName;
  final String districtLabel;
  final String? coverImageKey;
  final int? distanceM;
  final bool wheelchairAccessible;
  final String? meetingPoint;
  final Offer? featuredOffer;
  final double? latitude;
  final double? longitude;

  factory LocationCard.fromJson(Map<String, dynamic> j) => LocationCard(
        id: j['id'] as String,
        slug: j['slug'] as String,
        name: j['name'] as String,
        kindLabel: j['kind_label'] as String,
        categorySlug: j['category_slug'] as String,
        subcategorySlug: j['subcategory_slug'] as String,
        subcategoryName: j['subcategory_name'] as String,
        districtLabel: j['district_label'] as String,
        coverImageKey: j['cover_image_key'] as String?,
        distanceM: j['distance_m'] as int?,
        wheelchairAccessible: j['wheelchair_accessible'] as bool? ?? false,
        meetingPoint: j['meeting_point'] as String?,
        featuredOffer: j['featured_offer'] == null ? null : Offer.fromJson(j['featured_offer'] as Map<String, dynamic>),
        latitude: (j['latitude'] as num?)?.toDouble(),
        longitude: (j['longitude'] as num?)?.toDouble(),
      );
}

class LocationPage {
  const LocationPage({required this.items, required this.total});
  final List<LocationCard> items;
  final int total;

  factory LocationPage.fromJson(Map<String, dynamic> j) => LocationPage(
        items: (j['items'] as List).map((e) => LocationCard.fromJson(e as Map<String, dynamic>)).toList(),
        total: j['total'] as int,
      );
}

class TeamMember {
  const TeamMember({required this.name, required this.roleLabel, required this.kind});
  final String name;
  final String roleLabel;
  final String kind;

  factory TeamMember.fromJson(Map<String, dynamic> j) =>
      TeamMember(name: j['name'] as String, roleLabel: j['role_label'] as String, kind: j['kind'] as String);
}

class LocationDetail {
  const LocationDetail({
    required this.card,
    required this.merchantName,
    required this.description,
    required this.addressLine,
    required this.postalCode,
    required this.cityName,
    required this.accessInfo,
    required this.hoursSummary,
    required this.offers,
    required this.team,
  });

  final LocationCard card;
  final String merchantName;
  final String description;
  final String addressLine;
  final String postalCode;
  final String cityName;
  final String? accessInfo;
  final String hoursSummary;
  final List<Offer> offers;
  final List<TeamMember> team;

  String get fullAddress => '$addressLine, $postalCode $cityName';

  factory LocationDetail.fromJson(Map<String, dynamic> j) => LocationDetail(
        card: LocationCard.fromJson(j),
        merchantName: j['merchant_name'] as String,
        description: j['description'] as String? ?? '',
        addressLine: j['address_line'] as String,
        postalCode: j['postal_code'] as String,
        cityName: j['city_name'] as String,
        accessInfo: j['access_info'] as String?,
        hoursSummary: j['hours_summary'] as String,
        offers: (j['offers'] as List).map((e) => Offer.fromJson(e as Map<String, dynamic>)).toList(),
        team: (j['team'] as List).map((e) => TeamMember.fromJson(e as Map<String, dynamic>)).toList(),
      );
}

/// Événement daté publié par un service RH ou l'admin sur un établissement.
class VenueEvent {
  const VenueEvent({
    required this.id,
    required this.title,
    required this.summary,
    required this.startsAt,
    required this.endsAt,
    required this.priceCredits,
    required this.coverImageKey,
    required this.locationSlug,
    required this.locationName,
    required this.addressLine,
    required this.districtLabel,
    required this.categorySlug,
  });

  final String id;
  final String title;
  final String summary;
  final DateTime startsAt;
  final DateTime endsAt;
  final int priceCredits;
  final String? coverImageKey;
  final String locationSlug;
  final String locationName;
  final String addressLine;
  final String districtLabel;
  final String categorySlug;

  factory VenueEvent.fromJson(Map<String, dynamic> j) => VenueEvent(
        id: j['id'] as String,
        title: j['title'] as String,
        summary: j['summary'] as String? ?? '',
        startsAt: DateTime.parse(j['starts_at'] as String).toLocal(),
        endsAt: DateTime.parse(j['ends_at'] as String).toLocal(),
        priceCredits: j['price_credits'] as int,
        coverImageKey: j['cover_image_key'] as String?,
        locationSlug: j['location_slug'] as String,
        locationName: j['location_name'] as String,
        addressLine: j['address_line'] as String? ?? '',
        districtLabel: j['district_label'] as String? ?? '',
        categorySlug: j['category_slug'] as String? ?? '',
      );
}
