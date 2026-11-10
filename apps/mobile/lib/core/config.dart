/// Configuration injectée au lancement :
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000 --dart-define=MEDIA_BASE_URL=http://10.0.2.2:8333/xpass-public
class AppConfig {
  static const apiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000');
  static const mediaBaseUrl =
      String.fromEnvironment('MEDIA_BASE_URL', defaultValue: 'http://localhost:8333/xpass-public');

  /// Fournisseur d'identité OIDC (vide = connexion de démonstration uniquement, développement).
  static const oidcIssuer = String.fromEnvironment('OIDC_ISSUER');
  static const oidcClientId = String.fromEnvironment('OIDC_CLIENT_ID', defaultValue: 'xpass-mobile');

  /// Connexion de démonstration sans mot de passe (refusée par l'API en production).
  static const devLoginEnabled = bool.fromEnvironment('DEV_LOGIN', defaultValue: false);

  /// Tuiles de carte OpenStreetMap. Développement : serveurs publics OSM (usage limité).
  /// Production : fournisseur de tuiles (MapTiler, Stadia…) avec sa clé, passé par --dart-define.
  static const mapTileUrl =
      String.fromEnvironment('MAP_TILE_URL', defaultValue: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png');

  /// Documents légaux publiés (vides tant qu'ils ne sont pas rédigés).
  static const termsUrl = String.fromEnvironment('TERMS_URL');
  static const privacyUrl = String.fromEnvironment('PRIVACY_URL');

  /// Construit l'URL publique d'un média à partir de sa clé de stockage.
  static String? mediaUrl(String? key) => key == null || key.isEmpty ? null : '$mediaBaseUrl/$key';
}
