# Applications mobiles — construction et publication

Ce document décrit ce qui est en place dans `apps/mobile` et les étapes qui demandent **vos** comptes
(Google Play, Apple, Firebase). Rien ici n'a été publié sur un store.

## État actuel

| Élément | État |
|---|---|
| Identifiant | `fr.xpass.app` (Android `applicationId`, iOS bundle id). Définitif après la première publication. |
| Nom affiché | « XPASS » (Android `android:label`, iOS `CFBundleDisplayName`). |
| Version | `pubspec.yaml` → `version: 0.1.0+1` (nom + numéro de build, à incrémenter à chaque envoi). |
| Icône | `assets/brand/app_icon.png` (+ premier plan adaptatif `app_icon_foreground.png`), générée par `flutter_launcher_icons`. |
| Écran de démarrage | `assets/brand/splash_logo.png`, généré par `flutter_native_splash`. |
| Localisation | Permission « pendant l'utilisation » (Android `ACCESS_FINE/COARSE_LOCATION`, iOS `NSLocationWhenInUseUsageDescription`). |
| APK Android | Construit avec succès (`build/app/outputs/flutter-apk/app-release.apk`, ~28 Mo), **signé avec la clé de débogage** : pour essai sur téléphone uniquement. |
| iOS | Configuré mais **jamais construit** (nécessite un Mac avec Xcode). |
| Notifications push | Côté serveur prêt (FCM HTTP v1, route `POST /api/v1/me/devices`). **Côté application non branché** : il faut un projet Firebase (voir plus bas). |

## Construire (sans Flutter installé, via Docker)

```powershell
# depuis apps/mobile
docker run --rm -v "${PWD}:/app" -v xpass_pub_cache:/root/.pub-cache -v xpass_gradle_cache:/root/.gradle -w /app `
  ghcr.io/cirruslabs/flutter:3.29.3 sh -c "flutter pub get && flutter build apk --release `
  --dart-define=API_BASE_URL=https://api.votre-domaine.fr `
  --dart-define=MEDIA_BASE_URL=https://media.votre-domaine.fr/xpass-public `
  --dart-define=OIDC_ISSUER=https://auth.votre-domaine.fr/realms/xpass"
```

Pour Google Play, construire un bundle : `flutter build appbundle --release …` (mêmes `--dart-define`).
`API_BASE_URL` ne doit **pas** se terminer par `/api/v1`.

Regénérer icône et écran de démarrage après avoir changé les images :

```powershell
dart run flutter_launcher_icons
dart run flutter_native_splash:create
```

## Signature Android (clé de publication)

1. Créer la clé **une seule fois** et la sauvegarder hors du dépôt (la perdre empêche les mises à jour si
   la signature Play n'est pas activée) :
   ```powershell
   keytool -genkey -v -keystore C:\cles\xpass-upload.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
   ```
2. Créer `apps/mobile/android/key.properties` (ignoré par Git) :
   ```properties
   storeFile=C:/cles/xpass-upload.jks
   storePassword=…
   keyAlias=upload
   keyPassword=…
   ```
3. Reconstruire : `build.gradle.kts` utilise automatiquement cette clé ; sans le fichier, la clé de débogage
   est utilisée (refusée par Google Play).

## Publication Google Play

1. Compte développeur Google Play (frais d'inscription unique, vérification d'identité).
2. Créer l'application, activer « Signature d'application par Google Play », envoyer le `.aab`.
3. Fiche : description fr/en/ar, captures, icône 512×512, politique de confidentialité
   (`https://<portails>/legal/confidentialite`, **à faire valider juridiquement avant**).
4. Questionnaire « Sécurité des données » : position (pendant l'utilisation), e-mail, nom, achats ;
   aucun partage publicitaire.
5. Test interne → test fermé (Google exige désormais des testeurs pour les nouveaux comptes) → production.

## Publication App Store

1. Compte Apple Developer (abonnement annuel) et un Mac avec Xcode.
2. `flutter build ipa --release …`, puis envoi via Xcode ou Transporter, test TestFlight.
3. Fiche App Store Connect : mêmes textes, « confidentialité de l'app », lien de suppression de compte
   (l'application propose déjà la suppression dans Profil → Paramètres).
4. Connexion : si un fournisseur social (Google…) est ajouté un jour, Apple impose aussi « Se connecter avec Apple ».

## Notifications push (à brancher)

Le serveur envoie déjà via FCM (rappel de réservation, nouveau message) aux appareils enregistrés.
Il reste, avec **votre** projet Firebase :

1. Créer un projet Firebase, y ajouter l'app Android `fr.xpass.app` et l'app iOS `fr.xpass.app`.
2. Placer `google-services.json` (Android) et `GoogleService-Info.plist` (iOS) — ne pas les publier
   publiquement ; pour iOS, téléverser la clé APNs dans Firebase.
3. Ajouter `firebase_core` et `firebase_messaging` à l'application, demander l'autorisation, puis envoyer le
   jeton à `POST /api/v1/me/devices` (`{"token": "…", "platform": "android" | "ios"}`) et le retirer à la
   déconnexion via `POST /api/v1/me/devices/remove`.
4. Côté serveur : compte de service Firebase (JSON) monté dans le conteneur et `FCM_SERVICE_ACCOUNT_FILE`.

Tant que ce n'est pas fait, aucune notification push n'est envoyée ; les e-mails restent actifs.

## Avant une première publication — à vérifier sur de vrais appareils

- Parcours complet sur un Android et un iPhone réels (connexion, réservation, annulation, paiement en mode test).
- TalkBack et VoiceOver sur les écrans principaux, et l'arabe (RTL).
- Remplacer les photos de démonstration (recadrages des maquettes) par des photos dont les droits sont acquis.
