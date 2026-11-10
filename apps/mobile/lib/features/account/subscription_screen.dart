import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api_client.dart';
import '../../core/auth.dart';
import '../../core/format.dart' as fmt;
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../booking/booking_repository.dart';
import '../booking/bookings_screen.dart' show SignedOutView;
import '../booking/models.dart';

/// Maquette 15 — abonnement. Les crédits n'arrivent qu'après confirmation du paiement par le serveur
/// (webhook signé du prestataire), jamais sur le simple retour de la page de paiement.
class SubscriptionScreen extends ConsumerStatefulWidget {
  const SubscriptionScreen({super.key, this.returnedFrom});
  final String? returnedFrom;

  @override
  ConsumerState<SubscriptionScreen> createState() => _SubscriptionScreenState();
}

class _SubscriptionScreenState extends ConsumerState<SubscriptionScreen> {
  Timer? _poll;
  int _polls = 0;
  bool _busy = false;
  String? _checkoutKey;
  // Valeur affichée dès le toucher de l'interrupteur, avant la réponse du serveur.
  bool? _autoRenew;

  bool get _waitingPayment => widget.returnedFrom == 'paiement' && _poll != null;

  @override
  void initState() {
    super.initState();
    if (widget.returnedFrom == 'paiement') {
      // Retour du paiement : on interroge le serveur jusqu'à confirmation (2 min maximum).
      _poll = Timer.periodic(const Duration(seconds: 3), (_) {
        _polls++;
        ref.invalidate(subscriptionProvider);
        if (_polls >= 40) _stopPolling();
      });
    }
  }

  void _stopPolling() {
    _poll?.cancel();
    if (mounted) setState(() => _poll = null);
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (ref.watch(authProvider).valueOrNull == null) {
      return const Scaffold(
          body: SafeArea(child: SignedOutView(message: 'Connectez-vous pour gérer votre abonnement.')));
    }
    ref.listen(subscriptionProvider, (_, next) {
      if (next.valueOrNull?.isActive == true && _poll != null) {
        _stopPolling();
        invalidateBookingData(ref);
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Paiement confirmé : vos crédits ont été ajoutés.')));
      }
    });
    final sub = ref.watch(subscriptionProvider);
    return Scaffold(
      body: SafeArea(
        child: sub.when(
          skipLoadingOnRefresh: true,
          loading: () => const LoadingView(),
          error: (e, _) => ErrorView(error: e, onRetry: () => ref.invalidate(subscriptionProvider)),
          data: (s) => ListView(padding: const EdgeInsets.fromLTRB(20, 8, 20, 32), children: [
            Row(children: [
              IconButton(
                tooltip: 'Retour',
                onPressed: () => context.canPop() ? context.pop() : context.go('/profil'),
                icon: const Icon(Icons.arrow_back),
              ),
              const XpassLogo(height: 26),
            ]),
            const SizedBox(height: 12),
            const Text('MON ABONNEMENT', style: TextStyle(letterSpacing: 3, fontSize: 12, color: XColors.lavenderText)),
            Text('Mon abonnement', style: serif(38)),
            const SizedBox(height: 6),
            const Text('Votre formule, vos crédits et vos prélèvements au même endroit.',
                style: TextStyle(fontSize: 16, color: XColors.navyMuted)),
            const SizedBox(height: 16),
            if (s.sandbox) const _SandboxBanner(),
            if (_waitingPayment && !s.isActive) const _PendingPayment(),
            if (widget.returnedFrom == 'annule' && !s.isActive)
              const Padding(
                padding: EdgeInsets.only(bottom: 12),
                child:
                    Text('Paiement annulé : aucun montant n’a été débité.', style: TextStyle(color: XColors.navyMuted)),
              ),
            if (s.isActive) ..._active(s) else _Offer(info: s, busy: _busy, onSubscribe: _subscribe),
            const SizedBox(height: 18),
            _Invoices(info: s),
          ]),
        ),
      ),
    );
  }

  List<Widget> _active(SubscriptionInfo s) {
    final plan = s.plan!;
    final end = s.currentPeriodEnd;
    return [
      SizedBox(width: double.infinity, child: _PlanCard(plan: plan, active: true)),
      const SizedBox(height: 12),
      if (end != null)
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: XColors.lavender, borderRadius: BorderRadius.circular(XRadius.card)),
          child: Row(children: [
            const CircleAvatar(radius: 26, backgroundColor: Colors.white, child: Icon(XIcons.credits)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(s.cancelAtPeriodEnd ? 'Fin de l’abonnement' : 'Prochain renouvellement',
                    style: const TextStyle(color: XColors.navyMuted)),
                Text('${fmt.dayMonth(end)} ${end.year}', style: serif(24)),
                if (!s.cancelAtPeriodEnd)
                  Text('${fmt.credits(plan.creditsPerPeriod)} ajoutés après paiement confirmé.',
                      style: const TextStyle(fontSize: 13, color: XColors.navyMuted)),
              ]),
            ),
          ]),
        ),
      const SizedBox(height: 12),
      Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(XRadius.card),
          border: Border.all(color: XColors.line),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('Renouvellement automatique', style: serif(22))),
            Switch(
              value: _autoRenew ?? !s.cancelAtPeriodEnd,
              activeColor: Colors.white,
              activeTrackColor: XColors.coral,
              onChanged: (v) => _setAutoRenew(v),
            ),
          ]),
          Text(
            s.cancelAtPeriodEnd && end != null
                ? 'Votre abonnement reste actif jusqu’au ${fmt.dayMonth(end)} ${end.year}, puis prendra fin.'
                : 'Votre abonnement se renouvelle chaque mois. Si vous le désactivez, il reste actif jusqu’à la fin de la période en cours.',
            style: const TextStyle(color: XColors.navyMuted),
          ),
        ]),
      ),
      const SizedBox(height: 12),
      _Rollover(info: s),
      const SizedBox(height: 12),
      _ChangePlan(info: s, busy: _busy, onChoose: _subscribe, onKeep: _changePlan),
    ];
  }

  Future<void> _changePlan(Plan plan) async {
    setState(() => _busy = true);
    try {
      await ref.read(bookingRepositoryProvider).changePlan(plan.code);
      ref.invalidate(subscriptionProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(plan.code == ref.read(subscriptionProvider).valueOrNull?.plan?.code
              ? 'Vous gardez votre formule actuelle.'
              : 'Formule ${plan.name} programmée pour le prochain renouvellement.'),
        ));
      }
    } on ApiException catch (e) {
      if (e.code == 'needs_checkout' || e.statusCode == 502) {
        if (mounted) setState(() => _busy = false);
        await _subscribe(plan);
        return;
      }
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _subscribe(Plan plan) async {
    setState(() => _busy = true);
    _checkoutKey ??= newIdempotencyKey();
    try {
      final url = await ref.read(bookingRepositoryProvider).checkout(plan.code, _checkoutKey!);
      _checkoutKey = null;
      // Paiement sur la page hébergée du prestataire ; le retour ramène sur cet écran.
      final opened = await launchUrl(Uri.parse(url), webOnlyWindowName: '_self');
      if (!opened && mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Impossible d’ouvrir la page de paiement.')));
      }
    } on ApiException catch (e) {
      if (!e.isNetwork) _checkoutKey = null;
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _setAutoRenew(bool enabled) async {
    setState(() => _autoRenew = enabled);
    try {
      await ref.read(bookingRepositoryProvider).setAutoRenew(enabled);
      ref.invalidate(subscriptionProvider);
      await ref.read(subscriptionProvider.future);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      // La valeur du serveur reprend la main (identique si tout s'est bien passé, rétablie sinon).
      if (mounted) setState(() => _autoRenew = null);
    }
  }
}

class _SandboxBanner extends StatelessWidget {
  const _SandboxBanner();

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: const Color(0xFFFFE7E2), borderRadius: BorderRadius.circular(14)),
        child: const Row(children: [
          Icon(Icons.science_outlined),
          SizedBox(width: 10),
          Expanded(child: Text('Paiements en bac à sable : aucun argent réel n’est débité.')),
        ]),
      );
}

class _PendingPayment extends StatelessWidget {
  const _PendingPayment();

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: XColors.lavender, borderRadius: BorderRadius.circular(14)),
        child: const Row(children: [
          SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5)),
          SizedBox(width: 12),
          Expanded(
            child: Text('Paiement en cours de confirmation. Vos crédits apparaîtront dès sa validation.',
                semanticsLabel: 'Paiement en cours de confirmation'),
          ),
        ]),
      );
}

class _PlanCard extends StatelessWidget {
  const _PlanCard({required this.plan, required this.active});
  final Plan plan;
  final bool active;

  @override
  Widget build(BuildContext context) => Container(
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(XRadius.card),
          border: Border.all(color: XColors.line),
        ),
        child: Stack(children: [
          const PositionedDirectional(
            top: 0,
            bottom: 0,
            end: 0,
            width: 170,
            child: FadedPhoto(imageKey: 'demo/screens/subscription.jpg', fadeStop: 0.3),
          ),
          Padding(
            padding: const EdgeInsetsDirectional.fromSTEB(18, 18, 120, 18),
            child: _planDetails(),
          ),
        ]),
      );

  Widget _planDetails() => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 10, crossAxisAlignment: WrapCrossAlignment.center, children: [
          Text(plan.name, style: serif(26)),
          if (active)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(color: XColors.mint, borderRadius: BorderRadius.circular(20)),
              child: const Text('Actif', style: TextStyle(fontWeight: FontWeight.w600)),
            ),
        ]),
        const SizedBox(height: 8),
        Text('${fmt.money(plan.priceMinor, plan.currency)} / mois', style: serif(30)),
        Text('${fmt.credits(plan.creditsPerPeriod)} par mois', style: const TextStyle(color: XColors.navyMuted)),
        if (plan.isDemo) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: XColors.lavender, borderRadius: BorderRadius.circular(10)),
            child: const Text('Formule illustrative', style: TextStyle(fontSize: 13)),
          ),
        ],
      ]);
}

class _Offer extends ConsumerWidget {
  const _Offer({required this.info, required this.busy, required this.onSubscribe});
  final SubscriptionInfo info;
  final bool busy;
  final void Function(Plan) onSubscribe;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (!info.paymentsEnabled) {
      return const EmptyView(message: 'Le paiement n’est pas encore disponible sur cette plateforme.');
    }
    final plans = ref.watch(plansProvider);
    return plans.when(
      loading: () => const SizedBox(height: 120, child: LoadingView()),
      error: (e, _) => ErrorView(error: e, onRetry: () => ref.invalidate(plansProvider)),
      data: (list) => Column(children: [
        for (final p in list) ...[
          SizedBox(width: double.infinity, child: _PlanCard(plan: p, active: false)),
          const SizedBox(height: 12),
          CoralButton(
            label: busy ? 'Ouverture du paiement…' : 'S’abonner · ${fmt.money(p.priceMinor, p.currency)} / mois',
            onPressed: busy ? null : () => onSubscribe(p),
          ),
          const SizedBox(height: 6),
          const Text('Paiement sécurisé sur la page du prestataire. Résiliable à tout moment.',
              textAlign: TextAlign.center, style: TextStyle(fontSize: 12, color: XColors.navyMuted)),
        ],
      ]),
    );
  }
}

/// Report des crédits non utilisés : jusqu'à un mois de formule, tant que l'abonnement est actif.
class _Rollover extends StatelessWidget {
  const _Rollover({required this.info});
  final SubscriptionInfo info;

  @override
  Widget build(BuildContext context) {
    final cap = info.rolloverCap ?? info.plan?.creditsPerPeriod ?? 0;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: XColors.mint, borderRadius: BorderRadius.circular(XRadius.card)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Crédits non utilisés', style: serif(22)),
        const SizedBox(height: 6),
        Text('${fmt.credits(info.subscriptionCredits)} d’abonnement disponibles.',
            style: const TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 4),
        Text(
          'À chaque renouvellement, jusqu’à ${fmt.credits(cap)} sont reportés au mois suivant ; au-delà, '
          'les plus anciens expirent. À l’arrêt de l’abonnement, les crédits d’abonnement non utilisés expirent. '
          'Les crédits offerts par votre employeur ne sont pas concernés.',
          style: const TextStyle(color: XColors.navyMuted, fontSize: 13),
        ),
      ]),
    );
  }
}

/// Changement de formule : appliqué au prochain renouvellement, sans prorata.
class _ChangePlan extends ConsumerWidget {
  const _ChangePlan({required this.info, required this.busy, required this.onChoose, required this.onKeep});
  final SubscriptionInfo info;
  final bool busy;
  final void Function(Plan) onChoose;
  final void Function(Plan) onKeep;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final plans = ref.watch(plansProvider).valueOrNull ?? const <Plan>[];
    final current = info.plan;
    final pending = info.pendingPlan;
    final others = plans.where((p) => p.code != current?.code && p.code != pending?.code).toList();
    if (others.isEmpty && pending == null) return const SizedBox.shrink();
    final end = info.currentPeriodEnd;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(XRadius.card),
        border: Border.all(color: XColors.line),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Changer de formule', style: serif(22)),
        const SizedBox(height: 4),
        const Text('Paiement immédiat de la nouvelle formule. Vos crédits arrivent dès confirmation.',
            style: TextStyle(color: XColors.navyMuted, fontSize: 13)),
        if (pending != null) ...[
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: XColors.lavender, borderRadius: BorderRadius.circular(14)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(
                'Formule ${pending.name} (${fmt.credits(pending.creditsPerPeriod)}, '
                '${fmt.money(pending.priceMinor, pending.currency)} / mois)'
                '${end != null ? ' à partir du ${fmt.dayMonth(end)} ${end.year}' : ''}.',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              if (current != null)
                TextButton(
                  onPressed: busy ? null : () => onKeep(current),
                  child: Text('Garder ${current.name}'),
                ),
            ]),
          ),
        ],
        for (final p in others)
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(p.name, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                  Text('${fmt.credits(p.creditsPerPeriod)} · ${fmt.money(p.priceMinor, p.currency)} / mois',
                      style: const TextStyle(color: XColors.navyMuted)),
                ]),
              ),
              OutlinedButton(onPressed: busy ? null : () => onChoose(p), child: const Text('Choisir')),
            ]),
          ),
      ]),
    );
  }
}

class _Invoices extends StatelessWidget {
  const _Invoices({required this.info});
  final SubscriptionInfo info;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(XRadius.card),
          border: Border.all(color: XColors.line),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Mes derniers prélèvements', style: serif(22)),
          const SizedBox(height: 8),
          if (info.invoices.isEmpty)
            const Text('Aucun prélèvement pour le moment.', style: TextStyle(color: XColors.navyMuted))
          else
            for (final i in info.invoices)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Row(children: [
                  Expanded(child: Text('${fmt.dayMonth(i.paidAt)} ${i.paidAt.year}')),
                  Expanded(child: Text(i.livemode ? i.planName : '${i.planName} (test)')),
                  Text(fmt.money(i.amountMinor, i.currency), style: const TextStyle(fontWeight: FontWeight.w700)),
                ]),
              ),
        ]),
      );
}
