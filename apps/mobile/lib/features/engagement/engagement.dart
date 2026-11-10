import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/auth.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../account/login_sheet.dart';

/// Relation client ↔ établissement : favoris, messagerie par réservation, avis notés.

class ChatMessage {
  const ChatMessage(
      {required this.id, required this.mine, required this.body, required this.createdAt, this.senderKind = 'customer'});
  final String id;
  final bool mine;
  final String body;
  final DateTime createdAt;
  final String senderKind;
  bool get isAuto => senderKind == 'system';

  factory ChatMessage.fromJson(Map<String, dynamic> j) => ChatMessage(
      id: j['id'] as String,
      mine: j['mine'] as bool,
      body: j['body'] as String,
      createdAt: DateTime.parse(j['created_at'] as String).toLocal(),
      senderKind: j['sender_kind'] as String? ?? (j['mine'] as bool ? 'customer' : 'partner'));
}

class Thread {
  const Thread(
      {required this.canWrite, required this.closedReason, required this.locationName, required this.messages});
  final bool canWrite;
  final String? closedReason;
  final String locationName;
  final List<ChatMessage> messages;

  factory Thread.fromJson(Map<String, dynamic> j) => Thread(
        canWrite: j['can_write'] as bool,
        closedReason: j['closed_reason'] as String?,
        locationName: j['location_name'] as String,
        messages: [for (final m in j['messages'] as List) ChatMessage.fromJson(m as Map<String, dynamic>)],
      );
}

class ReviewItem {
  const ReviewItem({required this.id, required this.rating, this.comment, required this.author, this.reply});
  final String id;
  final int rating;
  final String? comment;
  final String author;
  final String? reply;

  factory ReviewItem.fromJson(Map<String, dynamic> j) => ReviewItem(
      id: j['id'] as String,
      rating: j['rating'] as int,
      comment: j['comment'] as String?,
      author: j['author'] as String,
      reply: j['partner_reply'] as String?);
}

class Reviews {
  const Reviews({this.average, required this.count, required this.items});
  final double? average;
  final int count;
  final List<ReviewItem> items;
}

class FavoritePlace {
  const FavoritePlace(
      {required this.id,
      required this.slug,
      required this.name,
      required this.kind,
      required this.district,
      this.cover});
  final String id;
  final String slug;
  final String name;
  final String kind;
  final String district;
  final String? cover;
}

class EngagementRepository {
  EngagementRepository(this._public, this._auth);
  final Dio _public;
  final Dio _auth;

  Future<T> _call<T>(Future<Response<dynamic>> Function() send, T Function(dynamic) parse) async {
    try {
      return parse((await send()).data);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  Future<Thread> thread(String bookingId) =>
      _call(() => _auth.get('/bookings/$bookingId/messages'), (d) => Thread.fromJson(d as Map<String, dynamic>));
  Future<void> send(String bookingId, String body) =>
      _call(() => _auth.post('/bookings/$bookingId/messages', data: {'body': body}), (_) {});
  Future<List<FavoritePlace>> favorites() => _call(
      () => _auth.get('/me/favorites'),
      (d) => [
            for (final f in d as List)
              FavoritePlace(
                id: f['location_id'] as String,
                slug: f['slug'] as String,
                name: f['name'] as String,
                kind: f['kind_label'] as String,
                district: f['district_label'] as String,
                cover: f['cover_image_key'] as String?,
              )
          ]);
  Future<void> setFavorite(String locationId, bool on) =>
      _call(() => on ? _auth.put('/me/favorites/$locationId') : _auth.delete('/me/favorites/$locationId'), (_) {});
  Future<ReviewItem?> myReview(String bookingId) => _call(() => _auth.get('/bookings/$bookingId/review'),
      (d) => d == null ? null : ReviewItem.fromJson(d as Map<String, dynamic>));
  Future<void> review(String bookingId, int rating, String comment) => _call(
      () => _auth
          .post('/bookings/$bookingId/review', data: {'rating': rating, if (comment.isNotEmpty) 'comment': comment}),
      (_) {});
  Future<Reviews> reviews(String slug) => _call(
      () => _public.get('/catalog/locations/$slug/reviews'),
      (d) => Reviews(
            average: (d['average'] as num?)?.toDouble(),
            count: d['count'] as int,
            items: [for (final r in d['items'] as List) ReviewItem.fromJson(r as Map<String, dynamic>)],
          ));
}

final engagementRepositoryProvider =
    Provider((ref) => EngagementRepository(ref.watch(rawDioProvider), ref.watch(authDioProvider)));

final favoritesProvider = FutureProvider.autoDispose<List<FavoritePlace>>((ref) async {
  if (await ref.watch(authProvider.future) == null) return const [];
  return ref.watch(engagementRepositoryProvider).favorites();
});

/// État affiché tout de suite au toucher du cœur, avant la réponse du serveur (annulé en cas d'échec).
final favoriteOverridesProvider = StateProvider<Map<String, bool>>((ref) => const {});

final threadProvider = FutureProvider.autoDispose
    .family<Thread, String>((ref, bookingId) => ref.watch(engagementRepositoryProvider).thread(bookingId));

final reviewsProvider = FutureProvider.autoDispose
    .family<Reviews, String>((ref, slug) => ref.watch(engagementRepositoryProvider).reviews(slug));

final myReviewProvider = FutureProvider.autoDispose
    .family<ReviewItem?, String>((ref, bookingId) => ref.watch(engagementRepositoryProvider).myReview(bookingId));

// ---------------------------------------------------------------- favoris

/// Cœur des maquettes : ajoute ou retire l'établissement des favoris (connexion demandée si besoin).
class FavoriteButton extends ConsumerWidget {
  const FavoriteButton({super.key, required this.locationId, required this.name});
  final String locationId;
  final String name;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final favs = ref.watch(favoritesProvider).valueOrNull ?? const [];
    final on = ref.watch(favoriteOverridesProvider)[locationId] ?? favs.any((f) => f.id == locationId);
    return IconButton.filledTonal(
      style: IconButton.styleFrom(backgroundColor: Colors.white.withValues(alpha: 0.9)),
      tooltip: on ? 'Retirer $name des favoris' : 'Ajouter $name aux favoris',
      isSelected: on,
      onPressed: () async {
        if (!await ensureSignedIn(context, ref)) return;
        // Réponse immédiate : le cœur change tout de suite, la requête part ensuite.
        HapticFeedback.selectionClick();
        final overrides = ref.read(favoriteOverridesProvider.notifier);
        overrides.state = {...overrides.state, locationId: !on};
        try {
          await ref.read(engagementRepositoryProvider).setFavorite(locationId, !on);
          ref.invalidate(favoritesProvider);
        } catch (e) {
          overrides.state = {...overrides.state}..remove(locationId);
          if (context.mounted) {
            ScaffoldMessenger.of(context)
                .showSnackBar(const SnackBar(content: Text('Favori non enregistré : vérifiez votre connexion.')));
          }
        }
      },
      icon: Icon(on ? Icons.favorite : Icons.favorite_border, color: on ? XColors.coral : XColors.navy),
    );
  }
}

class FavoritesScreen extends ConsumerWidget {
  const FavoritesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final favs = ref.watch(favoritesProvider);
    return Scaffold(
      appBar: AppBar(title: Text('Mes favoris', style: serif(26))),
      body: favs.when(
        loading: () => const LoadingView(),
        error: (e, _) => ErrorView(error: e, onRetry: () => ref.invalidate(favoritesProvider)),
        data: (all) {
          // Un favori retiré disparaît immédiatement de la liste.
          final overrides = ref.watch(favoriteOverridesProvider);
          final list = all.where((f) => overrides[f.id] != false).toList();
          return list.isEmpty
              ? const EmptyView(message: 'Touchez le cœur d’un établissement pour le retrouver ici.')
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: list.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (_, i) {
                    final f = list[i];
                    return Material(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(XRadius.card),
                      clipBehavior: Clip.antiAlias,
                      child: InkWell(
                        onTap: () => context.push('/explore/lieu/${f.slug}'),
                        child: Row(children: [
                          SizedBox(width: 96, height: 80, child: MediaImage(imageKey: f.cover)),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Text(f.name, style: serif(20), maxLines: 1, overflow: TextOverflow.ellipsis),
                              Text('${f.kind} · ${f.district}', style: const TextStyle(color: XColors.navyMuted)),
                            ]),
                          ),
                          FavoriteButton(locationId: f.id, name: f.name),
                        ]),
                      ),
                    );
                  },
                );
        },
      ),
    );
  }
}

// ---------------------------------------------------------------- messagerie

/// Conversation avec l'établissement au sujet d'une réservation.
class MessagesScreen extends ConsumerStatefulWidget {
  const MessagesScreen({super.key, required this.bookingId});
  final String bookingId;

  @override
  ConsumerState<MessagesScreen> createState() => _MessagesScreenState();
}

class _MessagesScreenState extends ConsumerState<MessagesScreen> {
  final _text = TextEditingController();
  bool _sending = false;
  Timer? _poll;
  // Messages affichés dès l'envoi, en attente de confirmation du serveur.
  final List<ChatMessage> _pending = [];

  @override
  void initState() {
    super.initState();
    _poll = Timer.periodic(const Duration(seconds: 8), (_) {
      if (mounted) ref.invalidate(threadProvider(widget.bookingId));
    });
  }

  @override
  void dispose() {
    _poll?.cancel();
    _text.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final body = _text.text.trim();
    if (body.isEmpty) return;
    final local = ChatMessage(
        id: 'local-${DateTime.now().microsecondsSinceEpoch}', mine: true, body: body, createdAt: DateTime.now());
    // Réponse immédiate : le message apparaît et le champ se vide avant la réponse du serveur.
    HapticFeedback.lightImpact();
    setState(() {
      _pending.add(local);
      _sending = true;
    });
    _text.clear();
    try {
      await ref.read(engagementRepositoryProvider).send(widget.bookingId, body);
      ref.invalidate(threadProvider(widget.bookingId));
      await ref.read(threadProvider(widget.bookingId).future);
    } catch (e) {
      // Échec : le message est retiré et le texte rendu pour un nouvel essai.
      if (_text.text.isEmpty) _text.text = body;
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Message non envoyé : vérifiez votre connexion et réessayez.')));
      }
    } finally {
      if (mounted) {
        setState(() {
          _pending.remove(local);
          _sending = _pending.isNotEmpty;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final thread = ref.watch(threadProvider(widget.bookingId));
    return Scaffold(
      appBar: AppBar(title: Text(thread.valueOrNull?.locationName ?? 'Messages', style: serif(24))),
      body: thread.when(
        skipLoadingOnReload: true,
        skipLoadingOnRefresh: true,
        loading: () => const LoadingView(),
        error: (e, _) => ErrorView(error: e, onRetry: () => ref.invalidate(threadProvider(widget.bookingId))),
        data: (t) => Column(children: [
          Expanded(
            child: t.messages.isEmpty && _pending.isEmpty
                ? const EmptyView(message: 'Une question sur votre réservation ? Écrivez à l’établissement.')
                : ListView(
                    padding: const EdgeInsets.all(16),
                    reverse: true,
                    children: [
                      for (final m in [...t.messages, ..._pending].reversed)
                        Align(
                          alignment: m.isAuto
                              ? Alignment.center
                              : m.mine
                                  ? AlignmentDirectional.centerEnd
                                  : AlignmentDirectional.centerStart,
                          child: Container(
                            margin: const EdgeInsets.only(bottom: 8),
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                            constraints: const BoxConstraints(maxWidth: 300),
                            decoration: BoxDecoration(
                              color: m.isAuto
                                  ? XColors.mint
                                  : m.mine
                                      ? XColors.lavender
                                      : Colors.white,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: XColors.line),
                            ),
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              if (m.isAuto)
                                const Text('Message automatique',
                                    style: TextStyle(fontSize: 11, color: XColors.navyMuted)),
                              Text(m.body),
                              const SizedBox(height: 4),
                              if (_pending.contains(m))
                                const Text('Envoi…', style: TextStyle(fontSize: 11, color: XColors.navyMuted))
                              else
                                Text(
                                    '${m.createdAt.day.toString().padLeft(2, '0')}/${m.createdAt.month.toString().padLeft(2, '0')} '
                                    '${m.createdAt.hour.toString().padLeft(2, '0')}:${m.createdAt.minute.toString().padLeft(2, '0')}',
                                    style: const TextStyle(fontSize: 11, color: XColors.navyMuted)),
                            ]),
                          ),
                        ),
                    ],
                  ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 6, 12, 12),
              child: t.canWrite
                  ? Row(children: [
                      Expanded(
                        child: TextField(
                          controller: _text,
                          minLines: 1,
                          maxLines: 4,
                          maxLength: 2000,
                          decoration: InputDecoration(
                            hintText: 'Votre message…',
                            counterText: '',
                            filled: true,
                            fillColor: Colors.white,
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(20)),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton.filled(
                        tooltip: 'Envoyer',
                        style: IconButton.styleFrom(backgroundColor: XColors.coral),
                        onPressed: _sending ? null : _send,
                        icon: const Icon(Icons.send, color: Colors.white),
                      ),
                    ])
                  : Text(t.closedReason ?? '', style: const TextStyle(color: XColors.navyMuted)),
            ),
          ),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------- avis notés

String stars(int n) => '★' * n + '☆' * (5 - n);

/// Note de 1 à 5 et commentaire, une fois la prestation consommée (affiché sur le reçu).
class ReviewForm extends ConsumerStatefulWidget {
  const ReviewForm({super.key, required this.bookingId});
  final String bookingId;

  @override
  ConsumerState<ReviewForm> createState() => _ReviewFormState();
}

class _ReviewFormState extends ConsumerState<ReviewForm> {
  int _rating = 0;
  final _comment = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _comment.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final existing = ref.watch(myReviewProvider(widget.bookingId));
    return existing.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
      data: (r) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(XRadius.card),
            border: Border.all(color: XColors.line)),
        child: r != null
            ? Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Votre avis', style: serif(22)),
                Text(stars(r.rating), style: const TextStyle(color: XColors.coral, fontSize: 22)),
                if (r.comment != null) Text(r.comment!),
                if (r.reply != null) ...[
                  const SizedBox(height: 8),
                  Text('Réponse de l’établissement : ${r.reply}', style: const TextStyle(color: XColors.navyMuted)),
                ],
              ])
            : Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Notez votre prestation', style: serif(22)),
                const SizedBox(height: 6),
                Row(children: [
                  for (var i = 1; i <= 5; i++)
                    IconButton(
                      tooltip: '$i sur 5',
                      onPressed: () => setState(() => _rating = i),
                      icon: Icon(i <= _rating ? Icons.star : Icons.star_border, color: XColors.coral, size: 32),
                    ),
                ]),
                TextField(
                  controller: _comment,
                  maxLines: 3,
                  maxLength: 1000,
                  decoration: const InputDecoration(hintText: 'Un mot sur votre expérience (facultatif)'),
                ),
                if (_error != null) Text(_error!, style: const TextStyle(color: Color(0xFFB42318))),
                const SizedBox(height: 6),
                FilledButton(
                  onPressed: _rating == 0 || _busy
                      ? null
                      : () async {
                          setState(() {
                            _busy = true;
                            _error = null;
                          });
                          try {
                            await ref
                                .read(engagementRepositoryProvider)
                                .review(widget.bookingId, _rating, _comment.text.trim());
                            ref.invalidate(myReviewProvider(widget.bookingId));
                          } catch (e) {
                            setState(() => _error = e.toString());
                          } finally {
                            if (mounted) setState(() => _busy = false);
                          }
                        },
                  child: Text(_busy ? 'Envoi…' : 'Publier mon avis'),
                ),
                const Text('Votre avis est public, signé de votre prénom et de l’initiale de votre nom.',
                    style: TextStyle(fontSize: 12, color: XColors.navyMuted)),
              ]),
      ),
    );
  }
}

/// Avis publiés sur la fiche de l'établissement.
class LocationReviews extends ConsumerWidget {
  const LocationReviews({super.key, required this.slug});
  final String slug;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final reviews = ref.watch(reviewsProvider(slug)).valueOrNull;
    if (reviews == null || reviews.count == 0) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const SizedBox(height: 20),
      Row(children: [
        Text('Avis', style: serif(24)),
        const SizedBox(width: 10),
        Text('${reviews.average?.toStringAsFixed(1).replaceAll('.', ',')} / 5 · ${reviews.count} avis',
            style: const TextStyle(fontWeight: FontWeight.w600)),
      ]),
      for (final r in reviews.items.take(5))
        Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${stars(r.rating)}  ${r.author}', style: const TextStyle(color: XColors.coral)),
            if (r.comment != null) Text(r.comment!),
            if (r.reply != null)
              Text('Réponse : ${r.reply}', style: const TextStyle(color: XColors.navyMuted, fontSize: 13)),
          ]),
        ),
    ]);
  }
}
