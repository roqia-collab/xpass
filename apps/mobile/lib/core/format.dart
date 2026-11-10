/// Formats français sans dépendance supplémentaire.
library;

const _days = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche'];
const _shortDays = ['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.'];
const _months = [
  'janvier',
  'février',
  'mars',
  'avril',
  'mai',
  'juin',
  'juillet',
  'août',
  'septembre',
  'octobre',
  'novembre',
  'décembre',
];

String hhmm(DateTime d) => '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';

/// « Aujourd'hui à 18h30 », « Demain à 10:00 », « jeudi 12 novembre à 16:00 ».
/// [local] est l'heure murale de l'établissement (champ `local_start` de l'API), sans conversion.
String slotLabel(DateTime local, {DateTime? now}) {
  final today = _dateOnly(now ?? DateTime.now());
  final day = _dateOnly(local);
  final diff = day.difference(today).inDays;
  if (diff == 0) return "Aujourd'hui à ${hhmm(local)}";
  if (diff == 1) return 'Demain à ${hhmm(local)}';
  return '${_days[local.weekday - 1]} ${local.day} ${_months[local.month - 1]} à ${hhmm(local)}';
}

String credits(int n) => '$n crédit${n > 1 ? 's' : ''}';

String duration(int minutes) {
  if (minutes < 60) return '$minutes min';
  final h = minutes ~/ 60;
  final m = minutes % 60;
  return m == 0 ? '$h h' : '$h h ${m.toString().padLeft(2, '0')}';
}

String distance(int? meters) {
  if (meters == null) return '';
  final rounded = (meters / 50).round() * 50;
  if (rounded < 1000) return '$rounded m';
  return '${(meters / 1000).toStringAsFixed(1).replaceAll('.', ',')} km';
}

// UTC pour que la différence en jours ne soit pas faussée par les changements d'heure.
DateTime _dateOnly(DateTime d) => DateTime.utc(d.year, d.month, d.day);

/// Jour calendaire local, sans l’heure.
DateTime dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);

/// « ven. 7 » — pastilles de dates (Aujourd’hui / Demain restent dans la l10n).
String weekdayShortDay(DateTime d) => '${_shortDays[d.weekday - 1]} ${d.day}';

/// « jeudi 12 novembre 2026 »
String longDate(DateTime d) => '${_days[d.weekday - 1]} ${d.day} ${_months[d.month - 1]} ${d.year}';

/// « 11 novembre »
String dayMonth(DateTime d) => '${d.day} ${_months[d.month - 1]}';

const _shortMonths = [
  'janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.', //
];

/// « 12 nov. 2026 »
String shortDate(DateTime d) => '${d.day} ${_shortMonths[d.month - 1]} ${d.year}';

/// Montant en unités mineures : « 100,00 € ». Jamais confondu avec des crédits.
String money(int minor, String currency) {
  final sign = minor < 0 ? '−' : '';
  final abs = minor.abs();
  final units = abs ~/ 100;
  final grouped = units.toString().replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => ' ');
  final symbol = currency == 'EUR' ? '€' : currency;
  return '$sign$grouped,${(abs % 100).toString().padLeft(2, '0')} $symbol';
}
