import 'dart:js_interop';

import 'package:web/web.dart' as web;

Future<bool> isSupported() async => true;

Future<String> permission() async => web.Notification.permission;

Future<bool> request() async {
  final result = await web.Notification.requestPermission().toDart;
  return result.toDart == 'granted';
}

void show({required String title, required String body}) {
  if (web.Notification.permission != 'granted') return;
  web.Notification(title, web.NotificationOptions(body: body));
}
