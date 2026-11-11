import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/format.dart' as fmt;
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../catalog/catalog_repository.dart';
import '../catalog/models.dart';
import 'events_screen.dart';
import '../engagement/engagement.dart';
import '../../core/l10n.dart';

/// Maquette 08 — Fiche partenaire.
class LocationScreen extends ConsumerStatefulWidget {
  const LocationScreen({super.key, required this.slug});
  final String slug;

  @override
  ConsumerState<LocationScreen> createState() => _LocationScreenState();
}

class _LocationScreenState extends ConsumerState<LocationScreen> {
  int _tab = 0;
  String? _selectedOfferId;

  @override
  Widget build(BuildContext context) {
    final detail = ref.watch(locationDetailProvider(widget.slug));
    return Scaffold(
      body: detail.when(
        loading: () => const LoadingView(),
        error: (e, _) => SafeArea(
          child: Column(children: [
            Align(alignment: Alignment.centerLeft, child: BackButton(onPressed: () => _back(context))),
            Expanded(child: ErrorView(error: e, onRetry: () => ref.invalidate(locationDetailProvider(widget.slug)))),
          ]),
        ),
        data: (d) => _buildDetail(context, d),
      ),
    );
  }

  void _back(BuildContext context) => context.canPop() ? context.pop() : context.go('/explore');

  Widget _buildDetail(BuildContext context, LocationDetail d) {
    if (d.offers.isEmpty) {
      return SafeArea(
          child: Column(children: [
        Align(alignment: Alignment.centerLeft, child: BackButton(onPressed: () => _back(context))),
        EmptyView(message: context.l10n.noOffersYet),
      ]));
    }
    final offer = d.offers.firstWhere((o) => o.id == _selectedOfferId, orElse: () => d.offers.first);
    final card = d.card;
    return Stack(children: [
      CustomScrollView(slivers: [
        SliverToBoxAdapter(
          child: SizedBox(
            height: 280,
            child: Stack(fit: StackFit.expand, children: [
              MediaImage(
                  imageKey: card.coverImageKey,
                  fallbackIcon: categoryIcon(card.categorySlug),
                  semanticLabel: card.name),
              const DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.center,
                    colors: [Color(0x99FFFFFF), Colors.transparent],
                  ),
                ),
              ),
              SafeArea(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    IconButton(
                        tooltip: 'Retour', onPressed: () => _back(context), icon: const Icon(Icons.arrow_back_ios_new)),
                    const Spacer(),
                    const Padding(padding: EdgeInsets.only(top: 8), child: XpassLogo(height: 26)),
                    const Spacer(),
                    FavoriteButton(locationId: card.id, name: card.name),
                  ]),
                ),
              ),
            ]),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 120),
          sliver: SliverList.list(children: [
            Text(card.name, style: serif(38)),
            const SizedBox(height: 10),
            Wrap(spacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
              _Meta(icon: subcategoryIconFor(card), text: card.subcategoryName),
              const Text('•'),
              _Meta(icon: Icons.location_on_outlined, text: card.districtLabel),
              if (card.distanceM != null) ...[
                const Text('•'),
                _Meta(icon: Icons.directions_walk, text: fmt.distance(card.distanceM)),
              ],
            ]),
            const SizedBox(height: 18),
            _Tabs(index: _tab, onChanged: (i) => setState(() => _tab = i)),
            const SizedBox(height: 16),
            if (_tab == 0) ...[
              for (final o in d.offers) ...[
                _OfferCard(
                  offer: o,
                  selected: o.id == offer.id,
                  onTap: () => setState(() => _selectedOfferId = o.id),
                ),
                const SizedBox(height: 12),
              ],
              LocationEvents(slug: card.slug),
              _InfoCard(detail: d),
            ] else
              _InfosTab(detail: d),
            LocationReviews(slug: card.slug),
            const SizedBox(height: 12),
            _Banner(
              color: XColors.mint,
              icon: Icons.event_available_outlined,
              title: 'Annulation gratuite jusqu’à ${offer.freeCancellationHours} h avant',
            ),
            const SizedBox(height: 12),
            if (offer.isExternalTicket)
              _Banner(
                color: XColors.lavender,
                icon: Icons.confirmation_number_outlined,
                title: offer.externalTicketNote ?? context.l10n.externalTicket,
                subtitle: context.l10n.externalTicketIssued,
              )
            else if (offer.nextSlot != null)
              _Banner(
                color: XColors.lavender,
                icon: Icons.calendar_month_outlined,
                caption: context.l10n.nextOpeningSlot,
                title: fmt.slotLabel(offer.nextSlot!.localStart),
                trailingText: offer.nextSlot!.resourceName,
                subtitle: context.l10n.accordingToHours,
              )
            else
              _Banner(color: XColors.lavender, icon: Icons.event_busy_outlined, title: context.l10n.noSlot14Days),
          ]),
        ),
      ]),
      Positioned(
        left: 20,
        right: 20,
        bottom: 16,
        child: offer.isExternalTicket
            ? CoralButton(
                label: context.l10n.ticketAtDistributor,
                onPressed: () => showComingSoon(
                  context,
                  title: context.l10n.externalTicket,
                  body: context.l10n.externalTicketNoSlot,
                ),
              )
            : CoralButton(
                label: context.l10n.seeCalendar,
                onPressed: () => context.push('/explore/lieu/${card.slug}/reserver/${offer.id}'),
              ),
      ),
    ]);
  }
}

IconData subcategoryIconFor(LocationCard c) => switch (c.subcategorySlug) {
      'coiffure' => Icons.content_cut,
      'ongles' => Icons.back_hand_outlined,
      'soins' => Icons.spa_outlined,
      'yoga' => Icons.self_improvement,
      'fitness' => Icons.fitness_center,
      'escalade' => Icons.terrain_outlined,
      'cinema' => Icons.movie_outlined,
      'theatre' => Icons.theater_comedy_outlined,
      _ => categoryIcon(c.categorySlug),
    };

class _Meta extends StatelessWidget {
  const _Meta({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 20, color: XColors.navyMuted),
        const SizedBox(width: 4),
        Text(text, style: const TextStyle(fontSize: 16, color: XColors.navy)),
      ]);
}

class _Tabs extends StatelessWidget {
  const _Tabs({required this.index, required this.onChanged});
  final int index;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) => Container(
        decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: XColors.line))),
        child: Row(children: [
          for (final (i, label) in const ['Prestations', 'Infos'].indexed)
            Semantics(
              selected: i == index,
              button: true,
              child: InkWell(
                onTap: () => onChanged(i),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 12),
                  decoration: BoxDecoration(
                    border: Border(bottom: BorderSide(color: i == index ? XColors.navy : Colors.transparent, width: 3)),
                  ),
                  child: Text(label,
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                        color: i == index ? XColors.navy : XColors.navyMuted,
                      )),
                ),
              ),
            ),
        ]),
      );
}

class _OfferCard extends StatelessWidget {
  const _OfferCard({required this.offer, required this.selected, required this.onTap});
  final Offer offer;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final meta = [
      (Icons.schedule, fmt.duration(offer.durationMin)),
      (XIcons.credits, fmt.credits(offer.priceCredits)),
      (Icons.person_outline, offer.participantsMax > 1 ? '1 à ${offer.participantsMax} pers.' : '1 personne'),
    ];
    return Semantics(
      selected: selected,
      button: true,
      child: Material(
        color: selected ? XColors.lavender : Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(XRadius.card),
          side: BorderSide(color: selected ? XColors.lavenderStrong : XColors.line),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(children: [
              if (offer.imageKey != null) ...[
                ClipRRect(
                  borderRadius: BorderRadius.circular(14),
                  child: SizedBox(width: 96, height: 80, child: MediaImage(imageKey: offer.imageKey)),
                ),
                const SizedBox(width: 14),
              ],
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(offer.title, style: serif(22)),
                  const SizedBox(height: 6),
                  Wrap(spacing: 10, runSpacing: 4, children: [
                    for (final (icon, text) in meta)
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        Icon(icon, size: 17, color: XColors.navyMuted),
                        const SizedBox(width: 4),
                        Text(text, style: const TextStyle(color: XColors.navy)),
                      ]),
                  ]),
                  if (offer.includes != null) ...[
                    const SizedBox(height: 6),
                    Text('Inclus : ${offer.includes}', style: const TextStyle(color: XColors.lavenderText)),
                  ],
                ]),
              ),
              const Icon(Icons.chevron_right),
            ]),
          ),
        ),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.detail});
  final LocationDetail detail;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(XRadius.card),
          border: Border.all(color: XColors.line),
        ),
        child: Column(children: [
          _InfoRow(icon: Icons.location_on_outlined, label: 'Adresse', value: detail.fullAddress),
          if (detail.accessInfo != null) ...[
            const Divider(height: 1, indent: 16, endIndent: 16),
            _InfoRow(
              icon: Icons.train_outlined,
              label: 'Accès',
              value: detail.accessInfo!.replaceAll(' · ', '\n'),
            ),
          ],
          const Divider(height: 1, indent: 16, endIndent: 16),
          _InfoRow(icon: Icons.schedule, label: 'Horaires', value: detail.hoursSummary.replaceAll(' · ', '\n')),
        ]),
      );
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.icon, required this.label, required this.value});
  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, size: 24),
          const SizedBox(width: 12),
          SizedBox(width: 90, child: Text(label, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16))),
          Expanded(child: Text(value, style: const TextStyle(fontSize: 15, height: 1.35))),
        ]),
      );
}

class _InfosTab extends StatelessWidget {
  const _InfosTab({required this.detail});
  final LocationDetail detail;

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (detail.description.isNotEmpty) ...[
          Text(detail.description, style: const TextStyle(fontSize: 16, height: 1.45)),
          const SizedBox(height: 16),
        ],
        _InfoCard(detail: detail),
        const SizedBox(height: 16),
        Row(children: [
          Icon(detail.card.wheelchairAccessible ? Icons.accessible : Icons.not_accessible, size: 22),
          const SizedBox(width: 8),
          Text(detail.card.wheelchairAccessible
              ? context.l10n.wheelchairAccessible
              : context.l10n.accessibilityNotGuaranteed),
        ]),
        if (detail.team.where((t) => t.kind == 'staff').isNotEmpty) ...[
          const SizedBox(height: 20),
          Text('L’équipe', style: serif(24)),
          const SizedBox(height: 8),
          for (final t in detail.team.where((t) => t.kind == 'staff'))
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: CircleAvatar(
                backgroundColor: XColors.lavender,
                child: Text(t.name.characters.first, style: const TextStyle(color: XColors.navy)),
              ),
              title: Text(t.name, style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text(t.roleLabel),
            ),
        ],
      ]);
}

class _Banner extends StatelessWidget {
  const _Banner({
    required this.color,
    required this.icon,
    required this.title,
    this.caption,
    this.subtitle,
    this.trailingText,
  });

  final Color color;
  final IconData icon;
  final String title;
  final String? caption;
  final String? subtitle;
  final String? trailingText;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(XRadius.card)),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, size: 26),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              if (caption != null) Text(caption!, style: const TextStyle(color: XColors.navyMuted)),
              Text.rich(TextSpan(children: [
                TextSpan(text: title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 17)),
                if (trailingText != null)
                  TextSpan(text: ' · $trailingText', style: const TextStyle(fontSize: 17, color: XColors.navyMuted)),
              ])),
              if (subtitle != null) ...[
                const SizedBox(height: 4),
                Text(subtitle!, style: const TextStyle(fontSize: 13, color: XColors.navyMuted)),
              ],
            ]),
          ),
        ]),
      );
}
