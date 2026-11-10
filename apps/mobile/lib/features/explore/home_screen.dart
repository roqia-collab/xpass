import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/format.dart' as fmt;
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../account/account_repository.dart';
import '../booking/booking_repository.dart';
import '../catalog/catalog_repository.dart';
import '../catalog/models.dart';
import 'location_cards.dart';
import '../../core/l10n.dart';

/// Jour sélectionné sur l'accueil (créneaux du jour, comme un pass crédits).
final homeDayProvider = StateProvider<DateTime>((ref) {
  final n = DateTime.now();
  return DateTime(n.year, n.month, n.day);
});

/// Filtre univers sur le fil « à réserver » (null = tous : sport, culture, beauté, sorties).
final homeCategoryFilterProvider = StateProvider<String?>((ref) => null);

/// Accueil client : dates, univers, puis cartes à réserver.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final city = ref.watch(selectedCityProvider);
    final day = ref.watch(homeDayProvider);
    final category = ref.watch(homeCategoryFilterProvider);
    final categories = ref.watch(categoriesProvider);
    final nearby = ref.watch(locationSearchProvider(
        LocationQuery(city: city.slug, category: category, day: day, limit: 8)));

    return Scaffold(
      backgroundColor: XColors.navy,
      body: RefreshIndicator(
        color: XColors.coralBrand,
        onRefresh: () async {
          ref.invalidate(categoriesProvider);
          ref.invalidate(locationSearchProvider);
        },
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            const _HomeHero(),
            ColoredBox(
              color: XColors.cream,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 18, 14, 32),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              categories.when(
                loading: () => const SizedBox(height: 320, child: LoadingView()),
                error: (e, _) => ErrorView(error: e, onRetry: () => ref.invalidate(categoriesProvider)),
                data: (list) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  _UniverseChips(categories: list, selected: category),
                  const SizedBox(height: 14),
                  _CategoryGrid(categories: list),
                ]),
              ),
              const SizedBox(height: 28),
              Row(children: [
                Expanded(child: Text(context.l10n.nearYou, style: serif(26))),
                IconButton(
                  tooltip: context.l10n.seeOnMap,
                  onPressed: () => context.push('/explore/autour'),
                  icon: const Icon(Icons.map_outlined, color: XColors.lavenderText),
                ),
                TextButton(
                  onPressed: () => context.push('/explore/recherche'),
                  child: Row(children: [
                    Text(context.l10n.seeAll, style: const TextStyle(color: XColors.lavenderText, fontSize: 16)),
                    const Icon(Icons.chevron_right, color: XColors.lavenderText),
                  ]),
                ),
              ]),
              const SizedBox(height: 8),
              nearby.when(
                loading: () => const SizedBox(height: 160, child: LoadingView()),
                error: (e, _) => ErrorView(error: e, onRetry: () => ref.invalidate(locationSearchProvider)),
                data: (page) => page.items.isEmpty
                    ? EmptyView(message: context.l10n.noSlotsThatDay)
                    : Column(children: [
                        for (final (i, l) in page.items.take(8).indexed) ...[
                          FadeSlideIn(
                            index: i,
                            child: HorizontalLocationCard(location: l, showBookButton: true),
                          ),
                          const SizedBox(height: 14),
                        ],
                      ]),
              ),
              const SizedBox(height: 8),
              _EmployeeBenefitBanner(onTap: () => context.go('/profil')),
                ]),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HomeHero extends StatefulWidget {
  const _HomeHero();

  @override
  State<_HomeHero> createState() => _HomeHeroState();
}

class _HomeHeroState extends State<_HomeHero> {
  static const _photos = [
    'demo/heroes/divertissement.jpg',
    'demo/heroes/sport.jpg',
    'demo/heroes/culture.jpg',
    'demo/heroes/beaute.jpg',
  ];
  int _index = 0;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (!mounted) return;
      setState(() => _index = (_index + 1) % _photos.length);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(bottom: Radius.circular(32)),
      child: DecoratedBox(
        decoration: const BoxDecoration(color: XColors.navy),
        child: Stack(children: [
          Positioned.fill(
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 900),
              child: KeyedSubtree(
                key: ValueKey(_photos[_index]),
                child: KenBurnsPhoto(imageKey: _photos[_index], fallbackIcon: Icons.photo_outlined),
              ),
            ),
          ),
          const Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Color(0x990A0F1C), Color(0xCC0A0F1C), XColors.navy],
                  stops: [0, 0.45, 1],
                ),
              ),
            ),
          ),
          SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 18),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                FadeSlideIn(
                  child: Row(children: [
                    Text('XPASS', style: serif(28, color: Colors.white, height: 1)),
                    const Spacer(),
                    const _BellChip(onDark: true),
                    const SizedBox(width: 6),
                    _AccountChip(onTap: () => context.go('/credits'), onDark: true),
                  ]),
                ),
                const SizedBox(height: 18),
                FadeSlideIn(
                  index: 1,
                  child: Text('Un pass.\nToutes vos envies.', style: serif(34, color: Colors.white, height: 0.95)),
                ),
                const SizedBox(height: 8),
                const FadeSlideIn(
                  index: 2,
                  child: Text('Sport, culture, beauté, sorties.', style: TextStyle(color: Colors.white70, fontSize: 15)),
                ),
                const SizedBox(height: 16),
                FadeSlideIn(
                  index: 3,
                  child: Row(children: [
                    const CityChip(onDark: true),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _SearchField(
                        onDark: true,
                        onSubmitted: (q) => context.push('/explore/recherche?q=${Uri.encodeQueryComponent(q)}'),
                      ),
                    ),
                  ]),
                ),
                const SizedBox(height: 14),
                const FadeSlideIn(index: 4, child: _QuickActions(onDark: true)),
                const SizedBox(height: 12),
                const _DateStrip(onDark: true),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}

class _QuickActions extends StatelessWidget {
  const _QuickActions({this.onDark = false});
  final bool onDark;

  @override
  Widget build(BuildContext context) {
    final actions = [
      (Icons.map_outlined, 'Carte', () => context.push('/explore/autour')),
      (XIcons.credits, 'Crédits', () => context.go('/credits')),
    ];
    return Row(
      children: [
        for (final (i, a) in actions.indexed) ...[
          if (i > 0) const SizedBox(width: 8),
          Expanded(
            child: Pressable(
              onTap: a.$3,
              child: Material(
                color: onDark ? Colors.white12 : Colors.white,
                shape: const StadiumBorder(),
                child: InkWell(
                  customBorder: const StadiumBorder(),
                  onTap: a.$3,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                      Icon(a.$1, size: 18, color: onDark ? Colors.white : XColors.coral),
                      const SizedBox(width: 6),
                      Text(a.$2,
                          style: TextStyle(
                              color: onDark ? Colors.white : XColors.navy, fontWeight: FontWeight.w700, fontSize: 13)),
                    ]),
                  ),
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _BellChip extends ConsumerWidget {
  const _BellChip({this.onDark = false});
  final bool onDark;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final unread = ref.watch(unreadNotificationCountProvider);
    return IconButton.filledTonal(
      tooltip: context.l10n.notifications,
      style: IconButton.styleFrom(
        backgroundColor: onDark ? Colors.white12 : Colors.white,
        foregroundColor: onDark ? Colors.white : XColors.navy,
      ),
      onPressed: () => context.push('/profil/notifications'),
      icon: Badge(
        isLabelVisible: unread > 0,
        label: Text('$unread'),
        child: const Icon(Icons.notifications_none),
      ),
    );
  }
}

/// Solde réel lu depuis l'API quand le client est connecté ; sinon simple accès aux crédits.
class _AccountChip extends ConsumerWidget {
  const _AccountChip({required this.onTap, this.onDark = false});
  final VoidCallback onTap;
  final bool onDark;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final available = ref.watch(walletProvider).valueOrNull?.available;
    final fg = onDark ? Colors.white : XColors.navy;
    return Material(
      color: onDark ? XColors.coralBrand : Colors.white,
      shape: StadiumBorder(side: BorderSide(color: onDark ? Colors.transparent : XColors.line)),
      child: InkWell(
        customBorder: const StadiumBorder(),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(XIcons.credits, size: 18, color: fg),
            const SizedBox(width: 6),
            Text(available == null ? 'Crédits' : '$available crédits',
                style: TextStyle(fontWeight: FontWeight.w700, color: fg)),
          ]),
        ),
      ),
    );
  }
}

class _DateStrip extends ConsumerWidget {
  const _DateStrip({this.onDark = false});
  final bool onDark;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selected = ref.watch(homeDayProvider);
    final today = fmt.dateOnly(DateTime.now());
    final days = [for (var i = 0; i < 7; i++) today.add(Duration(days: i))];
    return SizedBox(
      height: 44,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: days.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final day = days[i];
          final on = day.year == selected.year && day.month == selected.month && day.day == selected.day;
          final label = i == 0
              ? context.l10n.todayChip
              : i == 1
                  ? context.l10n.tomorrowChip
                  : fmt.weekdayShortDay(day);
          return Material(
            color: on ? XColors.coralBrand : (onDark ? Colors.white24 : Colors.white),
            shape: const StadiumBorder(),
            child: InkWell(
              customBorder: const StadiumBorder(),
              onTap: () => ref.read(homeDayProvider.notifier).state = day,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                child: Text(
                  label,
                  style: TextStyle(fontWeight: FontWeight.w600, color: on || onDark ? Colors.white : XColors.navy),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _UniverseChips extends ConsumerWidget {
  const _UniverseChips({required this.categories, required this.selected});
  final List<Category> categories;
  final String? selected;

  @override
  Widget build(BuildContext context, WidgetRef ref) => SizedBox(
        height: 40,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: categories.length + 1,
          separatorBuilder: (_, __) => const SizedBox(width: 8),
          itemBuilder: (context, i) {
            final slug = i == 0 ? null : categories[i - 1].slug;
            final label = i == 0 ? context.l10n.allUniverses : categories[i - 1].name;
            final on = selected == slug;
            return Material(
              color: on ? XColors.navy : Colors.white,
              shape: StadiumBorder(side: BorderSide(color: on ? XColors.navy : XColors.line)),
              child: InkWell(
                customBorder: const StadiumBorder(),
                onTap: () => ref.read(homeCategoryFilterProvider.notifier).state = slug,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  child: Text(
                    label,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: on ? Colors.white : XColors.navy,
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      );
}

class _SearchField extends StatelessWidget {
  const _SearchField({required this.onSubmitted, this.onDark = false});
  final ValueChanged<String> onSubmitted;
  final bool onDark;

  @override
  Widget build(BuildContext context) => TextField(
        style: TextStyle(color: onDark ? Colors.white : XColors.navy, fontWeight: FontWeight.w600),
        textInputAction: TextInputAction.search,
        onSubmitted: (v) => v.trim().isEmpty ? null : onSubmitted(v.trim()),
        decoration: InputDecoration(
          hintText: context.l10n.homeSearchHint,
          prefixIcon: Icon(Icons.search, size: 22, color: onDark ? Colors.white70 : XColors.navyMuted),
          filled: true,
          fillColor: onDark ? Colors.white12 : Colors.white,
          hintStyle: TextStyle(color: onDark ? Colors.white54 : XColors.navyMuted, fontSize: 14),
          contentPadding: const EdgeInsets.symmetric(vertical: 12),
          border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(32), borderSide: const BorderSide(color: XColors.line)),
          enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(32), borderSide: const BorderSide(color: XColors.line)),
        ),
      );
}

class _CategoryGrid extends StatelessWidget {
  const _CategoryGrid({required this.categories});
  final List<Category> categories;

  @override
  Widget build(BuildContext context) => GridView.count(
        crossAxisCount: 2,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 8,
        crossAxisSpacing: 8,
        childAspectRatio: 1.18,
        children: [
          for (final (i, c) in categories.indexed) FadeSlideIn(index: i, child: _CategoryTile(category: c)),
        ],
      );
}

class _CategoryTile extends StatelessWidget {
  const _CategoryTile({required this.category});
  final Category category;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: category.name,
        child: Pressable(
          onTap: () => context.push('/explore/univers/${category.slug}'),
          child: DecoratedBox(
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(24), boxShadow: softShadow),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(24),
              child: Material(
                child: InkWell(
                  onTap: () => context.push('/explore/univers/${category.slug}'),
                  child: Stack(fit: StackFit.expand, children: [
                    MediaImage(imageKey: category.tileImageKey, fallbackIcon: categoryIcon(category.slug)),
                    const DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [Colors.transparent, Color(0xCC0B1024)],
                          stops: [0.45, 1],
                        ),
                      ),
                    ),
                    Positioned(
                      left: 10,
                      right: 8,
                      bottom: 10,
                      child: Row(children: [
                        Expanded(
                          // Maquette 01 : titre sur une ligne, réduit plutôt que coupé.
                          child: FittedBox(
                            fit: BoxFit.scaleDown,
                            alignment: AlignmentDirectional.centerStart,
                            child: Text(category.name, style: serif(19, color: Colors.white), maxLines: 1),
                          ),
                        ),
                        const SizedBox(width: 6),
                        Container(
                          width: 30,
                          height: 30,
                          decoration: BoxDecoration(
                            color: XColors.navy.withValues(alpha: 0.75),
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white54),
                          ),
                          child: const Icon(Icons.chevron_right, color: Colors.white, size: 20),
                        ),
                      ]),
                    ),
                  ]),
                ),
              ),
            ),
          ),
        ),
      );
}

class _EmployeeBenefitBanner extends StatelessWidget {
  const _EmployeeBenefitBanner({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: XColors.lavender,
        borderRadius: BorderRadius.circular(XRadius.card),
        child: InkWell(
          borderRadius: BorderRadius.circular(XRadius.card),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Row(children: [
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
                child: const Icon(XIcons.gift, size: 36, color: XColors.navy),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Votre avantage salarié', style: serif(22)),
                  const SizedBox(height: 4),
                  const Text('Connectez-vous pour voir les crédits offerts par votre employeur.',
                      style: TextStyle(color: XColors.navyMuted)),
                ]),
              ),
              const Icon(Icons.chevron_right),
            ]),
          ),
        ),
      );
}
