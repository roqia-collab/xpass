import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/api_client.dart';
import '../../core/auth.dart';
import '../../core/config.dart';
import '../../core/format.dart' as fmt;
import '../../core/theme.dart';
import '../../core/widgets.dart';
import 'account_repository.dart';
import 'employer_invitations.dart';
import 'login_sheet.dart';
import 'notifications_screen.dart';
import '../../core/l10n.dart';

const _languages = {'fr': 'Français', 'en': 'English', 'ar': 'العربية'};

/// Maquette 16 — paramètres : espace perso, préférences, assistance et confidentialité. Non connecté : écran 02.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(authProvider);
    return Scaffold(
      body: session.when(
        loading: () => const LoadingView(),
        error: (e, _) => SignInScreen(onExplore: () => context.go('/explore')),
        data: (s) => s == null ? SignInScreen(onExplore: () => context.go('/explore')) : _Profile(session: s),
      ),
    );
  }
}

/// Ancien écran dédié : le contenu est désormais dans l’onglet Paramètres.
class SettingsScreen extends ProfileScreen {
  const SettingsScreen({super.key});
}

const _appVersion = String.fromEnvironment('APP_VERSION', defaultValue: '0.1.0');

class _Profile extends ConsumerWidget {
  const _Profile({required this.session});
  final AuthSession session;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = session;
    final l = context.l10n;
    final initials = s.displayName.trim().split(RegExp(r'\s+')).take(2).map((w) => w.isEmpty ? '' : w[0]).join();
    return SafeArea(
      child: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 32), children: [
        PhotoHeader(
          imageKey: 'demo/screens/profile.jpg',
          widthFactor: 0.62,
          height: 170,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const XpassLogo(height: 28),
            const SizedBox(height: 8),
            Text(l.settings, style: serif(40)),
            SizedBox(
              width: MediaQuery.sizeOf(context).width * 0.62,
              child: Text(l.settingsSubtitle, style: const TextStyle(fontSize: 16, color: XColors.navyMuted)),
            ),
          ]),
        ),
        const SizedBox(height: 16),
        FadeSlideIn(
          child: _IdentityCard(
            initials: initials.toUpperCase(),
            name: s.displayName,
            email: s.email,
            verified: s.emailVerified,
            verifiedLabel: s.emailVerified ? l.emailVerified : l.emailNotVerified,
            onEdit: () => _editName(context, ref, s),
          ),
        ),
        const EmployerInvitations(),
        _Section(index: 1, title: l.mySpace, children: [
          _Row(icon: LucideIcons.calendar, label: l.myBookings, onTap: () => context.go('/reservations')),
          _Row(icon: LucideIcons.database, label: l.myCredits, onTap: () => context.go('/credits')),
          _Row(icon: LucideIcons.crown, label: l.mySubscription, onTap: () => context.push('/abonnement')),
          _Row(icon: LucideIcons.heart, label: l.myFavorites, onTap: () => context.push('/profil/favoris')),
          _Row(icon: LucideIcons.bell, label: l.notifications, onTap: () => context.push('/profil/notifications')),
        ]),
        _Section(index: 2, title: l.help, children: [
          _Row(icon: LucideIcons.bookOpen, label: l.helpCenter, onTap: () => _helpCenter(context)),
          _Row(icon: LucideIcons.messageCircle, label: l.contactSupport, onTap: () => showSupportForm(context, ref)),
          _Row(icon: LucideIcons.fileText, label: l.myRequests, onTap: () => _myRequests(context)),
        ]),
        _Section(index: 3, title: l.account, children: [
          _Row(
              icon: LucideIcons.idCard,
              label: l.personalInfo,
              value: s.displayName,
              onTap: () => _editName(context, ref, s)),
          _Row(icon: LucideIcons.mail, label: l.emailAddress, value: s.email),
          _Row(
            icon: LucideIcons.lock,
            label: l.passwordSecurity,
            value: s.isOidc ? null : l.demoMode,
            // Mot de passe, e-mail et sessions : sur la page sécurisée du compte XPASS (jamais dans l'app).
            onTap: s.isOidc && AppConfig.oidcIssuer.isNotEmpty
                ? () => launchUrl(Uri.parse('${AppConfig.oidcIssuer}/account'), mode: LaunchMode.externalApplication)
                : null,
          ),
        ]),
        _Section(index: 4, title: l.preferences, children: [
          _Row(
            icon: LucideIcons.languages,
            label: l.language,
            value: _languages[s.locale],
            onTap: () => _pickLanguage(context, ref, s),
          ),
          _Row(icon: LucideIcons.mapPin, label: l.country, value: l.france),
        ]),
        _Section(index: 5, title: l.notifications, children: [
          _SwitchRow(
            icon: LucideIcons.bell,
            label: l.bookingEmails,
            hint: l.bookingEmailsHint,
            value: s.notifyEmail,
            onChanged: (v) => _save(
                context,
                ref,
                () => ref.read(accountRepositoryProvider).updateProfile(notifyEmail: v),
                () => ref.read(authProvider.notifier).applyProfile(notifyEmail: v),
                revert: () => ref.read(authProvider.notifier).applyProfile(notifyEmail: !v)),
          ),
          const _PushSwitch(),
        ]),
        _Section(index: 6, title: l.privacy, children: [
          _Row(icon: LucideIcons.mapPin, label: l.locationPermission, value: l.optional),
          _Row(icon: LucideIcons.camera, label: l.cameraPermission, value: l.optional),
          _Row(icon: LucideIcons.download, label: l.exportData, onTap: () => _export(context, ref)),
          _Row(
            icon: LucideIcons.scale,
            label: l.legalDocs,
            value: AppConfig.termsUrl.isEmpty ? l.inDrafting : null,
            onTap: AppConfig.termsUrl.isEmpty ? null : () => launchUrl(Uri.parse(AppConfig.termsUrl)),
          ),
        ]),
        FadeSlideIn(
          index: 7,
          child: Container(
            margin: const EdgeInsets.only(bottom: 18),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: XColors.lavender, borderRadius: BorderRadius.circular(18)),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Icon(LucideIcons.shieldCheck, size: 18, color: XColors.lavenderText),
              const SizedBox(width: 10),
              Expanded(child: Text(l.permissionsNotice, style: const TextStyle(fontSize: 13, height: 1.4))),
            ]),
          ),
        ),
        _Section(index: 8, title: l.about, children: [
          _Row(icon: LucideIcons.info, label: l.appVersion, value: _appVersion),
          _Row(icon: LucideIcons.heart, label: l.madeByAlystra),
          _Row(icon: LucideIcons.globe, label: l.translationNotice.split('.').first),
        ]),
        _Section(index: 9, title: l.dangerZone, children: [
          _Row(icon: LucideIcons.trash2, label: l.deleteAccount, danger: true, onTap: () => _delete(context, ref)),
        ]),
        OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              foregroundColor: XColors.navy,
              minimumSize: const Size.fromHeight(54),
              side: const BorderSide(color: XColors.line, width: 1.5),
              shape: const StadiumBorder(),
              textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            ),
            onPressed: () async {
              await ref.read(authProvider.notifier).logout();
              if (context.mounted) context.go('/profil');
            },
            icon: const Icon(LucideIcons.logOut, size: 20),
            label: Text(l.signOut),
          ),
      ]),
    );
  }

  /// Réponse immédiate : la valeur s'affiche tout de suite ; elle est rétablie si le serveur refuse.
  Future<void> _save(BuildContext context, WidgetRef ref, Future<void> Function() call, VoidCallback apply,
      {VoidCallback? revert}) async {
    if (revert != null) apply();
    try {
      await call();
      if (revert == null) apply();
    } on ApiException catch (e) {
      revert?.call();
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _editName(BuildContext context, WidgetRef ref, AuthSession s) async {
    final controller = TextEditingController(text: s.displayName);
    final name = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Informations personnelles'),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          TextField(
              controller: controller, maxLength: 120, decoration: const InputDecoration(labelText: 'Nom affiché')),
          Text('E-mail : ${s.email}', style: const TextStyle(color: XColors.navyMuted)),
          if (s.isOidc)
            const Text('L’adresse e-mail et le mot de passe se modifient sur votre compte XPASS sécurisé.',
                style: TextStyle(fontSize: 12, color: XColors.navyMuted)),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: const Text('Annuler')),
          FilledButton(
            style: FilledButton.styleFrom(minimumSize: const Size(0, 44)),
            onPressed: () => Navigator.pop(c, controller.text.trim()),
            child: const Text('Enregistrer'),
          ),
        ],
      ),
    );
    if (name == null || name.isEmpty || !context.mounted) return;
    await _save(context, ref, () => ref.read(accountRepositoryProvider).updateProfile(displayName: name),
        () => ref.read(authProvider.notifier).applyProfile(displayName: name));
  }

  Future<void> _pickLanguage(BuildContext context, WidgetRef ref, AuthSession s) async {
    final locale = await showModalBottomSheet<String>(
      context: context,
      builder: (c) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          for (final e in _languages.entries)
            ListTile(
              title: Text(e.value),
              trailing: e.key == s.locale ? const Icon(Icons.check) : null,
              onTap: () => Navigator.pop(c, e.key),
            ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Text(c.l10n.translationNotice, style: const TextStyle(fontSize: 12, color: XColors.navyMuted)),
          ),
        ]),
      ),
    );
    if (locale == null || !context.mounted) return;
    ref.read(preferredLocaleProvider.notifier).state = locale;
    await _save(context, ref, () => ref.read(accountRepositoryProvider).updateProfile(locale: locale),
        () => ref.read(authProvider.notifier).applyProfile(locale: locale));
  }

  void _helpCenter(BuildContext context) => showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: XColors.cream,
        builder: (_) => DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.8,
          builder: (_, controller) => ListView(controller: controller, padding: const EdgeInsets.all(20), children: [
            Text('Centre d’aide', style: serif(28)),
            for (final (q, a) in _faq)
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: Text(q, style: const TextStyle(fontWeight: FontWeight.w600)),
                children: [Align(alignment: Alignment.centerLeft, child: Text(a))],
              ),
          ]),
        ),
      );

  void _myRequests(BuildContext context) => showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: XColors.cream,
        builder: (_) => const FractionallySizedBox(heightFactor: 0.8, child: MyRequests()),
      );

  Future<void> _export(BuildContext context, WidgetRef ref) async {
    try {
      final json = await ref.read(accountRepositoryProvider).exportData();
      await Share.shareXFiles(
          [XFile.fromData(utf8.encode(json), mimeType: 'application/json', name: 'mes-donnees-xpass.json')],
          fileNameOverrides: ['mes-donnees-xpass.json']);
    } on ApiException catch (e) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _delete(BuildContext context, WidgetRef ref) async {
    final controller = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Supprimer mon compte'),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Vos informations personnelles seront effacées et vos crédits restants perdus. '
              'Les traces comptables des réservations passées sont conservées sans votre identité.'),
          const SizedBox(height: 12),
          TextField(
              controller: controller, decoration: const InputDecoration(labelText: 'Tapez SUPPRIMER pour confirmer')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Annuler')),
          FilledButton(
            style: FilledButton.styleFrom(minimumSize: const Size(0, 44), backgroundColor: const Color(0xFFB42318)),
            onPressed: () => Navigator.pop(c, controller.text.trim() == 'SUPPRIMER'),
            child: const Text('Supprimer'),
          ),
        ],
      ),
    );
    if (ok != true || !context.mounted) return;
    try {
      await ref.read(accountRepositoryProvider).deleteAccount();
      await ref.read(authProvider.notifier).logout();
    } on ApiException catch (e) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }
}

const _faq = [
  (
    'Comment fonctionnent les crédits ?',
    'Chaque prestation a un prix en crédits. Vos crédits viennent de votre abonnement, de votre employeur ou '
        'd’offres promotionnelles ; les crédits qui expirent le plus tôt sont utilisés en premier.'
  ),
  (
    'Quand mes crédits sont-ils débités ?',
    'À la réservation, les crédits sont réservés. Ils ne sont consommés qu’au scan de votre QR par le partenaire.'
  ),
  (
    'Puis-je annuler ?',
    'Oui, gratuitement jusqu’à la limite affichée sur la réservation. Après, les crédits sont débités.'
  ),
  (
    'Mon QR ne fonctionne pas',
    'Le QR se renouvelle toutes les minutes : gardez l’écran ouvert. Le partenaire peut aussi saisir le code affiché '
        'sous le QR.'
  ),
  (
    'Un problème avec une prestation ?',
    'Depuis le reçu, touchez « Demander de l’aide » : l’équipe XPASS examine chaque réclamation et peut vous restituer '
        'vos crédits.'
  ),
  ('Mon employeur voit-il mes réservations ?', 'Non. Votre employeur ne voit que des chiffres agrégés.'),
];

const _categories = {
  'booking': 'Une réservation',
  'credits': 'Mes crédits',
  'account': 'Mon compte',
  'partner': 'Un établissement',
  'other': 'Autre',
};

Future<void> showSupportForm(BuildContext context, WidgetRef ref) => showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: XColors.cream,
      builder: (c) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(c).viewInsets.bottom),
        child: const SupportForm(),
      ),
    );

class SupportForm extends ConsumerStatefulWidget {
  const SupportForm({super.key});

  @override
  ConsumerState<SupportForm> createState() => _SupportFormState();
}

class _SupportFormState extends ConsumerState<SupportForm> {
  String _category = 'booking';
  final _subject = TextEditingController();
  final _message = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _subject.dispose();
    _message.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final r = await ref.read(accountRepositoryProvider).openSupport(
            category: _category,
            subject: _subject.text.trim(),
            message: _message.text.trim(),
          );
      ref.invalidate(supportRequestsProvider);
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Demande ${r.reference} envoyée. Vous recevrez la réponse dans « Mes demandes ».')));
      }
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('Contacter le support', style: serif(28)),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _category,
              decoration: const InputDecoration(labelText: 'Votre demande concerne'),
              items: [for (final e in _categories.entries) DropdownMenuItem(value: e.key, child: Text(e.value))],
              onChanged: (v) => setState(() => _category = v ?? 'other'),
            ),
            TextField(controller: _subject, maxLength: 160, decoration: const InputDecoration(labelText: 'Objet')),
            TextField(
                controller: _message,
                maxLines: 5,
                maxLength: 4000,
                decoration: const InputDecoration(labelText: 'Message')),
            if (_error != null) Text(_error!, style: const TextStyle(color: Color(0xFFB42318))),
            const SizedBox(height: 8),
            FilledButton(onPressed: _busy ? null : _send, child: Text(_busy ? 'Envoi…' : 'Envoyer')),
          ]),
        ),
      );
}

class MyRequests extends ConsumerWidget {
  const MyRequests({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final list = ref.watch(supportRequestsProvider);
    return ListView(padding: const EdgeInsets.all(20), children: [
      Text('Mes demandes', style: serif(28)),
      const SizedBox(height: 8),
      ...list.when(
        loading: () => [const SizedBox(height: 120, child: LoadingView())],
        error: (e, _) => [ErrorView(error: e, onRetry: () => ref.invalidate(supportRequestsProvider))],
        data: (items) => items.isEmpty
            ? [const EmptyView(message: 'Aucune demande pour le moment.')]
            : [
                for (final r in items)
                  _Card(children: [
                    Row(children: [
                      Expanded(
                          child: Text('${r.reference} · ${r.subject}',
                              style: const TextStyle(fontWeight: FontWeight.w700))),
                      _Pill(ok: r.status != 'open', text: r.statusLabel),
                    ]),
                    Text(fmt.shortDate(r.createdAt), style: const TextStyle(color: XColors.navyMuted, fontSize: 13)),
                    const SizedBox(height: 6),
                    Text(r.message),
                    if (r.reply != null) ...[
                      const Divider(),
                      const Text('Réponse de l’équipe XPASS', style: TextStyle(fontWeight: FontWeight.w600)),
                      Text(r.reply!),
                    ],
                  ]),
              ],
      ),
    ]);
  }
}

class _PushSwitch extends ConsumerWidget {
  const _PushSwitch();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = context.l10n;
    final enabled = ref.watch(pushEnabledProvider).valueOrNull ?? false;
    return _SwitchRow(
      icon: LucideIcons.smartphone,
      label: l.pushNotifications,
      hint: l.pushNotificationsHint,
      value: enabled,
      onChanged: (v) => togglePushNotifications(ref, v),
    );
  }
}

/// Carte d'identité : bleu nuit, avatar corail, e-mail et vérification ; touche pour modifier le nom.
class _IdentityCard extends StatelessWidget {
  const _IdentityCard({
    required this.initials,
    required this.name,
    required this.email,
    required this.verified,
    required this.verifiedLabel,
    required this.onEdit,
  });
  final String initials;
  final String name;
  final String email;
  final bool verified;
  final String verifiedLabel;
  final VoidCallback onEdit;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: '$name, $email. Modifier',
        child: Pressable(
          onTap: onEdit,
          child: Container(
            margin: const EdgeInsets.only(bottom: 20),
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(28),
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xFF1C2650), XColors.navy],
              ),
              boxShadow: const [BoxShadow(color: Color(0x33121A35), blurRadius: 24, offset: Offset(0, 12))],
            ),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                borderRadius: BorderRadius.circular(20),
                onTap: onEdit,
                child: Row(children: [
                  Container(
                    width: 64,
                    height: 64,
                    alignment: Alignment.center,
                    decoration: const BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(colors: [XColors.coralBrand, XColors.coral]),
                    ),
                    child: Text(initials, style: serif(26, color: Colors.white)),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(name, style: serif(24, color: Colors.white), maxLines: 1, overflow: TextOverflow.ellipsis),
                      const SizedBox(height: 2),
                      Text(email,
                          style: TextStyle(color: Colors.white.withValues(alpha: 0.75)),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis),
                      const SizedBox(height: 8),
                      _Pill(ok: verified, text: verifiedLabel),
                    ]),
                  ),
                  Icon(LucideIcons.pencil, color: Colors.white.withValues(alpha: 0.75), size: 18),
                ]),
              ),
            ),
          ),
        ),
      );
}

/// Section : titre discret au-dessus, carte blanche ombrée, lignes séparées par un trait fin.
class _Section extends StatelessWidget {
  const _Section({required this.title, required this.children, this.index = 0});
  final String title;
  final List<Widget> children;
  final int index;

  @override
  Widget build(BuildContext context) => FadeSlideIn(
        index: index,
        child: Padding(
          padding: const EdgeInsets.only(bottom: 18),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Padding(
              padding: const EdgeInsetsDirectional.only(start: 6, bottom: 8),
              child: Text(title.toUpperCase(),
                  style: const TextStyle(
                      fontSize: 12, letterSpacing: 1.6, fontWeight: FontWeight.w700, color: XColors.navyMuted)),
            ),
            DecoratedBox(
              decoration:
                  BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(22), boxShadow: softShadow),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(22),
                child: Column(children: [
                  for (final (i, c) in children.indexed) ...[
                    if (i > 0) const Divider(height: 1, indent: 62, color: XColors.line),
                    c,
                  ],
                ]),
              ),
            ),
          ]),
        ),
      );
}

class _Card extends StatelessWidget {
  const _Card({required this.children});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(22), boxShadow: softShadow),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: children),
      );
}

/// Icône dans une pastille arrondie (lavande ; rouge pour les actions sensibles).
class _IconChip extends StatelessWidget {
  const _IconChip(this.icon, {this.danger = false});
  final IconData icon;
  final bool danger;

  @override
  Widget build(BuildContext context) => Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          color: danger ? const Color(0xFFFDE8E4) : XColors.lavender,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(icon, size: 18, color: danger ? XColors.coral : XColors.navy),
      );
}

class _Row extends StatelessWidget {
  const _Row({required this.icon, required this.label, this.value, this.onTap, this.danger = false});
  final IconData icon;
  final String label;
  final String? value;
  final VoidCallback? onTap;
  final bool danger;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            child: Row(children: [
              _IconChip(icon, danger: danger),
              const SizedBox(width: 12),
              Expanded(
                child: Text(label,
                    style: TextStyle(
                        fontSize: 16, color: danger ? XColors.coral : XColors.navy, fontWeight: FontWeight.w500)),
              ),
              if (value != null) Text(value!, style: const TextStyle(color: XColors.navyMuted, fontSize: 14)),
              if (onTap != null) ...[
                const SizedBox(width: 4),
                const Icon(Icons.chevron_right, color: XColors.navyMuted),
              ],
            ]),
          ),
        ),
      );
}

class _SwitchRow extends StatelessWidget {
  const _SwitchRow(
      {required this.icon, required this.label, required this.hint, required this.value, required this.onChanged});
  final IconData icon;
  final String label;
  final String hint;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) => MergeSemantics(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          child: Row(children: [
            _IconChip(icon),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(label, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500)),
                Text(hint, style: const TextStyle(fontSize: 13, color: XColors.navyMuted)),
              ]),
            ),
            Switch(value: value, onChanged: onChanged, activeColor: Colors.white, activeTrackColor: XColors.coral),
          ]),
        ),
      );
}

class _Pill extends StatelessWidget {
  const _Pill({required this.ok, required this.text});
  final bool ok;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(color: ok ? XColors.mint : XColors.lavender, borderRadius: BorderRadius.circular(20)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          if (ok) const Icon(Icons.check_circle, size: 14, color: Color(0xFF2F7A45)),
          if (ok) const SizedBox(width: 4),
          Flexible(child: Text(text, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600))),
        ]),
      );
}
