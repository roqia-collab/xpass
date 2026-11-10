import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/auth.dart';

class SupportRequestInfo {
  const SupportRequestInfo({
    required this.reference,
    required this.subject,
    required this.message,
    required this.status,
    required this.createdAt,
    this.reply,
  });

  final String reference;
  final String subject;
  final String message;
  final String status;
  final DateTime createdAt;
  final String? reply;

  String get statusLabel => switch (status) {
        'answered' => 'Réponse reçue',
        'closed' => 'Close',
        _ => 'En cours',
      };

  factory SupportRequestInfo.fromJson(Map<String, dynamic> j) => SupportRequestInfo(
        reference: j['reference'] as String,
        subject: j['subject'] as String,
        message: j['message'] as String,
        status: j['status'] as String,
        createdAt: DateTime.parse(j['created_at'] as String).toLocal(),
        reply: j['reply'] as String?,
      );
}

/// Compte (écran 16) : préférences, assistance, export et suppression.
class AccountRepository {
  AccountRepository(this._dio);
  final Dio _dio;

  Future<T> _call<T>(Future<Response<dynamic>> Function() send, T Function(dynamic) parse) async {
    try {
      return parse((await send()).data);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  Future<void> updateProfile({String? displayName, String? locale, bool? notifyEmail}) => _call(
      () => _dio.patch('/me', data: {
            if (displayName != null) 'display_name': displayName,
            if (locale != null) 'locale': locale,
            if (notifyEmail != null) 'notify_email': notifyEmail,
          }),
      (_) {});

  /// Données personnelles au format JSON (portabilité).
  Future<String> exportData() =>
      _call(() => _dio.get('/me/export'), (d) => const JsonEncoder.withIndent('  ').convert(d));

  Future<void> deleteAccount() => _call(() => _dio.post('/me/delete', data: {'confirm': 'SUPPRIMER'}), (_) {});

  Future<List<SupportRequestInfo>> supportRequests() => _call(() => _dio.get('/me/support'),
      (d) => [for (final x in d as List) SupportRequestInfo.fromJson(x as Map<String, dynamic>)]);

  Future<SupportRequestInfo> openSupport(
          {required String category, required String subject, required String message}) =>
      _call(() => _dio.post('/me/support', data: {'category': category, 'subject': subject, 'message': message}),
          (d) => SupportRequestInfo.fromJson(d as Map<String, dynamic>));

  Future<List<AppNotification>> notifications() => _call(() => _dio.get('/me/notifications'),
      (d) => [for (final x in d as List) AppNotification.fromJson(x as Map<String, dynamic>)]);

  Future<void> registerWebDevice(String email) => _call(
      () => _dio.post('/me/devices',
          data: {
            'token': 'web-xpass-notifications-${email.replaceAll(RegExp(r'[^a-zA-Z0-9]'), '')}',
            'platform': 'web'
          }),
      (_) {});
}

class AppNotification {
  const AppNotification(
      {required this.id, required this.kind, required this.title, required this.body, required this.route, required this.createdAt});
  final String id;
  final String kind;
  final String title;
  final String body;
  final String route;
  final DateTime createdAt;

  factory AppNotification.fromJson(Map<String, dynamic> j) => AppNotification(
        id: j['id'] as String,
        kind: j['kind'] as String,
        title: j['title'] as String,
        body: j['body'] as String,
        route: j['route'] as String,
        createdAt: DateTime.parse(j['created_at'] as String).toLocal(),
      );
}

final accountRepositoryProvider = Provider((ref) => AccountRepository(ref.watch(authDioProvider)));

final supportRequestsProvider = FutureProvider.autoDispose<List<SupportRequestInfo>>((ref) async {
  if (await ref.watch(authProvider.future) == null) return const [];
  return ref.watch(accountRepositoryProvider).supportRequests();
});

final notificationsTickProvider = StreamProvider.autoDispose<int>((ref) {
  return Stream.periodic(const Duration(seconds: 25), (i) => i);
});

final notificationsProvider = FutureProvider.autoDispose<List<AppNotification>>((ref) async {
  ref.watch(notificationsTickProvider);
  if (await ref.watch(authProvider.future) == null) return const [];
  return ref.watch(accountRepositoryProvider).notifications();
});

final seenNotificationIdsProvider = StateProvider<Set<String>>((ref) => {});

final unreadNotificationCountProvider = Provider<int>((ref) {
  final items = ref.watch(notificationsProvider).valueOrNull ?? const [];
  final seen = ref.watch(seenNotificationIdsProvider);
  return items.where((n) => !seen.contains(n.id)).length;
});
