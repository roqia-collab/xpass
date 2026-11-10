import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../catalog/catalog_repository.dart';
import '../catalog/models.dart';
import 'location_cards.dart';

/// Maquettes 03 à 06 — un écran paramétré par l'univers renvoyé par l'API.
class CategoryScreen extends ConsumerStatefulWidget {
  const CategoryScreen({super.key, required this.slug});
  final String slug;

  @override
  ConsumerState<CategoryScreen> createState() => _CategoryScreenState();
}

class _CategoryScreenState extends ConsumerState<CategoryScreen> {
  String? _subcategory;
  int? _maxCredits;
  String _sort = 'distance';

  /// Divertissement et Culture : cartes horizontales ; Sport et Beauté : grandes photos.
  bool get _photoCards => widget.slug == 'sport' || widget.slug == 'beaute';

  @override
  Widget build(BuildContext context) {
    final category = ref.watch(categoryProvider(widget.slug));
    return Scaffold(
      body: category.when(
        loading: () => const LoadingView(),
        error: (e, _) => SafeArea(child: ErrorView(error: e, onRetry: () => ref.invalidate(categoriesProvider))),
        data: (c) => c == null
            ? const SafeArea(child: EmptyView(message: 'Cet univers est introuvable.'))
            : _buildBody(context, c),
      ),
    );
  }

  Widget _buildBody(BuildContext context, Category c) {
    final city = ref.watch(selectedCityProvider);
    final query = LocationQuery(
      city: city.slug,
      category: c.slug,
      subcategory: _subcategory,
      maxCredits: _maxCredits,
      sort: _sort,
    );
    final results = ref.watch(locationSearchProvider(query));

    return Stack(children: [
      CustomScrollView(slivers: [
        SliverToBoxAdapter(child: _Header(category: c, cityName: city.name)),
        SliverToBoxAdapter(
          child: _SubcategoryChips(
            subcategories: c.subcategories,
            selected: _subcategory,
            onSelected: (s) => setState(() => _subcategory = s == _subcategory ? null : s),
          ),
        ),
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
            child: Wrap(spacing: 10, runSpacing: 10, children: [
              _FilterChip(
                icon: XIcons.credits,
                label: _maxCredits == null ? 'Mon budget' : '≤ $_maxCredits crédits',
                active: _maxCredits != null,
                onTap: _pickBudget,
              ),
              _FilterChip(
                icon: _sort == 'distance' ? Icons.near_me_outlined : Icons.sort,
                label: _sort == 'distance' ? 'Distance' : 'Prix croissant',
                active: _sort != 'distance',
                onTap: () => setState(() => _sort = _sort == 'distance' ? 'price' : 'distance'),
              ),
            ]),
          ),
        ),
        results.when(
          loading: () => const SliverToBoxAdapter(child: SizedBox(height: 200, child: LoadingView())),
          error: (e, _) => SliverToBoxAdapter(
            child: ErrorView(error: e, onRetry: () => ref.invalidate(locationSearchProvider(query))),
          ),
          data: (page) => page.items.isEmpty
              ? const SliverToBoxAdapter(
                  child: EmptyView(message: 'Aucun résultat avec ces critères. Essayez d’élargir votre budget.'))
              : SliverMainAxisGroup(slivers: [
                  SliverToBoxAdapter(child: _PhotoStrip(items: page.items, accent: _accent(c.slug))),
                  SliverPadding(
                    padding: const EdgeInsets.fromLTRB(20, 4, 20, 110),
                    sliver: SliverList.separated(
                      itemCount: page.items.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 14),
                      itemBuilder: (_, i) => FadeSlideIn(
                        index: i.clamp(0, 8),
                        child: _photoCards
                            ? PhotoLocationCard(location: page.items[i])
                            : HorizontalLocationCard(location: page.items[i]),
                      ),
                    ),
                  ),
                ]),
        ),
      ]),
      Positioned(
        left: 20,
        right: 20,
        bottom: 16,
        child: CoralButton(
          label: c.ctaLabel,
          icon: c.slug == 'divertissement' ? Icons.location_on : null,
          onPressed: () => context.push('/explore/autour?categorie=${c.slug}'),
        ),
      ),
    ]);
  }

  Future<void> _pickBudget() async {
    const options = [10, 15, 20, 30, 40];
    final picked = await showModalBottomSheet<int?>(
      context: context,
      backgroundColor: XColors.cream,
      builder: (context) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Padding(padding: const EdgeInsets.all(20), child: Text('Budget maximum', style: serif(26))),
          for (final o in options) ListTile(title: Text('Jusqu’à $o crédits'), onTap: () => Navigator.pop(context, o)),
          ListTile(title: const Text('Sans limite'), onTap: () => Navigator.pop(context, -1)),
        ]),
      ),
    );
    if (picked != null) setState(() => _maxCredits = picked == -1 ? null : picked);
  }
}

Color _accent(String slug) => switch (slug) {
      'sport' => const Color(0xFFFF3B1F),
      'culture' => const Color(0xFFC4A574),
      'beaute' => const Color(0xFFE7A0B4),
      _ => const Color(0xFF7C8CFF),
    };

class _Header extends StatelessWidget {
  const _Header({required this.category, required this.cityName});
  final Category category;
  final String cityName;

  @override
  Widget build(BuildContext context) {
    final slug = category.slug;
    final tagline = slug == 'divertissement' ? '${category.tagline.replaceAll('.', '')} à $cityName.' : category.tagline;
    final accent = _accent(slug);
    final veil = switch (slug) {
      'sport' => const [Color(0x660A0F1C), Color(0xCC1A0C0A), Color(0xFF0A0F1C)],
      'culture' => const [Color(0x44140E08), Color(0xCC1C140C), Color(0xFF120E0A)],
      'beaute' => const [Color(0x664A2434), Color(0xCC3A2030), Color(0xFF2A1822)],
      _ => const [Color(0x660A0F1C), Color(0xDD101428), Color(0xFF0A0F1C)],
    };
    return ClipRRect(
      borderRadius: BorderRadius.vertical(bottom: Radius.circular(slug == 'beaute' ? 40 : 28)),
      child: SizedBox(
        height: 360,
        child: Stack(fit: StackFit.expand, children: [
          KenBurnsPhoto(
            imageKey: category.heroImageKey ?? category.tileImageKey,
            fallbackIcon: categoryIcon(slug),
          ),
          DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: veil),
            ),
          ),
          SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(8, 4, 12, 20),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  IconButton(
                    tooltip: 'Retour',
                    color: Colors.white,
                    onPressed: () => context.canPop() ? context.pop() : context.go('/explore'),
                    icon: const Icon(Icons.arrow_back),
                  ),
                  const Spacer(),
                  CityChip(onDark: true, background: Colors.white24),
                ]),
                const Spacer(),
                FadeSlideIn(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(color: accent, borderRadius: BorderRadius.circular(20)),
                        child: Text(category.eyebrow,
                            style: const TextStyle(letterSpacing: 1.4, fontSize: 11, color: Colors.white, fontWeight: FontWeight.w700)),
                      ),
                      const SizedBox(height: 10),
                      Text(category.headline, style: serif(40, color: Colors.white, height: 0.98)),
                      const SizedBox(height: 8),
                      Text(tagline, style: const TextStyle(fontSize: 16, color: Colors.white70, height: 1.35)),
                    ]),
                  ),
                ),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}

class _PhotoStrip extends StatelessWidget {
  const _PhotoStrip({required this.items, required this.accent});
  final List<LocationCard> items;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final shown = items.take(8).toList();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 10),
        child: Text('En images', style: serif(22)),
      ),
      SizedBox(
        height: 128,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 20),
          itemCount: shown.length,
          separatorBuilder: (_, __) => const SizedBox(width: 10),
          itemBuilder: (_, i) {
            final l = shown[i];
            return FadeSlideIn(
              index: i,
              child: Pressable(
                onTap: () => openLocation(context, l),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(18),
                  child: SizedBox(
                    width: 168,
                    child: Stack(fit: StackFit.expand, children: [
                      MediaImage(imageKey: l.coverImageKey, fallbackIcon: categoryIcon(l.categorySlug)),
                      const DecoratedBox(
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [Colors.transparent, Color(0xCC0A0F1C)],
                            stops: [0.45, 1],
                          ),
                        ),
                      ),
                      Positioned(
                        left: 10,
                        right: 10,
                        bottom: 10,
                        child: Text(l.name,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
                      ),
                      Positioned(left: 10, top: 10, child: Container(width: 18, height: 4, color: accent)),
                    ]),
                  ),
                ),
              ),
            );
          },
        ),
      ),
      const SizedBox(height: 8),
    ]);
  }
}

class _SubcategoryChips extends StatelessWidget {
  const _SubcategoryChips({required this.subcategories, required this.selected, required this.onSelected});
  final List<Subcategory> subcategories;
  final String? selected;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Row(children: [
          for (final s in subcategories) ...[
            Semantics(
              selected: s.slug == selected,
              button: true,
              child: Material(
                color: s.slug == selected ? XColors.coral : XColors.lavender,
                shape: const StadiumBorder(),
                child: InkWell(
                  customBorder: const StadiumBorder(),
                  onTap: () => onSelected(s.slug),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                    child: Row(children: [
                      Icon(subcategoryIcon(s.icon), size: 20, color: s.slug == selected ? Colors.white : XColors.navy),
                      const SizedBox(width: 8),
                      Text(s.name,
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: s.slug == selected ? Colors.white : XColors.navy,
                          )),
                    ]),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 10),
          ],
        ]),
      );
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({required this.icon, required this.label, required this.onTap, this.active = false});
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool active;

  @override
  Widget build(BuildContext context) => Material(
        color: active ? XColors.lavender : Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: active ? XColors.lavenderStrong : XColors.line),
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(icon, size: 20),
              const SizedBox(width: 8),
              Text(label, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w500)),
              const Icon(Icons.keyboard_arrow_down, size: 20),
            ]),
          ),
        ),
      );
}
