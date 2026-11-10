import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth.dart';

import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../core/l10n.dart';

/// Navigation fixe : Explorer · Réservations · Mes crédits · Paramètres.
class AppShell extends ConsumerWidget {
  const AppShell({super.key, required this.shell});
  final StatefulNavigationShell shell;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = context.l10n;
    // L'onglet Paramètres sans session affiche l'écran de connexion (maquette 02), en plein écran.
    final auth = ref.watch(authProvider);
    final signInScreen = shell.currentIndex == 3 && !auth.isLoading && auth.valueOrNull == null;
    final items = [
      (XIcons.explore, l.navExplore),
      (XIcons.bookings, l.navBookings),
      (XIcons.credits, l.navCredits),
      (XIcons.profile, l.navProfile),
    ];
    return Scaffold(
      body: shell,
      bottomNavigationBar: signInScreen
          ? null
          : SafeArea(
              top: false,
              minimum: const EdgeInsets.only(bottom: 10),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 6, 16, 4),
                child: _FloatingNavBar(
                  items: items,
                  current: shell.currentIndex,
                  onSelect: (i) => shell.goBranch(i, initialLocation: i == shell.currentIndex),
                ),
              ),
            ),
    );
  }
}

/// Barre flottante : pilule bleu nuit, l'onglet actif s'élargit en pastille corail avec son nom.
class _FloatingNavBar extends StatelessWidget {
  const _FloatingNavBar({required this.items, required this.current, required this.onSelect});
  final List<(IconData, String)> items;
  final int current;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      explicitChildNodes: true,
      child: Container(
        height: 64,
        padding: const EdgeInsets.all(6),
        decoration: BoxDecoration(
          color: XColors.navy,
          borderRadius: BorderRadius.circular(32),
          boxShadow: const [
            BoxShadow(color: Color(0x33121A35), blurRadius: 24, offset: Offset(0, 10)),
          ],
        ),
        child: Row(children: [
          for (final (i, (icon, label)) in items.indexed)
            Expanded(
              flex: i == current ? 5 : 3,
              child: _NavItem(icon: icon, label: label, selected: i == current, onTap: () => onSelect(i)),
            ),
        ]),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({required this.icon, required this.label, required this.selected, required this.onTap});
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final reduce = MediaQuery.of(context).disableAnimations;
    final duration = Duration(milliseconds: reduce ? 0 : 280);
    return Semantics(
      button: true,
      selected: selected,
      label: label,
      excludeSemantics: true,
      child: Tooltip(
        message: label,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: onTap,
          child: AnimatedContainer(
            duration: duration,
            curve: Curves.easeOutCubic,
            margin: const EdgeInsets.symmetric(horizontal: 2),
            decoration: BoxDecoration(
              color: selected ? XColors.coral : Colors.transparent,
              borderRadius: BorderRadius.circular(22),
            ),
            child: Center(
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                AnimatedScale(
                  duration: duration,
                  scale: selected ? 1 : 0.92,
                  child: Icon(icon, size: 22, color: selected ? Colors.white : Colors.white.withValues(alpha: 0.62)),
                ),
                // Le nom n'apparaît que sur l'onglet actif (les autres ont une info-bulle et un libellé accessible).
                AnimatedSize(
                  duration: duration,
                  curve: Curves.easeOutCubic,
                  child: selected
                      ? Padding(
                          padding: const EdgeInsets.only(left: 8),
                          child: Text(
                            label,
                            maxLines: 1,
                            overflow: TextOverflow.fade,
                            softWrap: false,
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 14),
                          ),
                        )
                      : const SizedBox.shrink(),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

/// Onglet dont le lot n'est pas encore livré. Aucun contenu simulé.
class ComingSoonScreen extends StatelessWidget {
  const ComingSoonScreen({super.key, required this.title, required this.description, required this.lot});
  final String title;
  final String description;
  final String lot;

  @override
  Widget build(BuildContext context) => Scaffold(
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const XpassLogo(height: 28),
              const SizedBox(height: 32),
              Text(title, style: serif(40)),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(color: XColors.lavender, borderRadius: BorderRadius.circular(14)),
                child: Text('Bientôt disponible · $lot', style: const TextStyle(fontWeight: FontWeight.w600)),
              ),
              const SizedBox(height: 16),
              Text(description, style: const TextStyle(fontSize: 16, color: XColors.navyMuted, height: 1.45)),
              const Spacer(),
              OutlinedButton.icon(
                onPressed: () => context.go('/explore'),
                icon: const Icon(Icons.explore_outlined),
                label: const Text('Explorer les activités'),
              ),
            ]),
          ),
        ),
      );
}
