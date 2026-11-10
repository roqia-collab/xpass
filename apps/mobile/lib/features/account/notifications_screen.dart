import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/api_client.dart';
import '../../core/auth.dart';
import '../../core/format.dart' as fmt;
import '../../core/l10n.dart';
import '../../core/push_notifications.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import 'account_repository.dart';

const _pushPrefKey = 'xpass_notify_push';

final pushEnabledProvider = FutureProvider<bool>((ref) async {
  return (await const FlutterSecureStorage().read(key: _pushPrefKey)) == '1';
});

/// Affiche une alerte navigateur pour chaque nouvelle notification, si l’utilisateur l’a autorisée.
class NotificationBridge extends ConsumerStatefulWidget {
  const NotificationBridge({super.key, required this.child});
  final Widget child;

  @override
  ConsumerState<NotificationBridge> createState() => _NotificationBridgeState();
}

class _NotificationBridgeState extends ConsumerState<NotificationBridge> {
  final _announced = <String>{};

  @override
  Widget build(BuildContext context) {
    ref.listen(notificationsProvider, (_, next) async {
      final items = next.valueOrNull;
      if (items == null || items.isEmpty) return;
      if (await const FlutterSecureStorage().read(key: _pushPrefKey) != '1') return;
      if (await PushNotifications.permission() != 'granted') return;
      for (final n in items.reversed) {
        if (_announced.add(n.id)) PushNotifications.show(title: n.title, body: n.body);
      }
    });
    return widget.child;
  }
}

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = context.l10n;
    final list = ref.watch(notificationsProvider);
    return Scaffold(
      body: SafeArea(
        child: list.when(
          loading: () => const LoadingView(),
          error: (e, _) => ErrorView(error: e, onRetry: () => ref.invalidate(notificationsProvider)),
          data: (items) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              ref.read(seenNotificationIdsProvider.notifier).state = {for (final n in items) n.id};
            });
            return ListView(padding: const EdgeInsets.fromLTRB(20, 8, 20, 32), children: [
              Row(children: [
                IconButton(
                  tooltip: l.back,
                  onPressed: () => context.canPop() ? context.pop() : context.go('/profil'),
                  icon: const Icon(Icons.arrow_back),
                ),
                const XpassLogo(height: 26),
              ]),
              const SizedBox(height: 12),
              Text(l.notifications, style: serif(38)),
              const SizedBox(height: 6),
              Text(l.notificationsSubtitle, style: const TextStyle(fontSize: 16, color: XColors.navyMuted)),
              const SizedBox(height: 18),
              if (items.isEmpty)
                EmptyView(message: l.noNotifications)
              else
                for (final n in items)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Material(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(22),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(22),
                        onTap: () => context.push(n.route),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            _kindIcon(n.kind),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Text(n.title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                                const SizedBox(height: 4),
                                Text(n.body, style: const TextStyle(color: XColors.navyMuted, height: 1.35)),
                                const SizedBox(height: 6),
                                Text(fmt.shortDate(n.createdAt),
                                    style: const TextStyle(color: XColors.navyMuted, fontSize: 12)),
                              ]),
                            ),
                            const Icon(Icons.chevron_right, color: XColors.navyMuted),
                          ]),
                        ),
                      ),
                    ),
                  ),
            ]);
          },
        ),
      ),
    );
  }

  Widget _kindIcon(String kind) {
    final (icon, color) = switch (kind) {
      'booking.confirmed' => (LucideIcons.calendar, XColors.mint),
      'booking.cancelled' => (LucideIcons.calendar, const Color(0xFFFDE8E4)),
      'booking.redeemed' => (LucideIcons.heart, XColors.mint),
      'invoice.paid' => (LucideIcons.crown, XColors.lavender),
      'payment.refused' => (LucideIcons.bell, const Color(0xFFFDE8E4)),
      _ => (LucideIcons.bell, XColors.lavender),
    };
    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(12)),
      child: Icon(icon, size: 18, color: XColors.navy),
    );
  }
}

Future<void> togglePushNotifications(WidgetRef ref, bool enabled) async {
  final storage = const FlutterSecureStorage();
  if (!enabled) {
    await storage.write(key: _pushPrefKey, value: '0');
    ref.invalidate(pushEnabledProvider);
    return;
  }
  if (!await PushNotifications.isSupported()) {
    await storage.write(key: _pushPrefKey, value: '1');
    ref.invalidate(pushEnabledProvider);
    return;
  }
  final ok = await PushNotifications.request();
  await storage.write(key: _pushPrefKey, value: ok ? '1' : '0');
  ref.invalidate(pushEnabledProvider);
  if (ok) {
    final session = ref.read(authProvider).valueOrNull;
    if (session != null) {
      try {
        await ref.read(accountRepositoryProvider).registerWebDevice(session.email);
      } on ApiException {
        // L’alerte navigateur reste active même si l’enregistrement serveur échoue.
      }
    }
  }
}
