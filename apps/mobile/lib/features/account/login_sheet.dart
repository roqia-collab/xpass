import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/auth.dart';
import '../../core/config.dart';
import '../../core/oidc.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../core/l10n.dart';

/// Langue choisie avant connexion (transmise à la page du fournisseur d'identité ; textes de l'app : lot 8b).
final preferredLocaleProvider = StateProvider<String>((ref) => 'fr');

/// Garantit une session avant une action protégée. Retourne vrai si connecté.
Future<bool> ensureSignedIn(BuildContext context, WidgetRef ref) async {
  if (ref.read(authProvider).valueOrNull != null) return true;
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: XColors.cream,
    builder: (_) => const SafeArea(
      child: SingleChildScrollView(padding: EdgeInsets.all(24), child: SignInPanel(closeOnSuccess: true)),
    ),
  );
  return ref.read(authProvider).valueOrNull != null;
}

/// Maquette 02 — connexion et inscription. Le mot de passe est saisi sur la page sécurisée du fournisseur
/// d'identité, jamais dans l'application.
class SignInScreen extends StatelessWidget {
  const SignInScreen({super.key, this.onExplore});
  final VoidCallback? onExplore;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    // Le texte garde sa colonne à gauche ; la photo occupe la droite et se fond dans le fond crème.
    final textWidth = (width * (width < 420 ? 0.66 : 0.58)).clamp(200.0, 440.0);
    return ListView(padding: EdgeInsets.zero, children: [
      // Hauteur minimale de 360 px, extensible : les grands textes (réglage d'accessibilité) ne débordent pas.
      Stack(children: [
        PositionedDirectional(
          top: 0,
          bottom: 0,
          end: 0,
          width: (width * 0.62).clamp(220.0, 520.0),
          child: const FadedPhoto(imageKey: 'demo/screens/login.jpg', fadeStop: 0.45),
        ),
        const Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0x00F3F4F7), Color(0x00F3F4F7), Color(0xFFF3F4F7)],
                stops: [0, 0.8, 1],
              ),
            ),
          ),
        ),
        ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 360),
          child: SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsetsDirectional.fromSTEB(20, 12, 20, 24),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Row(children: [XpassLogo(height: 28), Spacer(), _LanguagePicker()]),
                const SizedBox(height: 72),
                SizedBox(
                  width: textWidth,
                  child: Text(context.l10n.welcomeTitle, style: serif(width < 420 ? 30 : 36, height: 1.05)),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: textWidth,
                  child: Text(context.l10n.welcomeSubtitle,
                      style: const TextStyle(fontSize: 16, color: XColors.navyMuted, height: 1.35)),
                ),
              ]),
            ),
          ),
        ),
      ]),
      Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
            child: SignInPanel(onExplore: onExplore, showTitle: false),
          ),
        ),
      ),
    ]);
  }
}

class SignInPanel extends ConsumerStatefulWidget {
  const SignInPanel({super.key, this.closeOnSuccess = false, this.onExplore, this.showTitle = true});
  final bool closeOnSuccess;
  final VoidCallback? onExplore;
  final bool showTitle;

  @override
  ConsumerState<SignInPanel> createState() => _SignInPanelState();
}

class _SignInPanelState extends ConsumerState<SignInPanel> {
  final _email = TextEditingController(text: 'client@xpass.demo');
  bool _showDemo = !OidcClient.configured;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  Future<void> _oidc({required bool register, String identity = 'google'}) async {
    setState(() => _error = null);
    try {
      await ref.read(authProvider.notifier).signIn(
          register: register, locale: ref.read(preferredLocaleProvider), identity: identity);
      if (mounted && widget.closeOnSuccess && ref.read(authProvider).valueOrNull != null) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _demo() async {
    await ref.read(authProvider.notifier).devLogin(_email.text.trim());
    if (!mounted) return;
    if (ref.read(authProvider).valueOrNull != null && widget.closeOnSuccess) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    final busy = auth.isLoading;
    final error = _error ?? (auth.hasError ? auth.error.toString() : null);
    return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      if (widget.showTitle) ...[
        Text(context.l10n.signIn, style: serif(32)),
        const SizedBox(height: 8),
        Text(context.l10n.signInHint, style: const TextStyle(color: XColors.navyMuted)),
        const SizedBox(height: 20),
      ],
      if (OidcClient.configured) ...[
        CoralButton(label: context.l10n.signIn, onPressed: busy ? null : () => _oidc(register: false)),
        const SizedBox(height: 12),
        OutlinedButton(
          style: OutlinedButton.styleFrom(
            foregroundColor: XColors.navy,
            minimumSize: const Size.fromHeight(56),
            side: const BorderSide(color: XColors.navy, width: 1.5),
            shape: const StadiumBorder(),
            textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
          ),
          onPressed: busy ? null : () => _oidc(register: false, identity: 'email'),
          child: Text(context.l10n.signInEmail),
        ),
        const SizedBox(height: 12),
        Row(children: [
          const Expanded(child: Divider()),
          Padding(padding: const EdgeInsets.symmetric(horizontal: 12), child: Text(context.l10n.or)),
          const Expanded(child: Divider()),
        ]),
        const SizedBox(height: 12),
        OutlinedButton(
          style: OutlinedButton.styleFrom(
            foregroundColor: XColors.navy,
            minimumSize: const Size.fromHeight(56),
            side: const BorderSide(color: XColors.navy, width: 1.5),
            shape: const StadiumBorder(),
            textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
          ),
          onPressed: busy ? null : () => _oidc(register: true, identity: 'email'),
          child: Text(context.l10n.createAccountEmail),
        ),
        const SizedBox(height: 8),
        Text(
          context.l10n.passwordNotice,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 12, color: XColors.navyMuted),
        ),
      ],
      if (widget.onExplore != null)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: TextButton(
            style: TextButton.styleFrom(foregroundColor: XColors.navy),
            onPressed: widget.onExplore,
            child: Text(context.l10n.exploreWithoutAccount,
                style: const TextStyle(fontSize: 16, decoration: TextDecoration.underline)),
          ),
        ),
      if (error != null) ...[
        const SizedBox(height: 8),
        Text(error, style: const TextStyle(color: Color(0xFFB42318))),
      ],
      if (AppConfig.devLoginEnabled) ...[
        const SizedBox(height: 8),
        if (!_showDemo)
          TextButton(
            style: TextButton.styleFrom(foregroundColor: XColors.navyMuted),
            onPressed: () => setState(() => _showDemo = true),
            child: Text(context.l10n.demoMode),
          )
        else
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: XColors.lavender, borderRadius: BorderRadius.circular(16)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const Text(
                  'Mode démonstration : connexion sans mot de passe réservée aux comptes de test, '
                  'désactivée en production.',
                  style: TextStyle(fontSize: 13)),
              const SizedBox(height: 10),
              TextField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                decoration: InputDecoration(
                  labelText: 'Adresse e-mail de démonstration',
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                ),
                onSubmitted: (_) => _demo(),
              ),
              const SizedBox(height: 10),
              FilledButton(
                  onPressed: busy ? null : _demo, child: Text(busy ? 'Connexion…' : 'Connexion de démonstration')),
            ]),
          ),
      ],
      const SizedBox(height: 12),
      const _LegalNotice(),
    ]);
  }
}

class _LegalNotice extends StatelessWidget {
  const _LegalNotice();

  @override
  Widget build(BuildContext context) {
    const style = TextStyle(fontSize: 12, color: XColors.navyMuted);
    if (AppConfig.termsUrl.isEmpty || AppConfig.privacyUrl.isEmpty) {
      return Text(context.l10n.legalPending, textAlign: TextAlign.center, style: style);
    }
    return Wrap(alignment: WrapAlignment.center, children: [
      const Text('En continuant, vous acceptez nos ', style: style),
      InkWell(
        onTap: () => launchUrl(Uri.parse(AppConfig.termsUrl)),
        child: const Text('Conditions générales d’utilisation',
            style: TextStyle(fontSize: 12, decoration: TextDecoration.underline)),
      ),
      const Text(' et notre ', style: style),
      InkWell(
        onTap: () => launchUrl(Uri.parse(AppConfig.privacyUrl)),
        child: const Text('Politique de confidentialité',
            style: TextStyle(fontSize: 12, decoration: TextDecoration.underline)),
      ),
      const Text('.', style: style),
    ]);
  }
}

class _LanguagePicker extends ConsumerWidget {
  const _LanguagePicker();

  static const _labels = {'fr': 'FR', 'en': 'EN', 'ar': 'AR'};

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final value = ref.watch(preferredLocaleProvider);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: XColors.line),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10),
        child: DropdownButton<String>(
          value: value,
          underline: const SizedBox(),
          items: [for (final e in _labels.entries) DropdownMenuItem(value: e.key, child: Text(e.value))],
          onChanged: (v) => ref.read(preferredLocaleProvider.notifier).state = v ?? 'fr',
        ),
      ),
    );
  }
}
