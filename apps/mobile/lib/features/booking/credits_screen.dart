import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth.dart';
import '../../core/format.dart' as fmt;
import '../../core/theme.dart';
import '../../core/widgets.dart';
import 'booking_repository.dart';
import 'bookings_screen.dart';
import 'models.dart';
import '../../core/l10n.dart';

/// Maquette 14 — Mes crédits : disponibles / réservés, origine, lots prioritaires, historique.
class CreditsScreen extends ConsumerWidget {
  const CreditsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (ref.watch(authProvider).valueOrNull == null) {
      return Scaffold(body: SafeArea(child: SignedOutView(message: context.l10n.signInToSeeCredits)));
    }
    final wallet = ref.watch(walletProvider);
    final history = ref.watch(walletHistoryProvider);
    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          color: XColors.coral,
          onRefresh: () async {
            ref.invalidate(walletProvider);
            ref.invalidate(walletHistoryProvider);
          },
          child: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 32), children: [
            PhotoHeader(
              imageKey: 'demo/screens/credits.jpg',
              widthFactor: 0.5,
              height: 250,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const XpassLogo(height: 28),
                const SizedBox(height: 16),
                Text(context.l10n.myCredits, style: serif(40)),
                const SizedBox(height: 8),
                SizedBox(
                  width: MediaQuery.sizeOf(context).width * 0.6,
                  child: const Text(
                    'Vos crédits vous ouvrent le sport, la culture, la beauté et les sorties — un pass, toutes vos envies.',
                    style: TextStyle(color: XColors.navyMuted, fontSize: 15),
                  ),
                ),
                const SizedBox(height: 20),
              ]),
            ),
            const SizedBox(height: 18),
            wallet.when(
              loading: () => const SizedBox(height: 200, child: LoadingView()),
              error: (e, _) => ErrorView(error: e, onRetry: () => ref.invalidate(walletProvider)),
              data: (w) => w == null ? const SizedBox() : _WalletBody(wallet: w),
            ),
            const SizedBox(height: 18),
            const _CreditRules(),
            const SizedBox(height: 24),
            Text('Historique récent', style: serif(26)),
            const SizedBox(height: 8),
            history.when(
              loading: () => const SizedBox(height: 80, child: LoadingView()),
              error: (e, _) => ErrorView(error: e, onRetry: () => ref.invalidate(walletHistoryProvider)),
              data: (items) => items.isEmpty
                  ? const EmptyView(message: 'Aucun mouvement pour le moment.')
                  : Column(children: [for (final h in items) _HistoryRow(entry: h)]),
            ),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: () => context.push('/abonnement'),
              icon: const Icon(Icons.workspace_premium_outlined),
              label: const Text('Obtenir des crédits avec l’abonnement'),
            ),
            const SizedBox(height: 10),
            CoralButton(
                label: 'Explorer avec mes crédits', icon: Icons.explore, onPressed: () => context.go('/explore')),
          ]),
        ),
      ),
    );
  }
}

class _WalletBody extends StatelessWidget {
  const _WalletBody({required this.wallet});
  final WalletSummary wallet;

  @override
  Widget build(BuildContext context) {
    final w = wallet;
    final personal = (w.bySource['personal']?.$1 ?? 0) + (w.bySource['promotional']?.$1 ?? 0);
    final employer = w.bySource['employer']?.$1 ?? 0;
    final expiring = w.lots.where((l) => l.expiresAt != null && l.available > 0).toList();
    final demo = w.lots.any((l) => l.isDemo);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(color: XColors.lavender, borderRadius: BorderRadius.circular(XRadius.card)),
        child: Row(children: [
          Expanded(child: _Big(icon: XIcons.credits, value: w.available, label: 'crédits disponibles')),
          Container(width: 1, height: 60, color: XColors.lavenderStrong),
          Expanded(child: _Big(icon: Icons.calendar_today_outlined, value: w.reserved, label: 'crédits réservés')),
        ]),
      ),
      if (demo) ...[
        const SizedBox(height: 8),
        const Text('Inclut des crédits de démonstration (offerts ou payés en bac à sable) : aucun argent réel.',
            style: TextStyle(fontSize: 12, color: XColors.navyMuted)),
      ],
      const SizedBox(height: 22),
      Text('Origine de vos crédits', style: serif(26)),
      const SizedBox(height: 12),
      Row(children: [
        Expanded(child: _SourceCard(icon: Icons.person_outline, title: 'Personnel', value: personal, coral: true)),
        const SizedBox(width: 12),
        Expanded(child: _SourceCard(icon: Icons.apartment, title: 'Employeur', value: employer)),
      ]),
      if (expiring.isNotEmpty) ...[
        const SizedBox(height: 22),
        Text('Lots à utiliser en priorité', style: serif(24)),
        const SizedBox(height: 10),
        for (final l in expiring)
          Container(
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(XRadius.card),
              border: Border.all(color: XColors.line),
            ),
            child: Row(children: [
              CircleAvatar(
                radius: 24,
                backgroundColor: l.source == 'employer' ? XColors.lavender : const Color(0xFFFFE7E2),
                child: Icon(Icons.card_giftcard, color: l.source == 'employer' ? XColors.navy : XColors.coral),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${fmt.credits(l.available)} · ${l.label}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  Text('À utiliser avant le ${fmt.shortDate(l.expiresAt!)}',
                      style: const TextStyle(color: XColors.navyMuted)),
                  Text(l.source == 'employer' ? 'Inclus dans le solde employeur' : 'Inclus dans le solde personnel',
                      style: const TextStyle(color: XColors.navyMuted, fontSize: 13)),
                ]),
              ),
            ]),
          ),
      ],
    ]);
  }
}

class _Big extends StatelessWidget {
  const _Big({required this.icon, required this.value, required this.label});
  final IconData icon;
  final int value;
  final String label;

  @override
  Widget build(BuildContext context) => Row(children: [
        CircleAvatar(radius: 24, backgroundColor: Colors.white, child: Icon(icon, color: XColors.navy)),
        const SizedBox(width: 10),
        Flexible(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('$value', style: serif(34)),
            Text(label, style: const TextStyle(color: XColors.navyMuted, fontSize: 13)),
          ]),
        ),
      ]);
}

class _SourceCard extends StatelessWidget {
  const _SourceCard({required this.icon, required this.title, required this.value, this.coral = false});
  final IconData icon;
  final String title;
  final int value;
  final bool coral;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(XRadius.card),
          border: Border.all(color: XColors.line),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          CircleAvatar(
            backgroundColor: coral ? const Color(0xFFFFE7E2) : XColors.lavender,
            child: Icon(icon, color: coral ? XColors.coral : XColors.navy),
          ),
          const SizedBox(height: 8),
          Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
          Text('$value', style: serif(32)),
          const Text('crédits disponibles', style: TextStyle(color: XColors.navyMuted, fontSize: 13)),
        ]),
      );
}

class _HistoryRow extends StatelessWidget {
  const _HistoryRow({required this.entry});
  final HistoryEntry entry;

  @override
  Widget build(BuildContext context) {
    final e = entry;
    final (icon, color, title, amount) = switch (e.kind) {
      'grant' => (Icons.add, XColors.mint, 'Crédits attribués', '+ ${e.availableDelta}'),
      'reserve' => (
          Icons.calendar_today_outlined,
          XColors.lavender,
          'Réservation d’activité',
          '${e.reservedDelta} réservés'
        ),
      'release' => (Icons.undo, XColors.mint, 'Restitution de crédits', '+ ${e.availableDelta}'),
      'capture' => (Icons.check, XColors.lavender, 'Crédits utilisés', '${-e.reservedDelta} débités'),
      'expire' => (Icons.timer_off_outlined, const Color(0xFFFFE7E2), 'Crédits expirés', '${e.availableDelta}'),
      _ => (Icons.tune, XColors.lavender, 'Ajustement', '${e.availableDelta}'),
    };
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(children: [
        CircleAvatar(radius: 20, backgroundColor: color, child: Icon(icon, size: 20, color: XColors.navy)),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
            Text('${fmt.shortDate(e.createdAt)} · ${e.offerTitle ?? e.memo}',
                style: const TextStyle(color: XColors.navyMuted, fontSize: 13),
                maxLines: 1,
                overflow: TextOverflow.ellipsis),
          ]),
        ),
        Text(amount, style: const TextStyle(fontWeight: FontWeight.w700)),
      ]),
    );
  }
}

/// Règles d'utilisation des crédits (prix variable, annulation, report, crédits employeur).
class _CreditRules extends StatelessWidget {
  const _CreditRules();

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: XColors.lavender, borderRadius: BorderRadius.circular(XRadius.card)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(l.creditRulesTitle, style: serif(22)),
        const SizedBox(height: 8),
        for (final rule in [l.creditRulePrice, l.creditRuleCancel, l.creditRuleRollover, l.creditRuleEmployer])
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Padding(padding: EdgeInsets.only(top: 6), child: Icon(Icons.circle, size: 6, color: XColors.navy)),
              const SizedBox(width: 10),
              Expanded(child: Text(rule, style: const TextStyle(fontSize: 14))),
            ]),
          ),
      ]),
    );
  }
}
