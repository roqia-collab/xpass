/// Modèles réservation et portefeuille, alignés sur contracts/openapi.json.
library;

DateTime _local(String s) => DateTime.parse(s);

class Slot {
  const Slot(
      {required this.startsAt,
      required this.localTime,
      required this.available,
      this.remaining,
      required this.freeResourceIds,
      required this.priceCredits,
      this.priceAdjustments = const []});
  final String startsAt; // ISO avec décalage, renvoyé tel quel à l'API
  final String localTime;
  final bool available;
  final int? remaining;
  final List<String> freeResourceIds;

  /// Prix par personne de ce créneau (heure de pointe, forte demande, dernière minute).
  final int priceCredits;
  final List<String> priceAdjustments;

  bool get isPeak => priceAdjustments.contains('peak');
  bool get isHighDemand => priceAdjustments.contains('demand');
  bool get isLastMinute => priceAdjustments.contains('last_minute');

  factory Slot.fromJson(Map<String, dynamic> j) => Slot(
        startsAt: j['starts_at'] as String,
        localTime: j['local_time'] as String,
        available: j['available'] as bool,
        remaining: j['remaining'] as int?,
        freeResourceIds: (j['free_resource_ids'] as List).cast<String>(),
        priceCredits: j['price_credits'] as int? ?? 0,
        priceAdjustments: (j['price_adjustments'] as List? ?? const []).cast<String>(),
      );
}

class BookableResource {
  const BookableResource({required this.id, required this.name, required this.roleLabel});
  final String id;
  final String name;
  final String roleLabel;
}

class Availability {
  const Availability({
    required this.offerId,
    required this.offerTitle,
    required this.bookingMode,
    required this.durationMin,
    required this.priceCredits,
    required this.participantsMin,
    required this.participantsMax,
    required this.locationName,
    required this.cityName,
    required this.date,
    required this.days,
    required this.resources,
    required this.slots,
  });

  final String offerId;
  final String offerTitle;
  final String bookingMode;
  final int durationMin;
  final int priceCredits;
  final int participantsMin;
  final int participantsMax;
  final String locationName;
  final String cityName;
  final String date;
  final List<(String date, bool open)> days;
  final List<BookableResource> resources;
  final List<Slot> slots;

  factory Availability.fromJson(Map<String, dynamic> j) => Availability(
        offerId: j['offer_id'] as String,
        offerTitle: j['offer_title'] as String,
        bookingMode: j['booking_mode'] as String,
        durationMin: j['duration_min'] as int,
        priceCredits: j['price_credits'] as int,
        participantsMin: j['participants_min'] as int,
        participantsMax: j['participants_max'] as int,
        locationName: j['location_name'] as String,
        cityName: j['city_name'] as String,
        date: j['date'] as String,
        days: [for (final d in j['days'] as List) ((d as Map)['date'] as String, d['open'] as bool)],
        resources: [
          for (final r in j['resources'] as List)
            BookableResource(
                id: (r as Map)['id'] as String, name: r['name'] as String, roleLabel: r['role_label'] as String)
        ],
        slots: (j['slots'] as List).map((e) => Slot.fromJson(e as Map<String, dynamic>)).toList(),
      );
}

class Funding {
  const Funding(this.source, this.credits);
  final String source;
  final int credits;

  String get label => switch (source) {
        'employer' => 'Crédits Employeur',
        'promotional' => 'Crédits promotionnels',
        _ => 'Crédits Personnel',
      };
}

class Booking {
  const Booking({
    required this.id,
    required this.status,
    required this.locationSlug,
    required this.locationName,
    required this.kindLabel,
    required this.categoryName,
    required this.address,
    required this.coverImageKey,
    required this.offerTitle,
    required this.durationMin,
    required this.resourceName,
    required this.localStart,
    required this.partySize,
    required this.totalCredits,
    required this.funding,
    required this.holdSecondsRemaining,
    required this.localFreeCancellationUntil,
    required this.lateCancellation,
    this.receiptReference,
    required this.startsAtUtc,
    this.pricePerPerson = 0,
    this.priceAdjustments = const [],
    this.lateCancellationRefundCredits = 0,
    this.refundedCredits = 0,
  });

  /// Instant absolu (UTC), utilisé pour l'agenda.
  final DateTime startsAtUtc;

  final String id;
  final String status;
  final String locationSlug;
  final String locationName;
  final String kindLabel;
  final String categoryName;
  final String address;
  final String? coverImageKey;
  final String offerTitle;
  final int durationMin;
  final String? resourceName;
  final DateTime localStart;
  final int partySize;
  final int totalCredits;
  final List<Funding> funding;
  final int? holdSecondsRemaining;
  final DateTime localFreeCancellationUntil;
  final bool lateCancellation;
  final String? receiptReference;
  final int pricePerPerson;
  final List<String> priceAdjustments;

  /// Crédits rendus en cas d'annulation après le délai gratuit (la moitié).
  final int lateCancellationRefundCredits;

  /// Crédits effectivement rendus à l'annulation.
  final int refundedCredits;

  bool get isRedeemed => status == 'redeemed';
  bool get isHeld => status == 'held';
  bool get isConfirmed => status == 'confirmed';

  String get statusLabel => switch (status) {
        'held' => 'En attente de confirmation',
        'confirmed' => 'Confirmée',
        'cancelled' => lateCancellation ? 'Annulée (tardive)' : 'Annulée',
        'expired' => 'Expirée',
        'redeemed' => 'Prestation utilisée',
        'no_show' => 'Absence (non présenté)',
        _ => status,
      };

  factory Booking.fromJson(Map<String, dynamic> j) {
    final loc = j['location'] as Map<String, dynamic>;
    return Booking(
      id: j['id'] as String,
      status: j['status'] as String,
      locationSlug: loc['slug'] as String,
      locationName: loc['name'] as String,
      kindLabel: loc['kind_label'] as String,
      categoryName: loc['category_name'] as String,
      address: loc['address'] as String,
      coverImageKey: loc['cover_image_key'] as String?,
      offerTitle: j['offer_title'] as String,
      durationMin: j['duration_min'] as int,
      resourceName: j['resource_name'] as String?,
      localStart: _local(j['local_start'] as String),
      partySize: j['party_size'] as int,
      totalCredits: j['total_credits'] as int,
      funding: [for (final f in j['funding'] as List) Funding((f as Map)['source'] as String, f['credits'] as int)],
      holdSecondsRemaining: j['hold_seconds_remaining'] as int?,
      localFreeCancellationUntil: _local(j['local_free_cancellation_until'] as String),
      lateCancellation: j['late_cancellation'] as bool? ?? false,
      receiptReference: j['receipt_reference'] as String?,
      startsAtUtc: DateTime.parse(j['starts_at'] as String).toUtc(),
      pricePerPerson: j['price_credits_per_person'] as int? ?? 0,
      priceAdjustments: (j['price_adjustments'] as List? ?? const []).cast<String>(),
      lateCancellationRefundCredits: j['late_cancellation_refund_credits'] as int? ?? 0,
      refundedCredits: j['refunded_credits'] as int? ?? 0,
    );
  }
}

/// QR + code court à présenter au partenaire (valables quelques dizaines de secondes).
class PassInfo {
  const PassInfo({required this.qrPayload, required this.manualCode, required this.expiresIn});
  final String qrPayload;
  final String manualCode;
  final int expiresIn;

  factory PassInfo.fromJson(Map<String, dynamic> j) => PassInfo(
        qrPayload: j['qr_payload'] as String,
        manualCode: j['manual_code'] as String,
        expiresIn: j['expires_in'] as int,
      );
}

class ReceiptInfo {
  const ReceiptInfo({
    required this.reference,
    required this.locationName,
    required this.offerTitle,
    required this.cityName,
    required this.coverImageKey,
    required this.localRedeemedAt,
    required this.creditsTotal,
    required this.funding,
    required this.reviewUrl,
  });

  final String reference;
  final String locationName;
  final String offerTitle;
  final String cityName;
  final String? coverImageKey;
  final DateTime localRedeemedAt;
  final int creditsTotal;
  final List<Funding> funding;
  final String? reviewUrl;

  factory ReceiptInfo.fromJson(Map<String, dynamic> j) => ReceiptInfo(
        reference: j['reference'] as String,
        locationName: j['location_name'] as String,
        offerTitle: j['offer_title'] as String,
        cityName: j['city_name'] as String,
        coverImageKey: j['cover_image_key'] as String?,
        localRedeemedAt: DateTime.parse(j['local_redeemed_at'] as String),
        creditsTotal: j['credits_total'] as int,
        funding: [for (final f in j['funding'] as List) Funding((f as Map)['source'] as String, f['credits'] as int)],
        reviewUrl: j['review_url'] as String?,
      );
}

class BookingList {
  const BookingList(this.items, this.counts);
  final List<Booking> items;
  final Map<String, int> counts;

  factory BookingList.fromJson(Map<String, dynamic> j) => BookingList(
        (j['items'] as List).map((e) => Booking.fromJson(e as Map<String, dynamic>)).toList(),
        (j['counts'] as Map).map((k, v) => MapEntry(k as String, v as int)),
      );
}

class CreditLot {
  const CreditLot(
      {required this.source,
      required this.label,
      required this.available,
      required this.reserved,
      this.expiresAt,
      required this.isDemo});
  final String source;
  final String label;
  final int available;
  final int reserved;
  final DateTime? expiresAt;
  final bool isDemo;
}

class WalletSummary {
  const WalletSummary({required this.available, required this.reserved, required this.bySource, required this.lots});
  final int available;
  final int reserved;
  final Map<String, (int available, int reserved)> bySource;
  final List<CreditLot> lots;

  factory WalletSummary.fromJson(Map<String, dynamic> j) => WalletSummary(
        available: j['available'] as int,
        reserved: j['reserved'] as int,
        bySource: (j['by_source'] as Map)
            .map((k, v) => MapEntry(k as String, ((v as Map)['available'] as int, v['reserved'] as int))),
        lots: [
          for (final l in j['lots'] as List)
            CreditLot(
              source: (l as Map)['source'] as String,
              label: l['label'] as String,
              available: l['available'] as int,
              reserved: l['reserved'] as int,
              expiresAt: l['expires_at'] == null ? null : DateTime.parse(l['expires_at'] as String).toLocal(),
              isDemo: l['is_demo'] as bool? ?? false,
            ),
        ],
      );
}

class HistoryEntry {
  const HistoryEntry(
      {required this.kind,
      required this.memo,
      required this.createdAt,
      required this.availableDelta,
      required this.reservedDelta,
      this.offerTitle});
  final String kind;
  final String memo;
  final DateTime createdAt;
  final int availableDelta;
  final int reservedDelta;
  final String? offerTitle;

  factory HistoryEntry.fromJson(Map<String, dynamic> j) => HistoryEntry(
        kind: j['kind'] as String,
        memo: j['memo'] as String,
        createdAt: DateTime.parse(j['created_at'] as String).toLocal(),
        availableDelta: j['available_delta'] as int,
        reservedDelta: j['reserved_delta'] as int,
        offerTitle: j['offer_title'] as String?,
      );
}

class Plan {
  const Plan(
      {required this.code,
      required this.name,
      required this.priceMinor,
      required this.currency,
      required this.creditsPerPeriod,
      required this.isDemo});
  final String code;
  final String name;
  final int priceMinor;
  final String currency;
  final int creditsPerPeriod;
  final bool isDemo;

  factory Plan.fromJson(Map<String, dynamic> j) => Plan(
        code: j['code'] as String,
        name: j['name'] as String,
        priceMinor: j['price_minor'] as int,
        currency: j['currency'] as String,
        creditsPerPeriod: j['credits_per_period'] as int,
        isDemo: j['is_demo'] as bool? ?? false,
      );
}

class InvoiceLine {
  const InvoiceLine(
      {required this.paidAt,
      required this.planName,
      required this.amountMinor,
      required this.currency,
      required this.livemode});
  final DateTime paidAt;
  final String planName;
  final int amountMinor;
  final String currency;
  final bool livemode;
}

class SubscriptionInfo {
  const SubscriptionInfo(
      {required this.paymentsEnabled,
      required this.sandbox,
      this.status,
      this.plan,
      this.currentPeriodEnd,
      required this.cancelAtPeriodEnd,
      required this.invoices,
      this.pendingPlan,
      this.subscriptionCredits = 0,
      this.rolloverCap});
  final bool paymentsEnabled;
  final bool sandbox;
  final String? status;
  final Plan? plan;
  final DateTime? currentPeriodEnd;
  final bool cancelAtPeriodEnd;
  final List<InvoiceLine> invoices;

  /// Formule choisie pour le prochain renouvellement.
  final Plan? pendingPlan;

  /// Crédits d'abonnement disponibles et plafond reporté au prochain renouvellement.
  final int subscriptionCredits;
  final int? rolloverCap;

  bool get isActive => status == 'active' || status == 'past_due';

  factory SubscriptionInfo.fromJson(Map<String, dynamic> j) => SubscriptionInfo(
        paymentsEnabled: j['payments_enabled'] as bool,
        sandbox: j['sandbox'] as bool,
        status: j['status'] as String?,
        plan: j['plan'] == null ? null : Plan.fromJson(j['plan'] as Map<String, dynamic>),
        currentPeriodEnd:
            j['current_period_end'] == null ? null : DateTime.parse(j['current_period_end'] as String).toLocal(),
        cancelAtPeriodEnd: j['cancel_at_period_end'] as bool? ?? false,
        pendingPlan: j['pending_plan'] == null ? null : Plan.fromJson(j['pending_plan'] as Map<String, dynamic>),
        subscriptionCredits: j['subscription_credits'] as int? ?? 0,
        rolloverCap: j['rollover_cap'] as int?,
        invoices: [
          for (final i in j['invoices'] as List)
            InvoiceLine(
              paidAt: DateTime.parse((i as Map)['paid_at'] as String).toLocal(),
              planName: i['plan_name'] as String,
              amountMinor: i['amount_minor'] as int,
              currency: i['currency'] as String,
              livemode: i['livemode'] as bool,
            ),
        ],
      );
}

class DisputeInfo {
  const DisputeInfo({required this.reference, required this.status, this.creditsRestored, this.resolutionReason});
  final String reference;
  final String status;
  final int? creditsRestored;
  final String? resolutionReason;

  bool get isOpen => status == 'open' || status == 'in_review' || status == 'waiting_customer';

  String get summary => switch (status) {
        'resolved_refund' => 'Réclamation $reference : ${creditsRestored ?? 0} crédits vous ont été restitués.',
        'resolved_rejected' =>
          'Réclamation $reference non retenue${resolutionReason != null ? ' : $resolutionReason' : '.'}',
        _ => 'Réclamation $reference en cours.',
      };

  factory DisputeInfo.fromJson(Map<String, dynamic> j) => DisputeInfo(
        reference: j['reference'] as String,
        status: j['status'] as String,
        creditsRestored: j['credits_restored'] as int?,
        resolutionReason: j['resolution_reason'] as String?,
      );
}
