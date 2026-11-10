import 'dart:math';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/auth.dart';
import 'models.dart';

/// Clé d'idempotence aléatoire (128 bits). Une même action réessayée réutilise sa clé.
String newIdempotencyKey() {
  final r = Random.secure();
  return List.generate(16, (_) => r.nextInt(256).toRadixString(16).padLeft(2, '0')).join();
}

class BookingRepository {
  BookingRepository(this._public, this._auth);
  final Dio _public;
  final Dio _auth;

  Future<T> _call<T>(Future<Response<dynamic>> Function() send, T Function(dynamic) parse) async {
    try {
      return parse((await send()).data);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  Future<Availability> availability(String offerId, {String? date}) => _call(
      () => _public.get('/catalog/offers/$offerId/availability', queryParameters: {if (date != null) 'date': date}),
      (d) => Availability.fromJson(d as Map<String, dynamic>));

  Future<Booking> hold({
    required String offerId,
    required String startsAt,
    required int partySize,
    String? resourceId,
    int? expectedPriceCredits,
    required String idempotencyKey,
  }) =>
      _call(
        () => _auth.post('/bookings',
            data: {
              'offer_id': offerId,
              'starts_at': startsAt,
              'party_size': partySize,
              if (resourceId != null) 'resource_id': resourceId,
              // Prix affiché : si le prix du créneau a changé entre-temps, le serveur refuse (price_changed).
              if (expectedPriceCredits != null) 'expected_price_credits': expectedPriceCredits,
            },
            options: Options(headers: {'Idempotency-Key': idempotencyKey})),
        (d) => Booking.fromJson(d as Map<String, dynamic>),
      );

  Future<Booking> confirm(String id, String idempotencyKey) => _call(
      () => _auth.post('/bookings/$id/confirm', options: Options(headers: {'Idempotency-Key': idempotencyKey})),
      (d) => Booking.fromJson(d as Map<String, dynamic>));

  Future<Booking> cancel(String id, String idempotencyKey) => _call(
      () => _auth.post('/bookings/$id/cancel', options: Options(headers: {'Idempotency-Key': idempotencyKey})),
      (d) => Booking.fromJson(d as Map<String, dynamic>));

  Future<Booking> get(String id) =>
      _call(() => _auth.get('/bookings/$id'), (d) => Booking.fromJson(d as Map<String, dynamic>));

  Future<BookingList> list(String scope) => _call(() => _auth.get('/bookings', queryParameters: {'scope': scope}),
      (d) => BookingList.fromJson(d as Map<String, dynamic>));

  Future<PassInfo> issuePass(String id) =>
      _call(() => _auth.post('/bookings/$id/pass'), (d) => PassInfo.fromJson(d as Map<String, dynamic>));

  Future<ReceiptInfo> receipt(String id) =>
      _call(() => _auth.get('/bookings/$id/receipt'), (d) => ReceiptInfo.fromJson(d as Map<String, dynamic>));

  /// Fichier iCalendar (sans jeton QR) généré par le serveur.
  Future<String> calendarIcs(String id) => _call(
      () => _auth.get<String>('/bookings/$id/calendar.ics', options: Options(responseType: ResponseType.plain)),
      (d) => d as String);

  Future<List<Plan>> plans() => _call(() => _public.get('/subscription/plans'),
      (d) => [for (final p in d as List) Plan.fromJson(p as Map<String, dynamic>)]);

  Future<SubscriptionInfo> subscription() =>
      _call(() => _auth.get('/subscription'), (d) => SubscriptionInfo.fromJson(d as Map<String, dynamic>));

  /// Adresse du paiement hébergé. Aucun crédit n'est ajouté ici : uniquement après confirmation serveur.
  Future<String> checkout(String planCode, String idempotencyKey) => _call(
      () => _auth.post('/subscription/checkout',
          data: {'plan_code': planCode}, options: Options(headers: {'Idempotency-Key': idempotencyKey})),
      (d) => (d as Map)['checkout_url'] as String);

  Future<SubscriptionInfo> setAutoRenew(bool enabled) => _call(
      () => _auth.post('/subscription/auto-renew', data: {'enabled': enabled}),
      (d) => SubscriptionInfo.fromJson(d as Map<String, dynamic>));

  /// Nouvelle formule au prochain renouvellement (le mois en cours ne change pas).
  Future<SubscriptionInfo> changePlan(String planCode) => _call(
      () => _auth.post('/subscription/change-plan', data: {'plan_code': planCode}),
      (d) => SubscriptionInfo.fromJson(d as Map<String, dynamic>));

  /// Invitations « avantage salarié » liées à l'adresse e-mail du compte connecté.
  Future<List<(String id, String organization)>> employerInvitations() => _call(
      () => _auth.get('/me/employer-invitations'),
      (d) => [for (final i in d as List) ((i as Map)['id'] as String, i['organization_name'] as String)]);

  Future<void> acceptEmployerInvitation(String id) =>
      _call(() => _auth.post('/me/employer-invitations/$id/accept'), (_) {});

  Future<void> openDispute(String bookingId, String reason) =>
      _call(() => _auth.post('/bookings/$bookingId/disputes', data: {'reason': reason}), (_) {});

  Future<List<DisputeInfo>> disputes(String bookingId) => _call(() => _auth.get('/bookings/$bookingId/disputes'),
      (d) => [for (final x in d as List) DisputeInfo.fromJson(x as Map<String, dynamic>)]);

  Future<WalletSummary> wallet() =>
      _call(() => _auth.get('/wallet'), (d) => WalletSummary.fromJson(d as Map<String, dynamic>));

  Future<List<HistoryEntry>> history() => _call(() => _auth.get('/wallet/history', queryParameters: {'limit': 10}),
      (d) => [for (final e in d as List) HistoryEntry.fromJson(e as Map<String, dynamic>)]);
}

final bookingRepositoryProvider =
    Provider((ref) => BookingRepository(ref.watch(rawDioProvider), ref.watch(authDioProvider)));

final availabilityProvider = FutureProvider.autoDispose.family<Availability, (String, String?)>(
    (ref, key) => ref.watch(bookingRepositoryProvider).availability(key.$1, date: key.$2));

/// Attend la restauration de la session avant tout appel protégé (ouverture directe d'un lien).
Future<void> _signedIn(Ref ref) async {
  if (await ref.watch(authProvider.future) == null) {
    throw ApiException('Connectez-vous pour voir cette réservation.', statusCode: 401);
  }
}

final bookingProvider = FutureProvider.autoDispose.family<Booking, String>((ref, id) async {
  await _signedIn(ref);
  return ref.watch(bookingRepositoryProvider).get(id);
});

final receiptProvider = FutureProvider.autoDispose.family<ReceiptInfo, String>((ref, id) async {
  await _signedIn(ref);
  return ref.watch(bookingRepositoryProvider).receipt(id);
});

final bookingListProvider = FutureProvider.autoDispose.family<BookingList, String>((ref, scope) async {
  await _signedIn(ref);
  return ref.watch(bookingRepositoryProvider).list(scope);
});

final walletProvider = FutureProvider.autoDispose<WalletSummary?>((ref) async {
  final session = await ref.watch(authProvider.future);
  if (session == null) return null;
  return ref.watch(bookingRepositoryProvider).wallet();
});

final walletHistoryProvider = FutureProvider.autoDispose<List<HistoryEntry>>((ref) async {
  final session = await ref.watch(authProvider.future);
  if (session == null) return const [];
  return ref.watch(bookingRepositoryProvider).history();
});

/// À appeler après toute commande qui modifie crédits ou réservations.
void invalidateBookingData(WidgetRef ref) {
  ref.invalidate(walletProvider);
  ref.invalidate(walletHistoryProvider);
  ref.invalidate(bookingListProvider);
}

final plansProvider = FutureProvider.autoDispose<List<Plan>>((ref) => ref.watch(bookingRepositoryProvider).plans());

final subscriptionProvider = FutureProvider.autoDispose<SubscriptionInfo>((ref) async {
  await _signedIn(ref);
  return ref.watch(bookingRepositoryProvider).subscription();
});

final employerInvitationsProvider = FutureProvider.autoDispose<List<(String, String)>>((ref) async {
  final session = await ref.watch(authProvider.future);
  if (session == null) return const [];
  return ref.watch(bookingRepositoryProvider).employerInvitations();
});

final disputesProvider = FutureProvider.autoDispose.family<List<DisputeInfo>, String>((ref, bookingId) async {
  await _signedIn(ref);
  return ref.watch(bookingRepositoryProvider).disputes(bookingId);
});
