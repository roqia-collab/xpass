import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/config.dart';
import '../../core/format.dart' as fmt;
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../catalog/catalog_repository.dart';
import '../catalog/models.dart';
import '../../core/l10n.dart';

/// Recherche affichée sur la carte : centre, rayon et filtres.
class AreaQuery {
  const AreaQuery(
      {required this.center, required this.radiusKm, this.category, this.maxCredits, this.day, this.participants});
  final LatLng center;
  final int radiusKm;
  final String? category;
  final int? maxCredits;

  /// Jour souhaité : établissements ouverts ce jour-là (horaires et fermetures exceptionnelles).
  final DateTime? day;

  /// Nombre de participants accepté par au moins une prestation.
  final int? participants;

  AreaQuery copyWith(
          {LatLng? center,
          int? radiusKm,
          String? category,
          int? maxCredits,
          DateTime? day,
          int? participants,
          bool clearCategory = false,
          bool clearBudget = false,
          bool clearDay = false,
          bool clearParticipants = false}) =>
      AreaQuery(
        center: center ?? this.center,
        radiusKm: radiusKm ?? this.radiusKm,
        category: clearCategory ? null : category ?? this.category,
        maxCredits: clearBudget ? null : maxCredits ?? this.maxCredits,
        day: clearDay ? null : day ?? this.day,
        participants: clearParticipants ? null : participants ?? this.participants,
      );

  @override
  bool operator ==(Object other) =>
      other is AreaQuery &&
      other.center == center &&
      other.radiusKm == radiusKm &&
      other.category == category &&
      other.maxCredits == maxCredits &&
      other.day == day &&
      other.participants == participants;

  @override
  int get hashCode => Object.hash(center, radiusKm, category, maxCredits, day, participants);
}

final areaResultsProvider = FutureProvider.autoDispose.family<LocationPage, AreaQuery>((ref, q) => ref
    .watch(catalogRepositoryProvider)
    .searchArea(
        lat: q.center.latitude,
        lng: q.center.longitude,
        radiusM: q.radiusKm * 1000,
        category: q.category,
        maxCredits: q.maxCredits,
        day: q.day,
        participants: q.participants));

/// Maquette 07 — « Autour de moi » : carte OpenStreetMap, rayon, filtres, fiche résumée.
/// La position n'est demandée qu'au clic sur « Me localiser » ; sans elle, la carte part du centre de la ville.
class NearbyScreen extends ConsumerStatefulWidget {
  const NearbyScreen({super.key, this.initialCategory});
  final String? initialCategory;

  @override
  ConsumerState<NearbyScreen> createState() => _NearbyScreenState();
}

class _NearbyScreenState extends ConsumerState<NearbyScreen> {
  static const _radii = [1, 5, 10, 25];
  static const _paris = LatLng(48.8566, 2.3522);
  final _map = MapController();
  late AreaQuery _query;
  LatLng? _me;
  LatLng? _pendingCenter; // carte déplacée : proposer « Rechercher dans cette zone »
  String? _selected;
  bool _locating = false;

  @override
  void initState() {
    super.initState();
    final city = ref.read(selectedCityProvider);
    final start = city.latitude != null ? LatLng(city.latitude!, city.longitude!) : _paris;
    _query = AreaQuery(center: start, radiusKm: 5, category: widget.initialCategory);
  }

  double _zoomFor(int km) => switch (km) { 1 => 14.5, 5 => 12.5, 10 => 11.5, _ => 10.2 };

  Future<void> _locate() async {
    final l = context.l10n;
    setState(() => _locating = true);
    try {
      if (!await Geolocator.isLocationServiceEnabled()) throw Exception(l.locationDisabled);
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
        throw Exception(l.locationDenied);
      }
      final p = await Geolocator.getCurrentPosition(
          locationSettings:
              const LocationSettings(accuracy: LocationAccuracy.medium, timeLimit: Duration(seconds: 10)));
      final here = LatLng(p.latitude, p.longitude);
      setState(() {
        _me = here;
        _query = _query.copyWith(center: here);
        _pendingCenter = null;
      });
      _map.move(here, _zoomFor(_query.radiusKm));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))));
      }
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  void _recenter() {
    setState(() => _pendingCenter = null);
    _map.move(_query.center, _zoomFor(_query.radiusKm));
  }

  @override
  Widget build(BuildContext context) {
    final results = ref.watch(areaResultsProvider(_query));
    final items = (results.valueOrNull?.items ?? const <LocationCard>[])
        .where((l) => l.latitude != null && l.longitude != null)
        .toList();
    final selected = items.where((l) => l.slug == _selected).firstOrNull;
    final categories = ref.watch(categoriesProvider).valueOrNull ?? const [];
    final l = context.l10n;
    final city = ref.watch(selectedCityProvider);
    final categoryName = categories.where((c) => c.slug == _query.category).firstOrNull?.name ?? l.allCategories;
    final showSearchArea = _pendingCenter != null && _pendingCenter != _query.center;

    return Scaffold(
      body: Column(children: [
        // En-tête crème arrondi, posé sur la carte (maquette 07).
        Material(
          color: XColors.cream,
          elevation: 2,
          shadowColor: const Color(0x22000000),
          borderRadius: const BorderRadius.vertical(bottom: Radius.circular(24)),
          child: SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsetsDirectional.fromSTEB(16, 4, 16, 14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  IconButton(
                    tooltip: l.back,
                    onPressed: () => context.canPop() ? context.pop() : context.go('/explore'),
                    icon: const BackButtonIcon(),
                  ),
                  const XpassLogo(height: 26),
                  const Spacer(),
                  IconButton.filledTonal(
                    tooltip: MaterialLocalizations.of(context).searchFieldLabel,
                    style: IconButton.styleFrom(backgroundColor: XColors.creamDark),
                    onPressed: () => context.push('/explore/recherche'),
                    icon: const Icon(XIcons.search, color: XColors.navy),
                  ),
                ]),
                Padding(
                  padding: const EdgeInsetsDirectional.only(start: 4),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(l.nearbyTitle, style: serif(38)),
                    const SizedBox(height: 2),
                    Text(l.nearbySubtitle, style: const TextStyle(fontSize: 16, color: XColors.navyMuted)),
                  ]),
                ),
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(
                    child: _AddressField(
                      label: _me != null ? l.myPosition : '${city.name}, France',
                      onClear: _me == null
                          ? null
                          : () {
                              final start = city.latitude != null ? LatLng(city.latitude!, city.longitude!) : _paris;
                              setState(() {
                                _me = null;
                                _query = _query.copyWith(center: start);
                                _selected = null;
                              });
                              _map.move(start, _zoomFor(_query.radiusKm));
                            },
                    ),
                  ),
                  const SizedBox(width: 8),
                  _OutlineAction(
                    icon: XIcons.locate,
                    label: _locating ? l.locating : l.locateMe,
                    onTap: _locating ? null : _locate,
                  ),
                ]),
                const SizedBox(height: 10),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(children: [
                    _FilterBox(
                      icon: XIcons.calendar,
                      label: l.filterDate,
                      value: _query.day == null ? l.anyDate : fmt.dayMonth(_query.day!),
                      onTap: _pickDay,
                    ),
                    const SizedBox(width: 8),
                    _FilterBox(
                      icon: XIcons.grid,
                      label: l.category,
                      value: categoryName,
                      onTap: () => _pick<String?>(
                        title: l.category,
                        current: _query.category,
                        options: {null: l.allCategories, for (final c in categories) c.slug: c.name},
                        onPicked: (v) => setState(() {
                          _query = _query.copyWith(category: v, clearCategory: v == null);
                          _selected = null;
                        }),
                      ),
                    ),
                    const SizedBox(width: 8),
                    _FilterBox(
                      icon: XIcons.credits,
                      label: l.budget,
                      value: _query.maxCredits == null ? l.anyBudget : l.upToCredits(_query.maxCredits!),
                      onTap: () => _pick<int?>(
                        title: l.budget,
                        current: _query.maxCredits,
                        options: {
                          null: l.anyBudget,
                          for (final b in const [10, 15, 20, 30]) b: l.upToCredits(b)
                        },
                        onPicked: (v) => setState(() {
                          _query = _query.copyWith(maxCredits: v, clearBudget: v == null);
                          _selected = null;
                        }),
                      ),
                    ),
                    const SizedBox(width: 8),
                    _FilterBox(
                      icon: XIcons.people,
                      label: l.filterParticipants,
                      value:
                          _query.participants == null ? l.anyParticipants : l.participantsCount(_query.participants!),
                      onTap: () => _pick<int?>(
                        title: l.filterParticipants,
                        current: _query.participants,
                        options: {
                          null: l.anyParticipants,
                          for (final n in const [1, 2, 3, 4, 6, 8]) n: l.participantsCount(n)
                        },
                        onPicked: (v) => setState(() {
                          _query = _query.copyWith(participants: v, clearParticipants: v == null);
                          _selected = null;
                        }),
                      ),
                    ),
                  ]),
                ),
                const SizedBox(height: 10),
                _RadiusTrack(
                  radii: _radii,
                  selected: _query.radiusKm,
                  semantics: l.radiusKm,
                  onChanged: (r) {
                    setState(() => _query = _query.copyWith(radiusKm: r));
                    _map.move(_query.center, _zoomFor(r));
                  },
                ),
              ]),
            ),
          ),
        ),
        Expanded(
          child: Stack(children: [
            FlutterMap(
              mapController: _map,
              options: MapOptions(
                initialCenter: _query.center,
                initialZoom: _zoomFor(_query.radiusKm),
                onTap: (_, __) => setState(() => _selected = null),
                onPositionChanged: (camera, hasGesture) {
                  if (hasGesture) setState(() => _pendingCenter = camera.center);
                },
              ),
              children: [
                TileLayer(
                  urlTemplate: AppConfig.mapTileUrl,
                  userAgentPackageName: 'fr.xpass.app',
                  // Fond adouci (moins saturé, plus clair) pour faire ressortir les prix, comme la maquette.
                  tileBuilder: (context, tile, _) => ColorFiltered(colorFilter: _softMap, child: tile),
                ),
                CircleLayer(circles: [
                  CircleMarker(
                    point: _query.center,
                    radius: _query.radiusKm * 1000.0,
                    useRadiusInMeter: true,
                    color: XColors.lavenderStrong.withValues(alpha: 0.28),
                    borderColor: XColors.lavenderStrong,
                    borderStrokeWidth: 1,
                  ),
                ]),
                MarkerLayer(markers: [
                  if (_me != null)
                    Marker(
                      point: _me!,
                      width: 22,
                      height: 22,
                      child: Semantics(
                        label: l.myPosition,
                        child: Container(
                          decoration: BoxDecoration(
                            color: const Color(0xFF3B6FE0),
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 3),
                            boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 4)],
                          ),
                        ),
                      ),
                    ),
                  for (final c in [
                    ...items.where((c) => c.slug != _selected),
                    ...items.where((c) => c.slug == _selected)
                  ])
                    Marker(
                      point: LatLng(c.latitude!, c.longitude!),
                      width: c.slug == _selected ? 80 : 64,
                      height: c.slug == _selected ? 96 : 76,
                      alignment: Alignment.topCenter,
                      child: _PricePin(
                        card: c,
                        selected: c.slug == _selected,
                        unit: l.creditsUnit,
                        onTap: () => setState(() => _selected = c.slug),
                      ),
                    ),
                ]),
                const RichAttributionWidget(
                  alignment: AttributionAlignment.bottomLeft,
                  attributions: [TextSourceAttribution('© contributeurs OpenStreetMap')],
                ),
              ],
            ),
            if (results.isLoading) const Positioned(top: 16, right: 16, child: CircularProgressIndicator()),
            if (results.hasError)
              Positioned(
                top: 12,
                left: 12,
                right: 12,
                child: _Notice(
                  text: l.loadPlacesError,
                  action:
                      TextButton(onPressed: () => ref.invalidate(areaResultsProvider(_query)), child: Text(l.retry)),
                ),
              ),
            if (!results.isLoading && !results.hasError && items.isEmpty)
              Positioned(top: 12, left: 12, right: 12, child: _Notice(text: l.noResultsArea)),
            Positioned(
              left: 12,
              right: 12,
              bottom: 12,
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Stack(alignment: Alignment.center, children: [
                  if (showSearchArea)
                    FilledButton.icon(
                      style: FilledButton.styleFrom(
                        minimumSize: const Size(0, 48),
                        padding: const EdgeInsets.symmetric(horizontal: 22),
                      ),
                      onPressed: () => setState(() {
                        _query = _query.copyWith(center: _pendingCenter);
                        _pendingCenter = null;
                        _selected = null;
                      }),
                      icon: const Icon(XIcons.map, size: 20),
                      label: Text(l.searchThisArea),
                    ),
                  Align(
                    alignment: AlignmentDirectional.centerEnd,
                    child: Material(
                      color: Colors.white,
                      shape: const CircleBorder(),
                      elevation: 3,
                      child: IconButton(
                        tooltip: l.recenter,
                        onPressed: _recenter,
                        icon: const Icon(XIcons.directions, color: XColors.navy),
                      ),
                    ),
                  ),
                ]),
                const SizedBox(height: 10),
                if (selected != null)
                  _SelectedCard(card: selected)
                else if (items.isNotEmpty)
                  _Notice(text: l.placesInRadius(items.length, _query.radiusKm), center: true),
              ]),
            ),
          ]),
        ),
      ]),
    );
  }

  Future<void> _pickDay() async {
    final l = context.l10n;
    final today = DateTime.now();
    final start = DateTime(today.year, today.month, today.day);
    final picked = await showDatePicker(
      context: context,
      initialDate: _query.day ?? start,
      firstDate: start,
      lastDate: start.add(const Duration(days: 90)),
      helpText: l.openThatDay,
      cancelText: l.anyDate,
    );
    setState(() {
      _query = picked == null ? _query.copyWith(clearDay: true) : _query.copyWith(day: picked);
      _selected = null;
    });
  }

  Future<void> _pick<T>({
    required String title,
    required T current,
    required Map<T, String> options,
    required ValueChanged<T> onPicked,
  }) async {
    final picked = await showModalBottomSheet<(T,)>(
      context: context,
      backgroundColor: XColors.cream,
      builder: (c) => SafeArea(
        child: ListView(shrinkWrap: true, children: [
          Padding(padding: const EdgeInsets.fromLTRB(20, 20, 20, 8), child: Text(title, style: serif(26))),
          for (final e in options.entries)
            ListTile(
              title: Text(e.value),
              trailing: e.key == current ? const Icon(Icons.check, color: XColors.coral) : null,
              onTap: () => Navigator.pop(c, (e.key,)),
            ),
        ]),
      ),
    );
    if (picked != null) onPicked(picked.$1);
  }
}

/// Désature et éclaircit les tuiles (matrice de couleur 4×5).
const _softMap = ColorFilter.matrix(<double>[
  0.55, 0.30, 0.05, 0, 62, //
  0.20, 0.65, 0.05, 0, 60, //
  0.15, 0.25, 0.40, 0, 52, //
  0, 0, 0, 1, 0, //
]);

class _PricePin extends StatelessWidget {
  const _PricePin({required this.card, required this.selected, required this.unit, required this.onTap});
  final LocationCard card;
  final bool selected;
  final String unit;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final price = card.featuredOffer?.priceCredits;
    final size = selected ? 68.0 : 54.0;
    final bg = selected ? XColors.coral : XColors.lavender;
    final fg = selected ? Colors.white : XColors.navy;
    return Semantics(
      button: true,
      selected: selected,
      label: '${card.name}${price != null ? ', ${context.l10n.creditsCount(price)}' : ''}',
      excludeSemantics: true,
      child: GestureDetector(
        onTap: onTap,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              color: bg,
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white, width: 3),
              boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 8, offset: Offset(0, 3))],
            ),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Text(price != null ? '$price' : '—',
                  style: TextStyle(fontWeight: FontWeight.w800, fontSize: selected ? 22 : 18, color: fg, height: 1)),
              Text(unit, style: TextStyle(fontSize: selected ? 12 : 10, color: fg, height: 1.2)),
            ]),
          ),
          // Pointe sous la bulle.
          Transform.translate(
            offset: const Offset(0, -7),
            child: Transform.rotate(
              angle: 0.785398,
              child: Container(width: 12, height: 12, color: selected ? XColors.coral : Colors.white),
            ),
          ),
          if (selected)
            Container(
              width: 12,
              height: 12,
              decoration: BoxDecoration(
                color: XColors.coralBrand,
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white, width: 2),
              ),
            ),
        ]),
      ),
    );
  }
}

class _SelectedCard extends StatelessWidget {
  const _SelectedCard({required this.card});
  final LocationCard card;

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    final offer = card.featuredOffer;
    final slot = offer?.nextSlot;
    return Material(
      color: Colors.white,
      elevation: 6,
      shadowColor: const Color(0x33000000),
      borderRadius: BorderRadius.circular(24),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: SizedBox(
              width: 112,
              height: 168,
              child: MediaImage(imageKey: card.coverImageKey, fallbackIcon: categoryIcon(card.categorySlug)),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text(card.name, style: serif(23), maxLines: 2, overflow: TextOverflow.ellipsis),
              const SizedBox(height: 2),
              Text('${card.kindLabel} · ${card.districtLabel}',
                  style: const TextStyle(color: XColors.navyMuted, fontSize: 13),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis),
              const SizedBox(height: 6),
              if (card.distanceM != null) _Line(XIcons.pin, l.distanceAway(fmt.distance(card.distanceM))),
              if (offer != null) _Line(XIcons.credits, l.creditsCount(offer.priceCredits), bold: true),
              if (slot != null)
                _Line(XIcons.clock, l.nextSlotAt(fmt.slotLabel(slot.localStart)), muted: true, lines: 2),
              const SizedBox(height: 8),
              Row(children: [
                Expanded(
                  child: _CardButton(
                    label: l.directions,
                    icon: XIcons.directions,
                    tonal: true,
                    onTap: card.latitude == null
                        ? null
                        : () => launchUrl(
                            Uri.https('www.google.com', '/maps/dir/', {
                              'api': '1',
                              'destination': '${card.latitude},${card.longitude}',
                            }),
                            mode: LaunchMode.externalApplication),
                  ),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: _CardButton(
                    label: l.seeDetails,
                    trailing: true,
                    onTap: () => context.push('/explore/lieu/${card.slug}'),
                  ),
                ),
              ]),
            ]),
          ),
        ]),
      ),
    );
  }
}

class _Line extends StatelessWidget {
  const _Line(this.icon, this.text, {this.bold = false, this.muted = false, this.lines = 1});
  final int lines;
  final IconData icon;
  final String text;
  final bool bold;
  final bool muted;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, size: 16, color: XColors.navy),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              text,
              maxLines: lines,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 14,
                fontWeight: bold ? FontWeight.w700 : FontWeight.w400,
                color: muted ? XColors.navyMuted : XColors.navy,
              ),
            ),
          ),
        ]),
      );
}

class _CardButton extends StatelessWidget {
  const _CardButton({required this.label, this.icon, this.tonal = false, this.trailing = false, this.onTap});
  final String label;
  final IconData? icon;
  final bool tonal;
  final bool trailing;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final fg = tonal ? XColors.navy : Colors.white;
    return Material(
      color: tonal ? XColors.lavender : XColors.coral,
      shape: const StadiumBorder(),
      child: InkWell(
        customBorder: const StadiumBorder(),
        onTap: onTap,
        child: SizedBox(
          height: 42,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Center(
              child: FittedBox(
                fit: BoxFit.scaleDown,
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  if (icon != null) ...[Icon(icon, size: 16, color: fg), const SizedBox(width: 6)],
                  Text(label, style: TextStyle(color: fg, fontWeight: FontWeight.w600, fontSize: 14)),
                  if (trailing) ...[const SizedBox(width: 2), Icon(Icons.chevron_right, size: 18, color: fg)],
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.text, this.action, this.center = false});
  final String text;
  final Widget? action;
  final bool center;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.white,
        elevation: 3,
        shadowColor: const Color(0x22000000),
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          child: Row(children: [
            Expanded(child: Text(text, textAlign: center ? TextAlign.center : TextAlign.start)),
            if (action != null) action!,
          ]),
        ),
      );
}

class _AddressField extends StatelessWidget {
  const _AddressField({required this.label, this.onClear});
  final String label;
  final VoidCallback? onClear;

  @override
  Widget build(BuildContext context) => Container(
        height: 52,
        padding: const EdgeInsetsDirectional.only(start: 14, end: 4),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: XColors.line),
        ),
        child: Row(children: [
          const Icon(XIcons.pin, size: 20),
          const SizedBox(width: 10),
          Expanded(child: Text(label, style: const TextStyle(fontSize: 16), overflow: TextOverflow.ellipsis)),
          if (onClear != null)
            IconButton(
              tooltip: MaterialLocalizations.of(context).deleteButtonTooltip,
              onPressed: onClear,
              icon: const Icon(Icons.close, size: 20),
            ),
        ]),
      );
}

class _OutlineAction extends StatelessWidget {
  const _OutlineAction({required this.icon, required this.label, this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: XColors.line),
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: SizedBox(
            height: 52,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(icon, size: 20),
                const SizedBox(width: 6),
                Text(label, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w500)),
              ]),
            ),
          ),
        ),
      );
}

/// Filtre sur deux lignes : libellé en gras, valeur en dessous (maquette 07).
class _FilterBox extends StatelessWidget {
  const _FilterBox({required this.icon, required this.label, required this.value, required this.onTap});
  final IconData icon;
  final String label;
  final String value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: XColors.line),
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsetsDirectional.fromSTEB(10, 8, 6, 8),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(icon, size: 22),
              const SizedBox(width: 8),
              Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                Text(value, style: const TextStyle(fontSize: 13, color: XColors.navyMuted)),
              ]),
              const SizedBox(width: 2),
              const Icon(Icons.keyboard_arrow_down, size: 18),
            ]),
          ),
        ),
      );
}

/// Choix du rayon : piste grise, segment actif corail (maquette 07).
class _RadiusTrack extends StatelessWidget {
  const _RadiusTrack({required this.radii, required this.selected, required this.semantics, required this.onChanged});
  final List<int> radii;
  final int selected;
  final String Function(int) semantics;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) => Container(
        height: 46,
        padding: const EdgeInsets.all(3),
        decoration: BoxDecoration(color: XColors.creamDark, borderRadius: BorderRadius.circular(24)),
        child: Row(children: [
          for (final r in radii)
            Expanded(
              child: Semantics(
                button: true,
                selected: r == selected,
                label: semantics(r),
                excludeSemantics: true,
                child: GestureDetector(
                  onTap: () => onChanged(r),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: r == selected ? XColors.coral : Colors.transparent,
                      borderRadius: BorderRadius.circular(21),
                    ),
                    child: Text(
                      '$r km',
                      maxLines: 1,
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: r == selected ? FontWeight.w600 : FontWeight.w400,
                        color: r == selected ? Colors.white : XColors.navy,
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ]),
      );
}
