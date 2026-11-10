import 'package:flutter/widgets.dart';

import '../l10n/gen/app_localizations.dart';

export '../l10n/gen/app_localizations.dart';

/// Textes de l'interface dans la langue choisie (fr, en, ar — l'arabe s'affiche de droite à gauche).
extension L10nContext on BuildContext {
  AppLocalizations get l10n => AppLocalizations.of(this);
}
