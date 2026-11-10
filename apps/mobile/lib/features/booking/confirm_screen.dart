import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/format.dart' as fmt;
import '../../core/theme.dart';
import '../../core/widgets.dart';
import 'booking_repository.dart';
import 'models.dart';
import '../../core/l10n.dart';

/// Maquette 10 — récapitulatif d'une réserve HELD, compte à rebours et confirmation.
class ConfirmScreen extends ConsumerStatefulWidget {
  const ConfirmScreen({super.key, required this.bookingId});
  final String bookingId;

  @override
  ConsumerState<ConfirmScreen> createState() => _ConfirmScreenState();
}

class _ConfirmScreenState extends ConsumerState<ConfirmScreen> {
  Timer? _timer;
  DateTime? _deadline; // horloge locale + secondes restantes données par le serveur
  bool _busy = false;
  String? _confirmKey;

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _startCountdown(Booking b) {
    if (_deadline != null || b.holdSecondsRemaining == null) return;
    _deadline = DateTime.now().add(Duration(seconds: b.holdSecondsRemaining!));
    _timer = Timer.periodic(const Duration(seconds: 1), (_) => mounted ? setState(() {}) : null);
  }

  Duration get _remaining {
    final d = _deadline?.difference(DateTime.now()) ?? Duration.zero;
    return d.isNegative ? Duration.zero : d;
  }

  @override
  Widget build(BuildContext context) {
    final booking = ref.watch(bookingProvider(widget.bookingId));
    return Scaffold(
      body: booking.when(
        loading: () => const LoadingView(),
        error: (e, _) =>
            SafeArea(child: ErrorView(error: e, onRetry: () => ref.invalidate(bookingProvider(widget.bookingId)))),
        data: (b) {
          if (b.isHeld) WidgetsBinding.instance.addPostFrameCallback((_) => _startCountdown(b));
          final expired = b.status == 'expired' || (b.isHeld && _deadline != null && _remaining == Duration.zero);
          return Stack(children: [
            ListView(padding: const EdgeInsets.fromLTRB(20, 0, 20, 120), children: [
              SafeArea(
                bottom: false,
                child: Row(children: [
                  const XpassLogo(height: 28),
                  const Spacer(),
                  IconButton.filledTonal(
                    tooltip: 'Retour',
                    onPressed: _busy ? null : () => _leave(b),
                    icon: const Icon(Icons.chevron_left),
                  ),
                ]),
              ),
              const SizedBox(height: 16),
              const Text('RÉSERVATION', style: TextStyle(letterSpacing: 3, fontSize: 12, color: XColors.navyMuted)),
              const SizedBox(height: 6),
              Text(context.l10n.confirmBooking, style: serif(36)),
              const SizedBox(height: 8),
              Text(context.l10n.checkBeforeConfirm, style: const TextStyle(fontSize: 16, color: XColors.navyMuted)),
              const SizedBox(height: 18),
              BookingSummaryCard(booking: b),
              const SizedBox(height: 12),
              if (b.isHeld && !expired)
                _HoldBanner(remaining: _remaining)
              else if (expired)
                _InfoBox(
                  color: const Color(0xFFFFE7E2),
                  icon: Icons.timer_off_outlined,
                  title: context.l10n.timeExpired,
                  body: context.l10n.slotReleased,
                ),
              const SizedBox(height: 12),
              _TotalCard(booking: b),
              const SizedBox(height: 12),
              _CancellationPolicy(booking: b),
            ]),
            Positioned(
              left: 20,
              right: 20,
              bottom: 16,
              child: expired
                  ? CoralButton(label: context.l10n.chooseAnotherSlot, onPressed: () => context.pop())
                  : CoralButton(
                      label: _busy ? 'Confirmation…' : 'Confirmer · ${fmt.credits(b.totalCredits)}',
                      onPressed: b.isHeld && !_busy ? () => _confirm(b) : null,
                    ),
            ),
          ]);
        },
      ),
    );
  }

  Future<void> _confirm(Booking b) async {
    setState(() => _busy = true);
    _confirmKey ??= newIdempotencyKey();
    try {
      final confirmed = await ref.read(bookingRepositoryProvider).confirm(b.id, _confirmKey!);
      invalidateBookingData(ref);
      ref.invalidate(bookingProvider(confirmed.id));
      if (!mounted) return;
      // Succès renvoyé par le serveur : on affiche la réservation confirmée.
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(context.l10n.bookingConfirmed)));
      context.go('/reservations/${confirmed.id}');
    } on ApiException catch (e) {
      if (!e.isNetwork) _confirmKey = null;
      ref.invalidate(bookingProvider(widget.bookingId));
      invalidateBookingData(ref);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(
              e.isNetwork ? '${e.message} Votre réservation n’est peut-être pas confirmée : réessayez.' : e.message),
        ));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Quitter libère immédiatement le créneau (sinon il expire de lui-même après 5 minutes).
  Future<void> _leave(Booking b) async {
    if (b.isHeld) {
      try {
        await ref.read(bookingRepositoryProvider).cancel(b.id, newIdempotencyKey());
      } on ApiException {
        // La réserve expirera d'elle-même ; aucun crédit n'est consommé.
      }
      invalidateBookingData(ref);
    }
    if (mounted) context.pop();
  }
}

class BookingSummaryCard extends StatelessWidget {
  const BookingSummaryCard({super.key, required this.booking});
  final Booking booking;

  @override
  Widget build(BuildContext context) {
    final b = booking;
    final rows = [
      if (b.resourceName != null) (Icons.person_outline, b.resourceName!),
      (Icons.calendar_today_outlined, fmt.longDate(b.localStart)),
      (Icons.schedule, fmt.hhmm(b.localStart)),
      (Icons.hourglass_empty, fmt.duration(b.durationMin)),
      (Icons.group_outlined, '${b.partySize} personne${b.partySize > 1 ? 's' : ''}'),
    ];
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(XRadius.card),
        border: Border.all(color: XColors.line),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(14),
          child: SizedBox(width: 110, height: 150, child: MediaImage(imageKey: b.coverImageKey)),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(b.locationName, style: serif(22)),
            Text(b.kindLabel.toUpperCase(),
                style: const TextStyle(letterSpacing: 2, fontSize: 11, color: XColors.lavenderText)),
            const SizedBox(height: 6),
            Text(b.offerTitle, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
            const SizedBox(height: 6),
            for (final (icon, text) in rows)
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Row(children: [
                  Icon(icon, size: 18, color: XColors.navyMuted),
                  const SizedBox(width: 8),
                  Expanded(child: Text(text)),
                ]),
              ),
          ]),
        ),
      ]),
    );
  }
}

class _HoldBanner extends StatelessWidget {
  const _HoldBanner({required this.remaining});
  final Duration remaining;

  @override
  Widget build(BuildContext context) {
    final mm = remaining.inMinutes.toString().padLeft(2, '0');
    final ss = (remaining.inSeconds % 60).toString().padLeft(2, '0');
    return Semantics(
      liveRegion: true,
      label: 'Créneau maintenu pendant ${remaining.inMinutes} minutes et ${remaining.inSeconds % 60} secondes',
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: XColors.lavender, borderRadius: BorderRadius.circular(XRadius.card)),
        child: Row(children: [
          const CircleAvatar(
              radius: 26, backgroundColor: Colors.white, child: Icon(Icons.lock_outline, color: XColors.navy)),
          const SizedBox(width: 14),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text.rich(TextSpan(children: [
                const TextSpan(
                    text: 'Créneau maintenu pendant ', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                TextSpan(
                    text: '$mm:$ss',
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: XColors.coral)),
              ])),
              const SizedBox(height: 2),
              Text(context.l10n.creditsHeld, style: const TextStyle(color: XColors.navyMuted)),
            ]),
          ),
        ]),
      ),
    );
  }
}

class _TotalCard extends StatelessWidget {
  const _TotalCard({required this.booking});
  final Booking booking;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(XRadius.card),
          border: Border.all(color: XColors.line),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Total : ${fmt.credits(booking.totalCredits)}', style: serif(26)),
          if (booking.priceAdjustments.isNotEmpty)
            Text(
              [
                for (final a in booking.priceAdjustments)
                  switch (a) {
                    'peak' => context.l10n.slotPricePeak,
                    'demand' => context.l10n.slotPriceDemand,
                    _ => context.l10n.slotPriceLastMinute,
                  }
              ].join(' · '),
              style: const TextStyle(color: XColors.navyMuted, fontSize: 13),
            ),
          const SizedBox(height: 8),
          for (final f in booking.funding)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(children: [
                Icon(
                    f.source == 'employer'
                        ? Icons.business_center_outlined
                        : (f.source == 'promotional' ? Icons.card_giftcard : Icons.person_outline),
                    color: XColors.navyMuted),
                const SizedBox(width: 12),
                Expanded(child: Text(f.label, style: const TextStyle(fontSize: 16))),
                Text(fmt.credits(f.credits), style: const TextStyle(fontSize: 16)),
              ]),
            ),
        ]),
      );
}

class _CancellationPolicy extends StatelessWidget {
  const _CancellationPolicy({required this.booking});
  final Booking booking;

  @override
  Widget build(BuildContext context) {
    final until = booking.localFreeCancellationUntil;
    return Column(children: [
      _InfoBox(
        color: XColors.mint,
        icon: Icons.event_available_outlined,
        title: 'Annulation gratuite jusqu’au ${fmt.dayMonth(until)} à ${fmt.hhmm(until)}',
        body: context.l10n.freeCancelUntil,
      ),
      const SizedBox(height: 8),
      _InfoBox(
        color: const Color(0xFFFFF1EC),
        icon: Icons.error_outline,
        title: context.l10n.cancelAfterDate,
        body: context.l10n.lateCancelInfo(
            fmt.credits(booking.lateCancellationRefundCredits), fmt.credits(booking.totalCredits)),
      ),
    ]);
  }
}

class _InfoBox extends StatelessWidget {
  const _InfoBox({required this.color, required this.icon, required this.title, required this.body});
  final Color color;
  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(XRadius.card)),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, color: XColors.navy),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              const SizedBox(height: 2),
              Text(body, style: const TextStyle(color: XColors.navyMuted)),
            ]),
          ),
        ]),
      );
}
