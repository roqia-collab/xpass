import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/format.dart' as fmt;
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../account/login_sheet.dart';
import '../catalog/catalog_repository.dart';
import 'booking_repository.dart';
import 'models.dart';
import '../../core/l10n.dart';

/// Maquette 09 — choix de la date, du professionnel et de l'heure (disponibilités réelles).
class CalendarScreen extends ConsumerStatefulWidget {
  const CalendarScreen({super.key, required this.locationSlug, required this.offerId});
  final String locationSlug;
  final String offerId;

  @override
  ConsumerState<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends ConsumerState<CalendarScreen> {
  String? _date;
  String? _resourceId; // null = sans préférence
  Slot? _slot;
  int _party = 1;
  bool _submitting = false;
  String? _pendingKey; // conservée en cas de réessai (timeout après commit)

  static const _dayNames = ['LUN', 'MAR', 'MER', 'JEU', 'VEN', 'SAM', 'DIM'];

  @override
  Widget build(BuildContext context) {
    final location = ref.watch(locationDetailProvider(widget.locationSlug));
    final avail = ref.watch(availabilityProvider((widget.offerId, _date)));
    final offer = location.valueOrNull?.offers.where((o) => o.id == widget.offerId).firstOrNull;

    return Scaffold(
      body: avail.when(
        loading: () => const LoadingView(),
        error: (e, _) => SafeArea(
          child: ErrorView(error: e, onRetry: () => ref.invalidate(availabilityProvider((widget.offerId, _date)))),
        ),
        data: (a) {
          // Aujourd'hui sans horaire restant : on passe au prochain jour ouvert.
          if (_date == null && a.slots.isEmpty) {
            final next = a.days.where((d) => d.$2 && d.$1 != a.date).firstOrNull;
            if (next != null) WidgetsBinding.instance.addPostFrameCallback((_) => setState(() => _date = next.$1));
          }
          final slots = _visibleSlots(a);
          // Prix du créneau choisi (heure de pointe, forte demande, dernière minute) ; sinon prix de base.
          final price = (_slot?.priceCredits ?? a.priceCredits) * _party;
          return Stack(children: [
            CustomScrollView(slivers: [
              SliverToBoxAdapter(
                child: SafeArea(
                  bottom: false,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      const XpassLogo(height: 28),
                      const SizedBox(height: 12),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(XRadius.card),
                        child: SizedBox(
                          height: 180,
                          child: MediaImage(imageKey: offer?.imageKey ?? location.valueOrNull?.card.coverImageKey),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextButton.icon(
                        onPressed: () => context.pop(),
                        icon: const Icon(Icons.arrow_back, color: XColors.navy),
                        label: const Text('Calendrier', style: TextStyle(color: XColors.navy)),
                      ),
                      Text(context.l10n.chooseMySlot, style: serif(36)),
                      const SizedBox(height: 14),
                      SizedBox(width: double.infinity, child: _OfferSummary(a: a)),
                      const SizedBox(height: 18),
                    ]),
                  ),
                ),
              ),
              SliverToBoxAdapter(child: _dayStrip(a)),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(20, 18, 20, 120),
                sliver: SliverList.list(children: [
                  if (a.bookingMode == 'resource_slot' && a.resources.length > 1) ...[
                    const Text('Professionnel', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                    const SizedBox(height: 8),
                    _ResourcePicker(
                      resources: a.resources,
                      value: _resourceId,
                      onChanged: (v) => setState(() {
                        _resourceId = v;
                        _slot = null;
                      }),
                    ),
                    const SizedBox(height: 18),
                  ],
                  if (a.participantsMax > 1) ...[
                    _PartyStepper(
                      value: _party,
                      min: a.participantsMin,
                      max: a.participantsMax,
                      onChanged: (v) => setState(() {
                        _party = v;
                        _slot = null;
                      }),
                    ),
                    const SizedBox(height: 18),
                  ],
                  Text(context.l10n.availableTimes, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                  const SizedBox(height: 10),
                  if (slots.isEmpty)
                    EmptyView(message: context.l10n.noTimeThatDay)
                  else
                    GridView.count(
                      crossAxisCount: 3,
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      mainAxisSpacing: 10,
                      crossAxisSpacing: 10,
                      childAspectRatio: 1.7,
                      children: [for (final s in slots) _slotTile(s)],
                    ),
                  if (slots.any((s) => s.priceAdjustments.isNotEmpty)) ...[
                    const SizedBox(height: 10),
                    Text(context.l10n.slotPriceLegend, style: const TextStyle(color: XColors.navyMuted, fontSize: 13)),
                  ],
                  const SizedBox(height: 16),
                  Row(children: [
                    const Icon(Icons.person_outline, color: XColors.navyMuted),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        [
                          if (_resourceName(a) != null) 'Avec ${_resourceName(a)}',
                          '$_party personne${_party > 1 ? 's' : ''}',
                        ].join(' · '),
                      ),
                    ),
                  ]),
                  const SizedBox(height: 8),
                  Row(children: [
                    const Icon(Icons.location_on_outlined, color: XColors.navyMuted),
                    const SizedBox(width: 8),
                    Expanded(child: Text('Heures locales du lieu · ${a.cityName}')),
                  ]),
                ]),
              ),
            ]),
            Positioned(
              left: 20,
              right: 20,
              bottom: 16,
              child: CoralButton(
                label: _submitting ? context.l10n.holdingSlot : 'Continuer · ${fmt.credits(price)}',
                onPressed: _slot == null || _submitting ? null : () => _continue(a),
              ),
            ),
          ]);
        },
      ),
    );
  }

  List<Slot> _visibleSlots(Availability a) {
    if (a.bookingMode != 'resource_slot' || _resourceId == null) {
      return a.slots
          .map((s) => a.bookingMode == 'resource_slot' || (s.remaining ?? 0) >= _party ? s : _unavailable(s))
          .toList();
    }
    return a.slots.map((s) => s.freeResourceIds.contains(_resourceId) ? s : _unavailable(s)).toList();
  }

  Slot _unavailable(Slot s) => Slot(
      startsAt: s.startsAt,
      localTime: s.localTime,
      available: false,
      remaining: s.remaining,
      freeResourceIds: const [],
      priceCredits: s.priceCredits,
      priceAdjustments: s.priceAdjustments);

  String? _resourceName(Availability a) {
    if (a.bookingMode != 'resource_slot') return null;
    final id =
        _resourceId ?? (_slot != null && _slot!.freeResourceIds.isNotEmpty ? _slot!.freeResourceIds.first : null);
    return a.resources.where((r) => r.id == id).firstOrNull?.name;
  }

  Widget _dayStrip(Availability a) => SizedBox(
        height: 84,
        child: ListView.separated(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          scrollDirection: Axis.horizontal,
          itemCount: a.days.length,
          separatorBuilder: (_, __) => const SizedBox(width: 8),
          itemBuilder: (_, i) {
            final (date, open) = a.days[i];
            final d = DateTime.parse(date);
            final selected = date == a.date;
            return Semantics(
              selected: selected,
              button: true,
              label: '${_dayNames[d.weekday - 1]} ${d.day}${open ? '' : ', fermé'}',
              child: InkWell(
                borderRadius: BorderRadius.circular(14),
                onTap: open
                    ? () => setState(() {
                          _date = date;
                          _slot = null;
                        })
                    : null,
                child: Container(
                  width: 58,
                  decoration: BoxDecoration(
                    color: selected ? XColors.navy : Colors.transparent,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    Text(_dayNames[d.weekday - 1],
                        style: TextStyle(fontSize: 12, color: selected ? Colors.white : XColors.navyMuted)),
                    const SizedBox(height: 4),
                    Text('${d.day}',
                        style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.w600,
                          color: selected ? Colors.white : (open ? XColors.navy : XColors.line),
                        )),
                  ]),
                ),
              ),
            );
          },
        ),
      );

  Widget _slotTile(Slot s) {
    final selected = _slot?.startsAt == s.startsAt;
    return Semantics(
      button: true,
      selected: selected,
      enabled: s.available,
      label: [
        s.localTime,
        if (s.available) fmt.credits(s.priceCredits) else 'complet',
        if (s.available && s.isLastMinute) context.l10n.slotPriceLastMinute,
        if (s.available && s.isPeak) context.l10n.slotPricePeak,
        if (s.available && s.isHighDemand) context.l10n.slotPriceDemand,
      ].join(', '),
      child: Material(
        color: selected ? XColors.coral : (s.available ? Colors.white : XColors.creamDark),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: selected ? XColors.coral : XColors.line),
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: s.available ? () => setState(() => _slot = s) : null,
          child: Center(
            child: s.available
                ? Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Row(mainAxisSize: MainAxisSize.min, children: [
                          if (selected) const Icon(Icons.check, color: Colors.white, size: 18),
                          if (selected) const SizedBox(width: 4),
                          Text(s.localTime,
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w600,
                                color: selected ? Colors.white : XColors.navy,
                              )),
                        ])),
                    const SizedBox(height: 2),
                    _SlotPrice(slot: s, selected: selected),
                  ])
                : Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    Text(s.localTime,
                        style: const TextStyle(
                            color: XColors.navyMuted, decoration: TextDecoration.lineThrough, fontSize: 16)),
                    const Text('Complet', style: TextStyle(color: XColors.navyMuted, fontSize: 12)),
                  ]),
          ),
        ),
      ),
    );
  }

  Future<void> _continue(Availability a) async {
    if (!await ensureSignedIn(context, ref)) return;
    setState(() => _submitting = true);
    _pendingKey ??= newIdempotencyKey();
    try {
      final booking = await ref.read(bookingRepositoryProvider).hold(
            offerId: a.offerId,
            startsAt: _slot!.startsAt,
            partySize: _party,
            resourceId: _resourceId,
            expectedPriceCredits: _slot!.priceCredits > 0 ? _slot!.priceCredits : null,
            idempotencyKey: _pendingKey!,
          );
      _pendingKey = null;
      invalidateBookingData(ref);
      if (mounted) context.push('/explore/reservation/${booking.id}');
    } on ApiException catch (e) {
      // Erreur métier : la clé est abandonnée. Erreur réseau : elle est gardée pour un réessai sûr.
      if (!e.isNetwork) _pendingKey = null;
      if (e.code == 'slot_unavailable' || e.code == 'slot_full' || e.code == 'price_changed') {
        ref.invalidate(availabilityProvider((widget.offerId, _date)));
        _slot = null;
      }
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }
}

/// Prix du créneau : flèche montante (heure de pointe, forte demande) ou descendante (dernière minute).
class _SlotPrice extends StatelessWidget {
  const _SlotPrice({required this.slot, required this.selected});
  final Slot slot;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final up = slot.isPeak || slot.isHighDemand;
    final color =
        selected ? Colors.white : (slot.isLastMinute ? XColors.mintText : (up ? XColors.coral : XColors.navyMuted));
    // Réduit si la tuile est étroite (petit écran, grands textes) plutôt que de déborder.
    return FittedBox(
      fit: BoxFit.scaleDown,
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        if (slot.isLastMinute) Icon(Icons.south, size: 12, color: color),
        if (up) Icon(Icons.north, size: 12, color: color),
        Text(fmt.credits(slot.priceCredits), style: TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.w600)),
      ]),
    );
  }
}

class _OfferSummary extends StatelessWidget {
  const _OfferSummary({required this.a});
  final Availability a;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(XRadius.card),
          border: Border.all(color: XColors.line),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(a.locationName, style: serif(26)),
          const SizedBox(height: 4),
          Text('${a.offerTitle} · ${fmt.duration(a.durationMin)} · ${fmt.credits(a.priceCredits)}',
              style: const TextStyle(color: XColors.navyMuted, fontSize: 16)),
        ]),
      );
}

class _ResourcePicker extends StatelessWidget {
  const _ResourcePicker({required this.resources, required this.value, required this.onChanged});
  final List<BookableResource> resources;
  final String? value;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context) => DropdownButtonFormField<String?>(
        value: value,
        decoration: InputDecoration(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
        ),
        items: [
          DropdownMenuItem(value: null, child: Text(context.l10n.noPreference)),
          for (final r in resources) DropdownMenuItem(value: r.id, child: Text('${r.name} · ${r.roleLabel}')),
        ],
        onChanged: onChanged,
      );
}

class _PartyStepper extends StatelessWidget {
  const _PartyStepper({required this.value, required this.min, required this.max, required this.onChanged});
  final int value;
  final int min;
  final int max;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) => Row(children: [
        const Expanded(child: Text('Participants', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16))),
        IconButton.outlined(
          tooltip: context.l10n.removeParticipant,
          onPressed: value > min ? () => onChanged(value - 1) : null,
          icon: const Icon(Icons.remove),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          child: Text('$value', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w600)),
        ),
        IconButton.outlined(
          tooltip: context.l10n.addParticipant,
          onPressed: value < max ? () => onChanged(value + 1) : null,
          icon: const Icon(Icons.add),
        ),
      ]);
}
