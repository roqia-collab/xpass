import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api_client.dart';
import '../../core/format.dart' as fmt;
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../account/profile_screen.dart';
import 'booking_repository.dart';
import 'confirm_screen.dart';
import 'models.dart';
import '../../core/l10n.dart';

/// Maquette 12 — réservation confirmée, QR éphémère, agenda, itinéraire, annulation.
class BookingDetailScreen extends ConsumerStatefulWidget {
  const BookingDetailScreen({super.key, required this.bookingId});
  final String bookingId;

  @override
  ConsumerState<BookingDetailScreen> createState() => _BookingDetailScreenState();
}

class _BookingDetailScreenState extends ConsumerState<BookingDetailScreen> {
  Timer? _poll;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    // Le partenaire valide de son côté : on suit le statut pour afficher le reçu dès la consommation.
    _poll = Timer.periodic(const Duration(seconds: 5), (_) => ref.invalidate(bookingProvider(widget.bookingId)));
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(bookingProvider(widget.bookingId), (_, next) {
      final b = next.valueOrNull;
      if (b != null && b.isRedeemed) {
        _poll?.cancel();
        invalidateBookingData(ref);
        context.pushReplacement('/reservations/${b.id}/recu');
      }
    });
    final booking = ref.watch(bookingProvider(widget.bookingId));
    return Scaffold(
      body: booking.when(
        skipLoadingOnRefresh: true,
        loading: () => const LoadingView(),
        error: (e, _) =>
            SafeArea(child: ErrorView(error: e, onRetry: () => ref.invalidate(bookingProvider(widget.bookingId)))),
        data: (b) => _body(context, b),
      ),
    );
  }

  Widget _body(BuildContext context, Booking b) {
    final late = DateTime.now().isAfter(b.localFreeCancellationUntil);
    return ListView(padding: const EdgeInsets.fromLTRB(20, 0, 20, 32), children: [
      SafeArea(
        bottom: false,
        child: Row(children: [
          IconButton(
            tooltip: 'Retour',
            onPressed: () => context.canPop() ? context.pop() : context.go('/reservations'),
            icon: const Icon(Icons.arrow_back),
          ),
          const XpassLogo(height: 26),
        ]),
      ),
      PhotoHeader(
        imageKey: 'demo/screens/confirmed.jpg',
        widthFactor: 0.5,
        height: 190,
        top: -60,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const SizedBox(height: 12),
          SizedBox(
            width: MediaQuery.sizeOf(context).width * 0.6,
            child: Text(b.isConfirmed ? context.l10n.bookingConfirmed : b.statusLabel, style: serif(38)),
          ),
          if (b.isConfirmed) ...[
            const SizedBox(height: 6),
            SizedBox(
              width: MediaQuery.sizeOf(context).width * 0.55,
              child:
                  Text(context.l10n.sessionConfirmed, style: const TextStyle(fontSize: 16, color: XColors.navyMuted)),
            ),
          ],
        ]),
      ),
      const SizedBox(height: 16),
      BookingSummaryCard(booking: b),
      const SizedBox(height: 12),
      Row(children: [
        const Icon(XIcons.credits),
        const SizedBox(width: 10),
        Text('${fmt.credits(b.totalCredits)} ${b.isConfirmed ? 'réservés' : ''}',
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
      ]),
      const SizedBox(height: 14),
      if (b.isConfirmed) ...[
        PassPanel(bookingId: b.id),
        const SizedBox(height: 14),
        Row(children: [
          Expanded(
            child: _ActionTile(
              icon: Icons.calendar_month_outlined,
              label: context.l10n.addToCalendar,
              onTap: () => showAddToCalendar(context, ref, b),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _ActionTile(
              icon: Icons.place_outlined,
              label: 'Itinéraire',
              onTap: () => launchUrl(
                Uri.https('www.google.com', '/maps/search/', {'api': '1', 'query': b.address}),
                mode: LaunchMode.externalApplication,
              ),
            ),
          ),
        ]),
        const SizedBox(height: 12),
        _ActionTile(
          icon: Icons.chat_bubble_outline,
          label: context.l10n.writeToVenue,
          onTap: () => context.push('/reservations/${b.id}/messages'),
        ),
        const SizedBox(height: 18),
        const Divider(),
        Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
          TextButton.icon(
            onPressed: _busy ? null : () => _cancel(b, late),
            icon: const Icon(Icons.close, color: XColors.navy),
            label: Text(context.l10n.cancelBooking, style: const TextStyle(color: XColors.navy)),
          ),
          TextButton.icon(
            // Assistance réelle (lot 8a) : formulaire de demande au support XPASS.
            onPressed: () => showSupportForm(context, ref),
            icon: const Icon(Icons.headset_mic_outlined, color: XColors.navy),
            label: Text(context.l10n.needHelp, style: const TextStyle(color: XColors.navy)),
          ),
        ]),
        Text(
          late
              ? context.l10n.lateCancelInfo(
                  fmt.credits(b.lateCancellationRefundCredits), fmt.credits(b.totalCredits))
              : 'Annulation gratuite jusqu’au ${fmt.dayMonth(b.localFreeCancellationUntil)} à ${fmt.hhmm(b.localFreeCancellationUntil)}.',
          textAlign: TextAlign.center,
          style: const TextStyle(color: XColors.navyMuted, fontSize: 13),
        ),
      ],
    ]);
  }

  Future<void> _cancel(Booking b, bool late) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.l10n.cancelBookingQuestion),
        content: Text(late
            ? context.l10n.lateCancelInfo(fmt.credits(b.lateCancellationRefundCredits), fmt.credits(b.totalCredits))
            : 'Vos ${fmt.credits(b.totalCredits)} vous seront restitués.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Garder')),
          FilledButton(
            style: FilledButton.styleFrom(minimumSize: const Size(0, 44)),
            onPressed: () => Navigator.pop(context, true),
            child: Text(context.l10n.cancelBooking),
          ),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final res = await ref.read(bookingRepositoryProvider).cancel(b.id, newIdempotencyKey());
      invalidateBookingData(ref);
      ref.invalidate(bookingProvider(widget.bookingId));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(res.lateCancellation
              ? context.l10n.cancelledPartlyRefunded(fmt.credits(res.refundedCredits))
              : context.l10n.cancelledRefunded),
        ));
      }
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}

/// QR + code manuel, renouvelés automatiquement avant expiration. Aucun jeton n'est conservé localement.
class PassPanel extends ConsumerStatefulWidget {
  const PassPanel({super.key, required this.bookingId});
  final String bookingId;

  @override
  ConsumerState<PassPanel> createState() => _PassPanelState();
}

class _PassPanelState extends ConsumerState<PassPanel> {
  PassInfo? _pass;
  DateTime? _renewAt;
  String? _error;
  Timer? _tick;

  @override
  void initState() {
    super.initState();
    _issue();
    _tick = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      if (_renewAt != null && DateTime.now().isAfter(_renewAt!)) {
        _renewAt = null;
        _issue();
      }
      setState(() {});
    });
  }

  @override
  void dispose() {
    _tick?.cancel();
    super.dispose();
  }

  Future<void> _issue() async {
    try {
      final p = await ref.read(bookingRepositoryProvider).issuePass(widget.bookingId);
      if (!mounted) return;
      setState(() {
        _pass = p;
        _error = null;
        // Renouvelé 5 s avant l'expiration serveur pour éviter un code périmé à l'écran.
        _renewAt = DateTime.now().add(Duration(seconds: p.expiresIn - 5));
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _pass = null;
        _error = e.message;
        _renewAt = e.isNetwork ? DateTime.now().add(const Duration(seconds: 10)) : null;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final left = _renewAt == null ? Duration.zero : _renewAt!.difference(DateTime.now());
    final secs = left.isNegative ? 0 : left.inSeconds;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: XColors.lavender, borderRadius: BorderRadius.circular(XRadius.card)),
      child: Column(children: [
        if (_pass == null && _error == null) const SizedBox(height: 220, child: LoadingView()),
        if (_error != null) ...[
          const Icon(Icons.qr_code_2, size: 48, color: XColors.navyMuted),
          const SizedBox(height: 8),
          Text(_error!, textAlign: TextAlign.center),
          TextButton(onPressed: _issue, child: const Text('Réessayer')),
        ],
        if (_pass != null) ...[
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
            child: Semantics(
              label: context.l10n.qrSemantics,
              child: QrImageView(
                data: _pass!.qrPayload,
                size: 200,
                eyeStyle: const QrEyeStyle(eyeShape: QrEyeShape.square, color: XColors.navy),
                dataModuleStyle:
                    const QrDataModuleStyle(dataModuleShape: QrDataModuleShape.square, color: XColors.navy),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Text.rich(TextSpan(children: [
            const TextSpan(text: 'Code renouvelé dans ', style: TextStyle(fontSize: 16)),
            TextSpan(
              text: '00:${secs.toString().padLeft(2, '0')}',
              style: const TextStyle(fontSize: 16, color: XColors.coral, fontWeight: FontWeight.w700),
            ),
          ])),
          const SizedBox(height: 4),
          Text(context.l10n.showToPartner, style: const TextStyle(color: XColors.navyMuted)),
          const SizedBox(height: 10),
          SelectableText('Code : ${_pass!.manualCode}',
              style: const TextStyle(fontSize: 18, letterSpacing: 2, fontWeight: FontWeight.w700)),
        ],
      ]),
    );
  }
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: XColors.lavender,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 18),
            child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              Icon(icon),
              const SizedBox(width: 8),
              Flexible(child: Text(label, style: const TextStyle(fontWeight: FontWeight.w600))),
            ]),
          ),
        ),
      );
}

/// Maquette 17 — ajout volontaire à l'agenda. L'événement ne contient jamais le jeton QR.
Future<void> showAddToCalendar(BuildContext context, WidgetRef ref, Booking b) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: XColors.cream,
    builder: (sheet) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Expanded(child: Text(context.l10n.addToCalendar, style: serif(30))),
            IconButton(tooltip: 'Fermer', onPressed: () => Navigator.pop(sheet), icon: const Icon(Icons.close)),
          ]),
          Text(context.l10n.calendarIntro, style: const TextStyle(color: XColors.navyMuted)),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: XColors.creamDark, borderRadius: BorderRadius.circular(XRadius.card)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(b.locationName, style: serif(22)),
              const SizedBox(height: 6),
              Text(fmt.longDate(b.localStart)),
              Text('${fmt.hhmm(b.localStart)} – ${fmt.hhmm(b.localStart.add(Duration(minutes: b.durationMin)))}'),
              Text(b.address),
            ]),
          ),
          const SizedBox(height: 14),
          Text(context.l10n.chooseCalendar, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
          const SizedBox(height: 8),
          _CalendarChoice(
            icon: Icons.phone_iphone,
            label: context.l10n.phoneCalendar,
            onTap: () => _shareIcs(sheet, ref, b),
          ),
          _CalendarChoice(
            icon: Icons.event,
            label: 'Google Calendar',
            onTap: () => launchUrl(_googleCalendarUrl(b), mode: LaunchMode.externalApplication),
          ),
          const SizedBox(height: 6),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: XColors.lavender, borderRadius: BorderRadius.circular(16)),
            child: Row(children: [
              const Icon(Icons.notifications_none),
              const SizedBox(width: 10),
              Expanded(child: Text(context.l10n.reminderSuggested)),
            ]),
          ),
          const SizedBox(height: 10),
          Text(
            context.l10n.calendarNoQr,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 12, color: XColors.navyMuted),
          ),
        ]),
      ),
    ),
  );
}

Uri _googleCalendarUrl(Booking b) {
  String f(DateTime d) => '${d.toUtc().toIso8601String().replaceAll('-', '').replaceAll(':', '').split('.').first}Z';
  final end = b.startsAtUtc.add(Duration(minutes: b.durationMin));
  return Uri.https('calendar.google.com', '/calendar/render', {
    'action': 'TEMPLATE',
    'text': '${b.offerTitle} · ${b.locationName}',
    'dates': '${f(b.startsAtUtc)}/${f(end)}',
    'location': b.address,
    'details': 'Réservation XPASS. Présentez votre QR depuis l’application le jour J.',
  });
}

Future<void> _shareIcs(BuildContext context, WidgetRef ref, Booking b) async {
  try {
    final ics = await ref.read(bookingRepositoryProvider).calendarIcs(b.id);
    await Share.shareXFiles([
      XFile.fromData(utf8.encode(ics), mimeType: 'text/calendar', name: 'xpass-reservation.ics'),
    ], fileNameOverrides: [
      'xpass-reservation.ics'
    ]);
  } on ApiException catch (e) {
    if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
  }
}

class _CalendarChoice extends StatelessWidget {
  const _CalendarChoice({required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Material(
          color: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: const BorderSide(color: XColors.line),
          ),
          child: ListTile(
            leading: CircleAvatar(backgroundColor: XColors.lavender, child: Icon(icon, color: XColors.navy)),
            title: Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
            trailing: const Icon(Icons.chevron_right),
            onTap: onTap,
          ),
        ),
      );
}
