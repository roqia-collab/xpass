import 'push_notifications_stub.dart' if (dart.library.js_interop) 'push_notifications_web.dart' as impl;

/// Notifications du navigateur (web). Sur mobile natif, le canal Firebase reste à brancher.
class PushNotifications {
  static Future<bool> isSupported() => impl.isSupported();
  static Future<String> permission() => impl.permission();
  static Future<bool> request() => impl.request();
  static void show({required String title, required String body}) => impl.show(title: title, body: body);
}
