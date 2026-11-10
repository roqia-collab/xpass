import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../catalog/catalog_repository.dart';
import 'location_cards.dart';

/// Recherche texte et « Voir tout » de l'accueil.
class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key, this.initialQuery});
  final String? initialQuery;

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  late final _controller = TextEditingController(text: widget.initialQuery);
  late String? _q = widget.initialQuery;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final city = ref.watch(selectedCityProvider);
    final query = LocationQuery(city: city.slug, q: _q, limit: 50);
    final results = ref.watch(locationSearchProvider(query));
    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _controller,
          autofocus: widget.initialQuery == null,
          textInputAction: TextInputAction.search,
          onSubmitted: (v) => setState(() => _q = v.trim().isEmpty ? null : v.trim()),
          decoration: const InputDecoration(hintText: 'Rechercher une activité, un lieu…', border: InputBorder.none),
        ),
        actions: const [CityChip()],
      ),
      body: results.when(
        loading: () => const LoadingView(),
        error: (e, _) => ErrorView(error: e, onRetry: () => ref.invalidate(locationSearchProvider(query))),
        data: (page) => page.items.isEmpty
            ? EmptyView(message: _q == null ? 'Aucune activité dans cette ville.' : 'Aucun résultat pour « $_q ».')
            : ListView.separated(
                padding: const EdgeInsets.all(20),
                itemCount: page.items.length + 1,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder: (_, i) => i == 0
                    ? Text('${page.total} résultat${page.total > 1 ? 's' : ''} à ${city.name}',
                        style: const TextStyle(color: XColors.navyMuted))
                    : HorizontalLocationCard(location: page.items[i - 1]),
              ),
      ),
    );
  }
}
