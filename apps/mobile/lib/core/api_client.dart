import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'config.dart';

/// Erreur présentable à l'utilisateur. Jamais de succès inventé en cas d'échec.
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode, this.isNetwork = false, this.code});

  final String message;

  /// Code métier renvoyé par l'API (`slot_full`, `insufficient_credits`, ...).
  final String? code;
  final int? statusCode;
  final bool isNetwork;

  @override
  String toString() => message;

  factory ApiException.fromDio(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.sendTimeout:
        return ApiException('Le serveur met trop de temps à répondre. Réessayez.', isNetwork: true);
      case DioExceptionType.connectionError:
        return ApiException('Connexion impossible. Vérifiez votre réseau.', isNetwork: true);
      default:
        final status = e.response?.statusCode;
        final data = e.response?.data;
        final detail = data is Map ? data['detail'] : null;
        final message = detail is Map && detail['message'] is String
            ? detail['message'] as String
            : 'Une erreur est survenue (${status ?? 'réseau'}).';
        return ApiException(message, statusCode: status, code: detail is Map ? detail['code'] as String? : null);
    }
  }
}

/// Client sans authentification (catalogue public, connexion).
final rawDioProvider = Provider<Dio>((ref) {
  return Dio(BaseOptions(
    baseUrl: '${AppConfig.apiBaseUrl}/api/v1',
    connectTimeout: const Duration(seconds: 8),
    receiveTimeout: const Duration(seconds: 15),
    headers: {'Accept': 'application/json', 'Accept-Language': 'fr-FR'},
  ));
});

/// Alias historique utilisé par le catalogue.
final dioProvider = rawDioProvider;
