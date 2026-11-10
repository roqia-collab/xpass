import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/format.dart' as fmt;
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../catalog/models.dart';

void openLocation(BuildContext context, LocationCard l) => context.push('/explore/lieu/${l.slug}');

/// Un geste : le créneau, sans repasser par la fiche. Billet externe : la fiche explique la suite.
void bookFeatured(BuildContext context, LocationCard l) {
  final offer = l.featuredOffer;
  if (offer != null && !offer.isExternalTicket) {
    context.push('/explore/lieu/${l.slug}/reserver/${offer.id}');
    return;
  }
  openLocation(context, l);
}

/// Carte horizontale (accueil « À réserver près de vous », Divertissement, Culture).
class HorizontalLocationCard extends StatelessWidget {
  const HorizontalLocationCard({super.key, required this.location, this.showBookButton = false});
  static const _photoWidth = 150.0;
  final LocationCard location;
  final bool showBookButton;

  @override
  Widget build(BuildContext context) {
    final offer = location.featuredOffer;
    if (showBookButton) return _stacked(context, offer);
    return _CardShell(
      onTap: () => openLocation(context, location),
      label: location.name,
      // La colonne de droite fixe la hauteur ; la photo remplit la gauche (pas d'IntrinsicHeight).
      child: Stack(children: [
        Positioned(
          left: 0,
          top: 0,
          bottom: 0,
          width: _photoWidth,
          child: Stack(fit: StackFit.expand, children: [
            MediaImage(imageKey: location.coverImageKey, fallbackIcon: categoryIcon(location.categorySlug)),
            Positioned(
                left: 8, bottom: 8, child: _Pill(icon: Icons.location_on_outlined, text: location.districtLabel)),
          ]),
        ),
        ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 190),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(_photoWidth + 14, 14, 10, 14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              _Tag(location.subcategoryName.toUpperCase()),
              const SizedBox(height: 6),
              Text(location.name, style: serif(22)),
              const SizedBox(height: 4),
              Text(offer?.title ?? location.kindLabel, style: const TextStyle(color: XColors.navyMuted)),
              const SizedBox(height: 10),
              if (offer != null) ...[
                if (offer.isExternalTicket)
                  _InfoLine(
                      icon: Icons.confirmation_number_outlined, text: offer.externalTicketNote ?? 'Billet externe')
                else if (offer.nextSlot != null)
                  _InfoLine(
                    icon: Icons.calendar_today_outlined,
                    text: fmt.slotLabel(offer.nextSlot!.localStart),
                    caption: 'Prochain créneau · indicatif',
                  ),
                if (location.meetingPoint != null)
                  _InfoLine(icon: Icons.place_outlined, text: location.meetingPoint!, caption: 'Point de rendez-vous'),
                const SizedBox(height: 8),
                Text(
                  '${fmt.credits(offer.priceCredits)}${offer.participantsMax > 1 ? ' / pers.' : ''}',
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: XColors.coral),
                ),
                const Align(alignment: Alignment.centerRight, child: Icon(Icons.chevron_right, color: XColors.navy)),
              ],
            ]),
          ),
        ),
      ]),
    );
  }

  /// Photo au-dessus, texte puis bouton « Réserver » en dessous : rien ne se chevauche.
  Widget _stacked(BuildContext context, Offer? offer) {
    return _CardShell(
      onTap: () => openLocation(context, location),
      label: location.name,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        AspectRatio(
          aspectRatio: 16 / 8,
          child: Stack(fit: StackFit.expand, children: [
            MediaImage(imageKey: location.coverImageKey, fallbackIcon: categoryIcon(location.categorySlug)),
            Positioned(
              left: 12,
              bottom: 12,
              child: _Pill(icon: Icons.location_on_outlined, text: location.districtLabel),
            ),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _Tag(location.subcategoryName.toUpperCase()),
            const SizedBox(height: 6),
            Text(location.name, style: serif(24)),
            const SizedBox(height: 4),
            Text(offer?.title ?? location.kindLabel, style: const TextStyle(color: XColors.navyMuted, fontSize: 15)),
            if (offer != null) ...[
              const SizedBox(height: 10),
              if (offer.isExternalTicket)
                _InfoLine(icon: Icons.confirmation_number_outlined, text: offer.externalTicketNote ?? 'Billet externe')
              else if (offer.nextSlot != null)
                _InfoLine(
                  icon: Icons.calendar_today_outlined,
                  text: fmt.slotLabel(offer.nextSlot!.localStart),
                  caption: 'Prochain créneau · indicatif',
                ),
              const SizedBox(height: 4),
              Text(
                '${fmt.credits(offer.priceCredits)}${offer.participantsMax > 1 ? ' / pers.' : ''}',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: XColors.coral),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () => bookFeatured(context, location),
                  child: const Text('Réserver'),
                ),
              ),
            ],
          ]),
        ),
      ]),
    );
  }
}

/// Carte verticale à grande photo (Sport, Beauté).
class PhotoLocationCard extends StatelessWidget {
  const PhotoLocationCard({super.key, required this.location});
  final LocationCard location;

  @override
  Widget build(BuildContext context) {
    final offer = location.featuredOffer;
    final details = [
      if (offer != null) offer.title,
      if (offer != null) fmt.duration(offer.durationMin),
      if (location.distanceM != null) fmt.distance(location.distanceM),
    ].join(' · ');
    return _CardShell(
      onTap: () => openLocation(context, location),
      label: location.name,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        AspectRatio(
          aspectRatio: 16 / 7,
          child: Stack(fit: StackFit.expand, children: [
            MediaImage(imageKey: location.coverImageKey, fallbackIcon: categoryIcon(location.categorySlug)),
            Positioned(left: 12, top: 12, child: _Pill(text: location.kindLabel, dark: true)),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 12, 14),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(location.name, style: serif(24)),
                const SizedBox(height: 4),
                Text(details, style: const TextStyle(color: XColors.navyMuted, fontSize: 15)),
                const SizedBox(height: 6),
                Row(children: [
                  const Icon(Icons.location_on_outlined, size: 18, color: XColors.navyMuted),
                  const SizedBox(width: 4),
                  Text(location.districtLabel, style: const TextStyle(color: XColors.navyMuted)),
                ]),
              ]),
            ),
            if (offer != null)
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 140),
                child: Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(color: XColors.lavender, borderRadius: BorderRadius.circular(20)),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(XIcons.credits, size: 18),
                      const SizedBox(width: 6),
                      Flexible(
                          child: Text(fmt.credits(offer.priceCredits),
                              style: const TextStyle(fontWeight: FontWeight.w700))),
                    ]),
                  ),
                  const SizedBox(height: 10),
                  if (offer.nextSlot != null)
                    Text(fmt.slotLabel(offer.nextSlot!.localStart),
                        textAlign: TextAlign.end, style: const TextStyle(fontWeight: FontWeight.w500))
                  else if (offer.isOpenAccess)
                    const Text('Accès libre', style: TextStyle(fontWeight: FontWeight.w500)),
                ]),
              ),
          ]),
        ),
      ]),
    );
  }
}

class _CardShell extends StatelessWidget {
  const _CardShell({required this.child, required this.onTap, required this.label});
  final Widget child;
  final VoidCallback onTap;
  final String label;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: label,
        child: Pressable(
          onTap: onTap,
          child: DecoratedBox(
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(24), boxShadow: softShadow),
            child: Material(
              color: Colors.white,
              clipBehavior: Clip.antiAlias,
              borderRadius: BorderRadius.circular(24),
              child: InkWell(onTap: onTap, child: child),
            ),
          ),
        ),
      );
}

class _Pill extends StatelessWidget {
  const _Pill({required this.text, this.icon, this.dark = false});
  final String text;
  final IconData? icon;
  final bool dark;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: dark ? XColors.navy.withValues(alpha: 0.7) : Colors.white.withValues(alpha: 0.92),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          if (icon != null) ...[
            Icon(icon, size: 15, color: dark ? Colors.white : XColors.navy),
            const SizedBox(width: 3)
          ],
          Text(text,
              style: TextStyle(fontSize: 13, color: dark ? Colors.white : XColors.navy, fontWeight: FontWeight.w500)),
        ]),
      );
}

class _Tag extends StatelessWidget {
  const _Tag(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Text(
        text,
        style:
            const TextStyle(fontSize: 12, letterSpacing: 1.2, fontWeight: FontWeight.w600, color: XColors.lavenderText),
      );
}

class _InfoLine extends StatelessWidget {
  const _InfoLine({required this.icon, required this.text, this.caption});
  final IconData icon;
  final String text;
  final String? caption;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, size: 18, color: XColors.navy),
          const SizedBox(width: 6),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              if (caption != null) Text(caption!, style: const TextStyle(fontSize: 12, color: XColors.navyMuted)),
              Text(text, style: const TextStyle(fontWeight: FontWeight.w600)),
            ]),
          ),
        ]),
      );
}
