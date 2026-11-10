import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/format.dart' as fmt;
import '../../core/theme.dart';
import '../../core/widgets.dart';
import 'booking_repository.dart';
import 'dispute_sheet.dart';
import 'models.dart';
import '../engagement/engagement.dart';
import '../../core/l10n.dart';

/// Maquette 13 — reçu après consommation validée par le partenaire, et lien d'avis neutre.
class ReceiptScreen extends ConsumerWidget {
  const ReceiptScreen({super.key, required this.bookingId});
  final String bookingId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final receipt = ref.watch(receiptProvider(bookingId));
    return Scaffold(
      body: receipt.when(
        loading: () => const LoadingView(),
        error: (e, _) =>
            SafeArea(child: ErrorView(error: e, onRetry: () => ref.invalidate(receiptProvider(bookingId)))),
        data: (r) => ListView(padding: const EdgeInsets.fromLTRB(20, 0, 20, 32), children: [
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
            imageKey: 'demo/screens/receipt.jpg',
            widthFactor: 0.42,
            height: 210,
            top: -60,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const SizedBox(height: 12),
              SizedBox(
                width: MediaQuery.sizeOf(context).width * 0.62,
                child: Text(context.l10n.serviceDoneTitle, style: serif(36)),
              ),
              const SizedBox(height: 6),
              SizedBox(
                width: MediaQuery.sizeOf(context).width * 0.58,
                child: Text(context.l10n.thanksBenefit, style: const TextStyle(fontSize: 16, color: XColors.navyMuted)),
              ),
            ]),
          ),
          const SizedBox(height: 18),
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(XRadius.card),
              border: Border.all(color: XColors.line),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                const CircleAvatar(
                  radius: 30,
                  backgroundColor: XColors.mint,
                  child: Icon(Icons.check, size: 32, color: Color(0xFF2F7A45)),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(context.l10n.serviceDone, style: serif(26)),
                    Text(context.l10n.validatedByPartner, style: const TextStyle(color: XColors.navyMuted)),
                  ]),
                ),
              ]),
              const SizedBox(height: 16),
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(14),
                  child: SizedBox(width: 110, height: 90, child: MediaImage(imageKey: r.coverImageKey)),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${r.locationName} · ${r.offerTitle}', style: serif(20)),
                    const SizedBox(height: 4),
                    Text(
                        '${fmt.dayMonth(r.localRedeemedAt)} ${r.localRedeemedAt.year} à ${fmt.hhmm(r.localRedeemedAt)}',
                        style: const TextStyle(color: XColors.navyMuted)),
                    Text('${r.cityName}, France', style: const TextStyle(color: XColors.navyMuted)),
                  ]),
                ),
              ]),
              const Divider(height: 32),
              Row(children: [
                Expanded(
                    child: Text(context.l10n.creditsUsed,
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16))),
                Text(fmt.credits(r.creditsTotal), style: serif(26)),
              ]),
              const SizedBox(height: 8),
              for (final Funding f in r.funding)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(children: [
                    Expanded(child: Text(f.label)),
                    Text(fmt.credits(f.credits)),
                  ]),
                ),
              const Divider(height: 32),
              Row(children: [
                Expanded(
                    child: Text(context.l10n.receiptReference, style: const TextStyle(fontWeight: FontWeight.w700))),
                SelectableText(r.reference, style: const TextStyle(fontWeight: FontWeight.w700)),
              ]),
            ]),
          ),
          const SizedBox(height: 18),
          ReviewForm(bookingId: bookingId),
          const SizedBox(height: 18),
          if (r.reviewUrl != null) ...[
            // Lien neutre : aucune récompense, aucune publication à la place du client.
            CoralButton(
              label: context.l10n.reviewOnGoogle,
              icon: Icons.rate_review_outlined,
              onPressed: () => launchUrl(Uri.parse(r.reviewUrl!), mode: LaunchMode.externalApplication),
            ),
            const SizedBox(height: 6),
            Text(context.l10n.reviewFree,
                textAlign: TextAlign.center, style: const TextStyle(fontSize: 12, color: XColors.navyMuted)),
          ] else
            Text(context.l10n.noReviewLink,
                textAlign: TextAlign.center, style: const TextStyle(color: XColors.navyMuted)),
          const SizedBox(height: 12),
          ...?ref.watch(disputesProvider(bookingId)).valueOrNull?.take(1).map((d) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(d.summary, style: const TextStyle(color: XColors.navyMuted)),
              )),
          ListTile(
            leading: const Icon(Icons.help_outline, color: XColors.lavenderText),
            title: Text(context.l10n.askForHelp),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => showDisputeSheet(context, bookingId),
          ),
        ]),
      ),
    );
  }
}
