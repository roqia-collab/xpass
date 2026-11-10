import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

/// Palette alignée sur les portails : encre, pierre, accent rouge.
class XColors {
  static const cream = Color(0xFFF3F4F7);
  static const creamDark = Color(0xFFE7E9EF);
  static const navy = Color(0xFF0A0F1C);
  static const navyMuted = Color(0xFF5C6478);

  /// Accent des boutons (blanc dessus). Les textes longs restent en encre.
  static const coral = Color(0xFFE1331C);
  static const coralDeep = coral;
  static const coralBrand = Color(0xFFFF3B1F);
  static const lavender = Color(0xFFE6E9F0);
  static const lavenderStrong = Color(0xFFB8C0D4);
  static const lavenderText = Color(0xFF3D4A6B);
  static const mint = Color(0xFFD8EDE3);
  static const mintText = Color(0xFF1F6B4A);
  static const line = Color(0xFFD5D8E0);
  static const white = Colors.white;
}

/// Icônes au trait des maquettes (famille Lucide).
class XIcons {
  static const credits = LucideIcons.database;
  static const explore = LucideIcons.compass;
  static const bookings = LucideIcons.calendar;
  static const profile = LucideIcons.settings;
  static const calendar = LucideIcons.calendar;
  static const clock = LucideIcons.clock;
  static const pin = LucideIcons.mapPin;
  static const people = LucideIcons.users;
  static const grid = LucideIcons.layoutGrid;
  static const gift = LucideIcons.gift;
  static const directions = LucideIcons.navigation;
  static const locate = LucideIcons.locateFixed;
  static const map = LucideIcons.map;
  static const search = LucideIcons.search;
  static const heart = LucideIcons.heart;
  static const bell = LucideIcons.bell;
}

class XRadius {
  static const card = 20.0;
  static const chip = 28.0;
}

/// Désactivé dans les tests (pas de téléchargement de polices).
bool useGoogleFonts = true;

TextStyle serif(double size, {Color color = XColors.navy, FontWeight weight = FontWeight.w700, double? height}) {
  final style = TextStyle(fontSize: size, color: color, fontWeight: weight, height: height ?? 1.05, letterSpacing: -0.4);
  return useGoogleFonts ? GoogleFonts.syne(textStyle: style) : style;
}

ThemeData buildTheme() {
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: XColors.coral,
      primary: XColors.coral,
      onPrimary: Colors.white,
      secondary: XColors.navy,
      surface: XColors.cream,
      onSurface: XColors.navy,
    ),
    scaffoldBackgroundColor: XColors.cream,
  );
  final text = (useGoogleFonts ? GoogleFonts.manropeTextTheme(base.textTheme) : base.textTheme)
      .apply(bodyColor: XColors.navy, displayColor: XColors.navy);
  return base.copyWith(
    textTheme: text,
    appBarTheme: const AppBarTheme(backgroundColor: XColors.cream, foregroundColor: XColors.navy, elevation: 0),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: XColors.coral,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(56),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(XRadius.chip)),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
      ),
    ),
    snackBarTheme: const SnackBarThemeData(backgroundColor: XColors.navy, behavior: SnackBarBehavior.floating),
    pageTransitionsTheme: const PageTransitionsTheme(builders: {
      TargetPlatform.android: FadeUpwardsPageTransitionsBuilder(),
      TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
      TargetPlatform.macOS: FadeUpwardsPageTransitionsBuilder(),
      TargetPlatform.windows: FadeUpwardsPageTransitionsBuilder(),
      TargetPlatform.linux: FadeUpwardsPageTransitionsBuilder(),
    }),
  );
}
