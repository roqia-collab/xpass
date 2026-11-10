# XPASS — application mobile (Flutter)

Riverpod · go_router · Dio · flutter_secure_storage (prévu pour les jetons, lot 8).

## Lancer

L'API doit tourner (`docker compose up -d` à la racine, puis seed — voir le README principal).

```powershell
cd apps\mobile
flutter pub get
# Navigateur Chrome (le plus simple sur PC)
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000 --dart-define=MEDIA_BASE_URL=http://localhost:8333/xpass-public
# Émulateur Android (10.0.2.2 = le PC hôte vu depuis l'émulateur)
flutter run -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000 --dart-define=MEDIA_BASE_URL=http://10.0.2.2:8333/xpass-public
```

## Vérifier

```powershell
flutter analyze
flutter test
```

`test/fixtures/locations_paris.json` est une réponse réelle de l'API (seed de démo) : le test
`cards_render_test.dart` rend chaque carte avec ces données pour détecter les débordements.

## Écrans livrés (lot 1)

- 01 Accueil : univers, recherche, « Disponible près de vous », bannière avantage salarié (sans solde inventé).
- 03–06 Univers : en-tête, sous-catégories, filtre budget, tri distance/prix, cartes.
- 08 Fiche partenaire : prestations, infos, annulation, prochain créneau **indicatif**.
- Réservations, Mes crédits, Profil : écrans « Bientôt disponible » (lots 2 et 8).
