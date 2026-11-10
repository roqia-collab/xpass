import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:xpass_mobile/core/l10n.dart';

import 'package:xpass_mobile/core/theme.dart';
import 'package:xpass_mobile/features/catalog/models.dart';
import 'package:xpass_mobile/features/explore/location_cards.dart';

/// Rend chaque carte avec une réponse réelle de l'API (fixture exportée du seed de démo).
void main() {
  setUpAll(() => useGoogleFonts = false);

  final page = LocationPage.fromJson(
      jsonDecode(File('test/fixtures/locations_paris.json').readAsStringSync()) as Map<String, dynamic>);

  testWidgets('toutes les cartes se mettent en page sans erreur', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);

    for (final l in page.items) {
      await tester.pumpWidget(MaterialApp(
        locale: const Locale('fr'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(
          body: ListView(children: [
            HorizontalLocationCard(location: l, showBookButton: true),
            PhotoLocationCard(location: l),
          ]),
        ),
      ));
      final error = tester.takeException();
      if (error != null) fail('${l.slug}: ${error is FlutterError ? error.toStringDeep() : error}');
      expect(find.text(l.name), findsNWidgets(2));
    }
  });
}
