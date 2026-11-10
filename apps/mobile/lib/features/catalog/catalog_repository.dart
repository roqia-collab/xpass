import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import 'models.dart';

/// Paramètres de recherche ; égalité par valeur pour servir de clé de provider.
class LocationQuery {
  const LocationQuery(
      {this.city = 'paris',
      this.category,
      this.subcategory,
      this.q,
      this.maxCredits,
      this.day,
      this.sort = 'distance',
      this.limit = 20});

  final String city;
  final String? category;
  final String? subcategory;
  final String? q;
  final int? maxCredits;
  final DateTime? day;
  final String sort;
  final int limit;

  Map<String, dynamic> toParams() => {
        'city': city,
        if (category != null) 'category': category,
        if (subcategory != null) 'subcategory': subcategory,
        if (q != null && q!.isNotEmpty) 'q': q,
        if (maxCredits != null) 'max_credits': maxCredits,
        if (day != null)
          'day': '${day!.year}-${day!.month.toString().padLeft(2, '0')}-${day!.day.toString().padLeft(2, '0')}',
        'sort': sort,
        'limit': limit,
      };

  @override
  bool operator ==(Object other) =>
      other is LocationQuery &&
      other.city == city &&
      other.category == category &&
      other.subcategory == subcategory &&
      other.q == q &&
      other.maxCredits == maxCredits &&
      other.day?.year == day?.year &&
      other.day?.month == day?.month &&
      other.day?.day == day?.day &&
      other.sort == sort &&
      other.limit == limit;

  @override
  int get hashCode => Object.hash(city, category, subcategory, q, maxCredits, day?.year, day?.month, day?.day, sort, limit);
}

class CatalogRepository {
  CatalogRepository(this._dio);
  final Dio _dio;

  Future<T> _get<T>(String path, T Function(dynamic data) parse, {Map<String, dynamic>? params}) async {
    try {
      final res = await _dio.get<dynamic>(path, queryParameters: params);
      return parse(res.data);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  Future<List<Category>> categories() =>
      _get('/catalog/categories', (d) => (d as List).map((e) => Category.fromJson(e as Map<String, dynamic>)).toList());

  Future<List<City>> cities() =>
      _get('/geo/cities', (d) => (d as List).map((e) => City.fromJson(e as Map<String, dynamic>)).toList());

  Future<LocationPage> search(LocationQuery query) =>
      _get('/catalog/locations', (d) => LocationPage.fromJson(d as Map<String, dynamic>), params: query.toParams());

  /// Carte « Autour de moi » : lieux dans un rayon autour d'un point, triés par distance.
  Future<LocationPage> searchArea(
          {required double lat,
          required double lng,
          required int radiusM,
          String? category,
          int? maxCredits,
          DateTime? day,
          int? participants}) =>
      _get('/catalog/locations', (d) => LocationPage.fromJson(d as Map<String, dynamic>), params: {
        'lat': lat,
        'lng': lng,
        'radius_m': radiusM,
        if (category != null) 'category': category,
        if (maxCredits != null) 'max_credits': maxCredits,
        if (day != null)
          'day': '${day.year}-${day.month.toString().padLeft(2, '0')}-${day.day.toString().padLeft(2, '0')}',
        if (participants != null) 'participants': participants,
        'limit': 50,
      });

  Future<LocationDetail> location(String slug) =>
      _get('/catalog/locations/$slug', (d) => LocationDetail.fromJson(d as Map<String, dynamic>));
}

final catalogRepositoryProvider = Provider((ref) => CatalogRepository(ref.watch(dioProvider)));

final categoriesProvider = FutureProvider<List<Category>>((ref) => ref.watch(catalogRepositoryProvider).categories());

final citiesProvider = FutureProvider<List<City>>((ref) => ref.watch(catalogRepositoryProvider).cities());

/// Ville sélectionnée (Paris par défaut ; la géolocalisation arrive au lot 8).
final selectedCityProvider = StateProvider<City>((ref) => const City(slug: 'paris', name: 'Paris'));

final locationSearchProvider = FutureProvider.family<LocationPage, LocationQuery>(
    (ref, query) => ref.watch(catalogRepositoryProvider).search(query));

final locationDetailProvider =
    FutureProvider.family<LocationDetail, String>((ref, slug) => ref.watch(catalogRepositoryProvider).location(slug));

final categoryProvider = FutureProvider.family<Category?, String>((ref, slug) async {
  final all = await ref.watch(categoriesProvider.future);
  for (final c in all) {
    if (c.slug == slug) return c;
  }
  return null;
});
