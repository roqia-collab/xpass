import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/format.dart' as fmt;
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../account/login_sheet.dart';
import '../booking/booking_repository.dart';
import '../catalog/catalog_repository.dart';
import '../catalog/models.dart';

void openEvent(BuildContext context, VenueEvent event) => context.push('/explore/evenement/${event.id}');

/// Carte événement, même langage que les établissements de l'accueil.
class EventPoster extends StatelessWidget {
  const EventPoster({super.key, required this.event});
  final VenueEvent event;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: event.title,
        child: Pressable(
          onTap: () => openEvent(context, event),
          child: DecoratedBox(
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(24), boxShadow: softShadow),
            child: Material(
              color: Colors.white,
              clipBehavior: Clip.antiAlias,
              borderRadius: BorderRadius.circular(24),
              child: InkWell(
                onTap: () => openEvent(context, event),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  AspectRatio(
                    aspectRatio: 16 / 8,
                    child: Stack(fit: StackFit.expand, children: [
                      MediaImage(
                        imageKey: event.coverImageKey,
                        fallbackIcon: categoryIcon(event.categorySlug),
                        semanticLabel: event.title,
                      ),
                      Positioned(left: 12, top: 12, child: _DateBadge(when: event.startsAt)),
                      Positioned(
                        left: 12,
                        bottom: 12,
                        child: _Chip(icon: Icons.location_on_outlined, text: event.districtLabel),
                      ),
                    ]),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(event.title, style: serif(24)),
                      const SizedBox(height: 4),
                      Text(event.locationName, style: const TextStyle(color: XColors.navyMuted, fontSize: 15)),
                      const SizedBox(height: 10),
                      Row(children: [
                        const Icon(Icons.schedule, size: 18, color: XColors.navyMuted),
                        const SizedBox(width: 6),
                        Expanded(child: Text(fmt.eventSpan(event.startsAt, event.endsAt), style: const TextStyle(fontSize: 14))),
                      ]),
                      const SizedBox(height: 12),
                      Row(children: [
                        Text(fmt.credits(event.priceCredits),
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: XColors.coral)),
                        const Spacer(),
                        const Text('Voir', style: TextStyle(fontWeight: FontWeight.w600)),
                        const Icon(Icons.chevron_right),
                      ]),
                    ]),
                  ),
                ]),
              ),
            ),
          ),
        ),
      );
}

class _DateBadge extends StatelessWidget {
  const _DateBadge({required this.when});
  final DateTime when;

  @override
  Widget build(BuildContext context) {
    const months = ['JAN', 'FÉV', 'MAR', 'AVR', 'MAI', 'JUN', 'JUL', 'AOÛ', 'SEP', 'OCT', 'NOV', 'DÉC'];
    return Container(
      width: 58,
      padding: const EdgeInsets.symmetric(vertical: 6),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
      child: Column(children: [
        Text(months[when.month - 1], style: const TextStyle(fontSize: 11, letterSpacing: 1, fontWeight: FontWeight.w700)),
        Text('${when.day}', style: serif(22)),
        Text(fmt.hhmm(when), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
      ]),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.text, this.icon});
  final String text;
  final IconData? icon;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.92), borderRadius: BorderRadius.circular(20)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          if (icon != null) ...[Icon(icon, size: 15, color: XColors.navy), const SizedBox(width: 3)],
          Text(text, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
        ]),
      );
}

class EventsScreen extends ConsumerWidget {
  const EventsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final city = ref.watch(selectedCityProvider);
    final events = ref.watch(eventsProvider(city.slug));
    return Scaffold(
      backgroundColor: XColors.cream,
      body: events.when(
        loading: () => const LoadingView(),
        error: (e, _) => ErrorView(error: e, onRetry: () => ref.invalidate(eventsProvider(city.slug))),
        data: (list) => CustomScrollView(slivers: [
          SliverToBoxAdapter(
            child: SafeArea(
              bottom: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(8, 4, 16, 8),
                child: Row(children: [
                  IconButton(
                    tooltip: 'Retour',
                    onPressed: () => context.canPop() ? context.pop() : context.go('/explore'),
                    icon: const Icon(Icons.arrow_back_ios_new),
                  ),
                  Expanded(child: Text('Événements', style: serif(28))),
                ]),
              ),
            ),
          ),
          if (list.isEmpty)
            const SliverFillRemaining(hasScrollBody: false, child: EmptyView(message: 'Aucun événement à venir pour le moment.'))
          else
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
              sliver: SliverList.separated(
                itemCount: list.length,
                separatorBuilder: (_, __) => const SizedBox(height: 16),
                itemBuilder: (_, i) => FadeSlideIn(index: i, child: EventPoster(event: list[i])),
              ),
            ),
        ]),
      ),
    );
  }
}

class EventScreen extends ConsumerWidget {
  const EventScreen({super.key, required this.id});
  final String id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final event = ref.watch(eventDetailProvider(id));
    return Scaffold(
      backgroundColor: XColors.cream,
      body: event.when(
        loading: () => const LoadingView(),
        error: (e, _) => SafeArea(
          child: Column(children: [
            Align(
              alignment: Alignment.centerLeft,
              child: BackButton(onPressed: () => context.canPop() ? context.pop() : context.go('/explore')),
            ),
            Expanded(child: ErrorView(error: e, onRetry: () => ref.invalidate(eventDetailProvider(id)))),
          ]),
        ),
        data: (e) => _Detail(event: e),
      ),
    );
  }
}

class _Detail extends StatelessWidget {
  const _Detail({required this.event});
  final VenueEvent event;

  @override
  Widget build(BuildContext context) => Stack(children: [
        CustomScrollView(slivers: [
          SliverToBoxAdapter(
            child: SizedBox(
              height: 300,
              child: Stack(fit: StackFit.expand, children: [
                MediaImage(
                  imageKey: event.coverImageKey,
                  fallbackIcon: categoryIcon(event.categorySlug),
                  semanticLabel: event.title,
                ),
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
                    child: Align(
                      alignment: Alignment.topLeft,
                      child: IconButton(
                        tooltip: 'Retour',
                        onPressed: () => context.canPop() ? context.pop() : context.go('/explore'),
                        icon: const Icon(Icons.arrow_back_ios_new),
                      ),
                    ),
                  ),
                ),
              ]),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 120),
            sliver: SliverList.list(children: [
              Text(event.title, style: serif(36)),
              const SizedBox(height: 12),
              Text(fmt.eventSpan(event.startsAt, event.endsAt), style: const TextStyle(fontSize: 16)),
              const SizedBox(height: 16),
              Material(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                child: InkWell(
                  borderRadius: BorderRadius.circular(20),
                  onTap: () => context.push('/explore/lieu/${event.locationSlug}'),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(children: [
                      const Icon(Icons.storefront_outlined),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(event.locationName, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                          const SizedBox(height: 2),
                          Text(
                            '${event.addressLine}${event.districtLabel.isEmpty ? '' : ' · ${event.districtLabel}'}',
                            style: const TextStyle(color: XColors.navyMuted),
                          ),
                        ]),
                      ),
                      const Icon(Icons.chevron_right),
                    ]),
                  ),
                ),
              ),
              if (event.summary.isNotEmpty) ...[
                const SizedBox(height: 18),
                Text(event.summary, style: const TextStyle(fontSize: 16, height: 1.4)),
              ],
              const SizedBox(height: 18),
              Text(fmt.credits(event.priceCredits),
                  style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: XColors.coral)),
              const SizedBox(height: 6),
              const Text('Une place, débitée en crédits. Vous confirmez ensuite, comme pour une prestation.',
                  style: TextStyle(color: XColors.navyMuted)),
            ]),
          ),
        ]),
        Positioned(
          left: 20,
          right: 20,
          bottom: 16,
          child: _BookEvent(event: event),
        ),
      ]);
}

class _BookEvent extends ConsumerStatefulWidget {
  const _BookEvent({required this.event});
  final VenueEvent event;

  @override
  ConsumerState<_BookEvent> createState() => _BookEventState();
}

class _BookEventState extends ConsumerState<_BookEvent> {
  bool _busy = false;
  String? _error;

  Future<void> _reserve() async {
    if (!await ensureSignedIn(context, ref)) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final booking = await ref.read(bookingRepositoryProvider).holdEvent(
            eventId: widget.event.id,
            expectedPriceCredits: widget.event.priceCredits,
            idempotencyKey: newIdempotencyKey(),
          );
      if (mounted) context.push('/explore/reservation/${booking.id}');
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (e) {
      if (mounted) setState(() => _error = 'La réservation n’a pas abouti.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Column(mainAxisSize: MainAxisSize.min, children: [
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: XColors.coral)),
          ),
        CoralButton(label: _busy ? 'Réservation…' : 'Réserver cette séance', onPressed: _busy ? null : _reserve),
      ]);
}

class LocationEvents extends ConsumerWidget {
  const LocationEvents({super.key, required this.slug});
  final String slug;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final events = ref.watch(locationEventsProvider(slug));
    return events.maybeWhen(
      data: (list) {
        if (list.isEmpty) return const SizedBox.shrink();
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Événements', style: serif(26)),
          const SizedBox(height: 12),
          for (final event in list) ...[
            EventPoster(event: event),
            const SizedBox(height: 14),
          ],
        ]);
      },
      orElse: () => const SizedBox.shrink(),
    );
  }
}
