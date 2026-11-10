import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth.dart';
import '../../core/format.dart' as fmt;
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../account/login_sheet.dart';
import 'booking_repository.dart';
import 'models.dart';
import '../../core/l10n.dart';

/// Maquette 11 — Mes réservations (à venir, passées, annulées).
class BookingsScreen extends ConsumerStatefulWidget {
  const BookingsScreen({super.key});

  @override
  ConsumerState<BookingsScreen> createState() => _BookingsScreenState();
}

class _BookingsScreenState extends ConsumerState<BookingsScreen> {
  String _scope = 'upcoming';
  static const _labels = {'upcoming': 'À venir', 'past': 'Passées', 'cancelled': 'Annulées'};

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(authProvider);
    return Scaffold(
      body: SafeArea(
        child: session.valueOrNull == null
            ? SignedOutView(message: context.l10n.signInToSeeBookings)
            : _buildList(context),
      ),
    );
  }

  Widget _buildList(BuildContext context) {
    final list = ref.watch(bookingListProvider(_scope));
    final counts = list.valueOrNull?.counts ?? const {};
    return RefreshIndicator(
      color: XColors.coral,
      onRefresh: () async => ref.invalidate(bookingListProvider),
      child: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 32), children: [
        const XpassLogo(height: 28),
        const SizedBox(height: 16),
        Text(context.l10n.myBookings, style: serif(40)),
        const SizedBox(height: 6),
        Text(context.l10n.myBookingsSubtitle, style: const TextStyle(color: XColors.navyMuted, fontSize: 16)),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(color: XColors.creamDark, borderRadius: BorderRadius.circular(18)),
          child: Row(children: [
            for (final e in _labels.entries)
              Expanded(
                child: Semantics(
                  selected: e.key == _scope,
                  button: true,
                  child: Material(
                    color: e.key == _scope ? XColors.coral : Colors.transparent,
                    borderRadius: BorderRadius.circular(14),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(14),
                      onTap: () => setState(() => _scope = e.key),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        child: Text(
                          '${e.value}${counts[e.key] != null ? ' (${counts[e.key]})' : ''}',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontWeight: FontWeight.w600,
                            color: e.key == _scope ? Colors.white : XColors.navy,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
          ]),
        ),
        const SizedBox(height: 18),
        list.when(
          loading: () => const SizedBox(height: 200, child: LoadingView()),
          error: (e, _) => ErrorView(error: e, onRetry: () => ref.invalidate(bookingListProvider(_scope))),
          data: (l) => l.items.isEmpty
              ? EmptyView(
                  message: switch (_scope) {
                    'upcoming' => 'Aucune réservation à venir.',
                    'past' => 'Aucune expérience passée.',
                    _ => 'Aucune réservation annulée.',
                  },
                )
              : Column(children: [
                  for (final (i, b) in l.items.indexed) ...[
                    FadeSlideIn(index: i, child: _BookingCard(booking: b)),
                    const SizedBox(height: 14),
                  ],
                ]),
        ),
      ]),
    );
  }
}

class SignedOutView extends ConsumerWidget {
  const SignedOutView({super.key, required this.message});
  final String message;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const XpassLogo(height: 28),
          const Spacer(),
          const Icon(Icons.lock_outline, size: 40, color: XColors.navyMuted),
          const SizedBox(height: 12),
          Text(message, style: serif(26)),
          const SizedBox(height: 20),
          FilledButton(onPressed: () => ensureSignedIn(context, ref), child: const Text('Se connecter')),
          const Spacer(),
        ]),
      );
}

class _BookingCard extends StatelessWidget {
  const _BookingCard({required this.booking});
  final Booking booking;

  @override
  Widget build(BuildContext context) {
    final b = booking;
    return Material(
      color: Colors.white,
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(XRadius.card),
        side: const BorderSide(color: XColors.line),
      ),
      child: InkWell(
        onTap: () => context.push(b.isRedeemed ? '/reservations/${b.id}/recu' : '/reservations/${b.id}'),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          SizedBox(
            height: 130,
            child: Stack(fit: StackFit.expand, children: [
              MediaImage(imageKey: b.coverImageKey),
              Positioned(left: 12, top: 12, child: StatusPill(booking: b)),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 12, 14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(b.categoryName.toUpperCase(),
                  style: const TextStyle(letterSpacing: 1.5, fontSize: 12, color: XColors.lavenderText)),
              const SizedBox(height: 4),
              Row(children: [
                Expanded(child: Text('${b.locationName} · ${b.offerTitle}', style: serif(22))),
                const Icon(Icons.chevron_right),
              ]),
              const SizedBox(height: 8),
              if (b.isConfirmed)
                Align(
                  alignment: Alignment.centerLeft,
                  child: FilledButton(
                    style: FilledButton.styleFrom(minimumSize: const Size(0, 40), padding: const EdgeInsets.symmetric(horizontal: 16)),
                    onPressed: () => context.push('/reservations/${b.id}'),
                    child: const Text('Ouvrir le pass'),
                  ),
                ),
              if (b.isConfirmed) const SizedBox(height: 8),
              Wrap(spacing: 16, runSpacing: 6, children: [
                _Meta(Icons.calendar_today_outlined, fmt.shortDate(b.localStart)),
                _Meta(Icons.schedule, fmt.hhmm(b.localStart)),
                _Meta(XIcons.credits, '${fmt.credits(b.totalCredits)} ${_creditVerb(b)}'),
              ]),
            ]),
          ),
        ]),
      ),
    );
  }

  String _creditVerb(Booking b) => switch (b.status) {
        'confirmed' || 'held' => 'réservés',
        'cancelled' => b.lateCancellation ? 'débités' : 'restitués',
        'redeemed' => 'utilisés',
        _ => '',
      };
}

class StatusPill extends StatelessWidget {
  const StatusPill({super.key, required this.booking});
  final Booking booking;

  @override
  Widget build(BuildContext context) {
    final ok = booking.isConfirmed;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(color: ok ? XColors.mint : XColors.lavender, borderRadius: BorderRadius.circular(20)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        if (ok) const Icon(Icons.check_circle, size: 16, color: Color(0xFF2F7A45)),
        if (ok) const SizedBox(width: 6),
        Text(booking.statusLabel, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
      ]),
    );
  }
}

class _Meta extends StatelessWidget {
  const _Meta(this.icon, this.text);
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 18, color: XColors.navyMuted),
        const SizedBox(width: 6),
        Text(text, style: const TextStyle(fontSize: 15)),
      ]);
}
