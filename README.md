# XPASS

Expériences de divertissement, sport, culture et beauté financées par crédits (personnels, employeur,
promotionnels). Application mobile cliente + portails commerçant, entreprise (RH) et administration.

Développeuse : Benaboud Roqia · Directeur : Zaki Mohamed Mehri

> **État : lots 1 à 7 et 8a.** Catalogue, disponibilités, portefeuille de crédits, réservation, QR et
> consommation, abonnement, règlements partenaires, gestion de l'établissement par le commerçant avantage salarié (portail RH), administration, connexion sécurisée Keycloak, profil et assistance. Les paiements tournent en **bac à sable local
> sans argent** ; l'adaptateur Stripe est écrit mais pas encore testé avec de vraies clés. Avancement détaillé : [docs/PLAN_IMPLEMENTATION.md](docs/PLAN_IMPLEMENTATION.md).

## Structure

| Dossier | Contenu |
|---|---|
| `apps/mobile/` | Flutter (Dart) — app cliente |
| `apps/portals/` | Next.js + TypeScript — `/partner`, `/company`, `/admin` + BFF |
| `backend/` | FastAPI, SQLAlchemy, Alembic, Celery — API REST `/api/v1` |
| `backend/migrations/` | Migrations PostgreSQL/PostGIS |
| `infra/` | Init PostgreSQL (extensions), config stockage S3, médias placeholder |
| `contracts/openapi.json` | Contrat OpenAPI exporté |
| `docs/` | Plan d'implémentation |
| `docker-compose.yml` | PostgreSQL+PostGIS, Redis, stockage S3, API, worker, scheduler |

## Prérequis (Windows)

- Docker Desktop (démarré)
- Node.js 20+ (portails)
- Flutter 3.29+ (mobile) — https://docs.flutter.dev/get-started/install/windows

## Démarrage — PowerShell, depuis le dossier `XPASS`

```powershell
cd C:\Users\PC\Downloads\XPASS_complete\XPASS
copy .env.example .env
docker compose up -d --build
docker compose exec api python -m app.seed.media
docker compose exec api python -m app.seed.demo
```

Vérifier :

- http://localhost:8000/health/ready → `{"status":"ok", ...}`
- http://localhost:8000/docs → documentation interactive de l'API
- http://localhost:8000/api/v1/catalog/locations?city=paris

### Portails web

```powershell
cd apps\portals
copy .env.example .env.local
npm install
npm run dev
```

Ouvrir http://localhost:3000 et cliquer sur « Se connecter avec mon compte XPASS ».
Les comptes de démonstration ont été supprimés (voir « Comptes » plus bas) ; la connexion sans mot de passe est coupée (`AUTH_DEV_LOGIN_ENABLED=false`).

### Application mobile

Compte client : créez-le depuis l’app (onglet Profil → « Créer un compte »).



```powershell
cd apps\mobile
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000 --dart-define=MEDIA_BASE_URL=http://localhost:8333/xpass-public
```

Émulateur Android : remplacer `localhost` par `10.0.2.2` dans les deux `--dart-define`.

## Tests

```powershell
# Backend — contre un vrai PostgreSQL/PostGIS (base xpass_test)
docker compose exec api pytest -q

# Portails
cd apps\portals
npm run typecheck
npm test
npm run build

# Mobile
cd apps\mobile
flutter analyze
flutter test
```

## Migrations

```powershell
docker compose exec api alembic upgrade head          # appliquer
docker compose exec api alembic revision --autogenerate -m "description"   # créer (puis relire le fichier !)
docker compose exec api alembic downgrade -1          # revenir d'une version
```

Réinitialiser les données de démo (réservations et journal compris) : `docker compose exec api python -m app.seed.demo --reset`.
Le seed ne crée plus de comptes de démonstration ; `--with-demo-accounts` les recrée (développement uniquement).
Tout effacer (volumes compris) : `docker compose down -v`.

## Connexion et e-mails (lot 8a)

- Keycloak local : http://localhost:8080 (realm `xpass`). Comptes et sessions conservés dans le volume `keycloak-data` ;
  le realm n’est importé qu’à la première création (`docker compose down -v` pour repartir de zéro).
- Pages de connexion et d’inscription au style XPASS (maquette 02) : thème `infra/keycloak/themes/xpass`. Après une modification du realm ou du montage : `docker compose up -d keycloak` (en développement, le realm est réimporté et les comptes créés à la main sont perdus).
- E-mails capturés par Mailpit : http://localhost:8025 (rien n'est envoyé à l'extérieur).
- Application web avec la connexion sécurisée : ajouter `--dart-define=OIDC_ISSUER=http://localhost:8080/realms/xpass`
  à `flutter run` (`--dart-define=DEV_LOGIN=true` réaffiche le mode démonstration, développement uniquement).

## Carte, langues et accessibilité (lot 8b)

- Carte « Autour de moi » : onglet Explorer → icône carte. Tuiles OpenStreetMap publiques en local ;
  en production, renseigner un fournisseur avec `--dart-define=MAP_TILE_URL=https://…/{z}/{x}/{y}.png`.
- Langue : Profil → Langue (Français, English, العربية). Traduction partielle (voir le plan, §4 nonies).
- Après modification d'un fichier `lib/l10n/*.arb` : `flutter gen-l10n` (fait aussi par `flutter pub get`).

## Réseau de commerçants (inscription réelle)

1. Le commerçant ouvre http://localhost:3000/devenir-partenaire → « Créer mon compte et m’inscrire »
   (page sécurisée XPASS, e-mail vérifié via Mailpit en local).
2. Formulaire d’inscription : **SIRET vérifié** dans l’annuaire public des entreprises
   (recherche-entreprises.api.gouv.fr), puis l’établissement : adresse placée sur la carte par la
   **Base Adresse Nationale** (data.geopf.fr), activité, téléphone, présentation.
3. XPASS crée le partenaire « à vérifier », l’établissement en **brouillon** (invisible des clients) et donne
   au commerçant le rôle de responsable : il complète photo, prestations (avec photos), horaires et équipe.
4. Administration → Partenaires : contrôles « Entreprise (annuaire SIRENE) » et « Adresse (Base Adresse Nationale) »,
   décision motivée, puis publication de l’établissement (Modération). Il apparaît alors dans l’application.
5. Quand les vrais partenaires sont en ligne : Administration → Vue d’ensemble → « Masquer les lieux de démo ».

Les deux services publics sont gratuits et sans clé ; adresses modifiables via `SIRENE_API_URL` et `GEOCODER_URL`.
Si l’annuaire ne répond pas, la candidature est acceptée mais marquée « à vérifier à la main » (jamais « vérifiée »).
Photos : JPEG, PNG ou WebP, 8 Mo maximum, 400 px minimum ; réencodées en JPEG sans métadonnées.
Équipe : Portail commerçant → Équipe → « Accès au portail » : le responsable invite ses collaborateurs par e-mail (« Équipe » : planning, scanner, consultation ; « Responsable » : tout) et retire un accès. Il ne peut retirer ni son propre accès ni le dernier responsable ; chaque geste est inscrit au journal d’audit.

## Réseau et relation client (après le lot 8)

- **Plusieurs établissements** : sélecteur dans l’en-tête du portail commerçant, « Ajouter un établissement »
  (adresse géocodée, brouillon jusqu’à publication XPASS).
- **Modification du nom, de l’activité ou de l’adresse** : Établissement → « Demander une modification » ;
  validation dans Administration → Modération (avant / après, motif tracé, e-mail au commerçant).
- **Statistiques** (portail commerçant) : visites, clients, crédits, brut / commission / net, semaines, jours, prestations.
- **Messagerie** : une conversation par réservation (application : réservation → « Écrire à l’établissement » ;
  portail : Messages). Fermée 30 jours après la prestation ; contenu jamais dans les e-mails ni les notifications.
- **Favoris** : cœur sur la fiche d’un lieu, liste dans Profil → Mes favoris.
- **Profil et Paramètres** : le Profil regroupe l’espace personnel (réservations, crédits, abonnement, favoris, aide) ; la page Paramètres (roue crantée) regroupe compte, préférences, notifications, confidentialité, à propos, suppression du compte et déconnexion.
- **Filtres Date et Participants** (carte « Autour de moi ») : lieux ouverts ce jour-là, prestations acceptant ce nombre.
- **Avis notés** : depuis le reçu, une fois par prestation consommée (60 jours) ; réponse du responsable (portail → Avis) ;
  masquage motivé par XPASS (Administration → Avis). Signés prénom + initiale.
- **Rappel de la veille** (tâche planifiée toutes les 15 min) : e-mail, et notification si Firebase est configuré.
- **Notifications sur téléphone** : le serveur est prêt (Firebase Cloud Messaging, API HTTP v1). À faire de votre côté :
  créer un projet Firebase, renseigner `FCM_SERVICE_ACCOUNT_FILE` (JSON du compte de service), puis ajouter
  `google-services.json` / `GoogleService-Info.plist` et le paquet `firebase_messaging` à l’application.
  Sans cela, aucune notification n’est envoyée (les e-mails restent actifs).

## Comptes

Les comptes de démonstration (`client@`, `partenaire@`, `rh@`, `admin@xpass.demo`) ont été fermés : données
personnelles effacées, réservations à venir annulées, écritures financières conservées sans identité.

```powershell
# Créer (ou promouvoir) un administrateur réel
docker compose exec api python -m app.seed.accounts create-admin --email vous@exemple.fr --name "Prénom Nom"
# Fermer les comptes de démonstration restants
docker compose exec api python -m app.seed.accounts remove-demo
```

Le compte doit aussi exister dans Keycloak avec la même adresse (e-mail vérifié). Le mot de passe se choisit
via le lien « Mettre à jour votre compte » (reçu dans Mailpit en local) ou « Mot de passe oublié ? ».
Un compte créé par « Créer un compte » est un compte client. Pour ouvrir un espace commerçant ou RH : Administration → Partenaires → fiche du partenaire → « Accès au portail », ou Administration → Entreprises. Saisissez l’adresse e-mail et le rôle (responsable / équipe, administrateur RH / lecture seule) ; la personne reçoit un e-mail d’information (sans lien) et se connecte, ou crée son compte, avec cette adresse. Chaque attribution et chaque retrait sont inscrits au journal d’audit.

## Paiements (lot 4)

En local, `PSP_PROVIDER=sandbox` : la page de paiement est un bac à sable **sans argent** qui produit
des webhooks signés, traités comme de vrais. Il faut un `PSP_WEBHOOK_SECRET` (valeur aléatoire) dans `.env`.
Le bac à sable est refusé si `APP_ENV=production`.

Pour Stripe (mode test d'abord) : `PSP_PROVIDER=stripe`, `PSP_SECRET_KEY=sk_test_…`,
`PSP_WEBHOOK_SECRET=whsec_…`, `PSP_PRICE_ESSENTIEL=price_…`, et un webhook Stripe pointant vers
`https://<api>/api/v1/payments/webhooks/stripe`.

**Versements aux commerçants (Stripe Connect, comptes Express)** — portail commerçant → Règlements →
« Ouvrir mon compte de versement » : XPASS crée le compte connecté et envoie le responsable sur la page
sécurisée de Stripe (identité, entreprise, IBAN : jamais saisis ni stockés chez XPASS). Au retour, le statut est
relu ; il est ensuite tenu à jour par le webhook signé `account.updated`. Les virements hebdomadaires ne partent
que vers un compte « Versements activés ». À configurer chez Stripe :
1. activer Connect (comptes Express) sur le compte plateforme ;
2. un second endpoint webhook « événements des comptes connectés » vers la même adresse
   `https://<api>/api/v1/payments/webhooks/stripe`, événement `account.updated`, et son secret dans `PSP_CONNECT_WEBHOOK_SECRET` ;
3. `PORTALS_PUBLIC_URL` = adresse publique des portails (retour après la page Stripe).

En local (`PSP_PROVIDER=sandbox`), la page Stripe est remplacée par une page de démonstration qui produit le même
webhook signé ; aucune donnée bancaire n’est demandée.

## Services à configurer

Voir `.env.example` et la section 5 du plan : fournisseur OIDC (production), prestataire de paiement
(lot 4), tuiles de carte `MAP_TILE_URL` (lot 8b), e-mail/SMS (lot 6), stockage S3 de production. La connexion de
démonstration est refusée au démarrage si `APP_ENV=production`.

## Médias

Les photos de `infra/seed-media/placeholders/` sont des **recadrages des maquettes** générés par
`infra/seed-media/extract_placeholders.py`, pour le développement uniquement. Elles doivent être
remplacées par des photos dont les droits sont acquis.

## Mise en ligne

- **Serveur** : kit dans `infra/production/` (Caddy HTTPS, Keycloak en mode `start` sur PostgreSQL, API 4 workers,
  worker, planificateur, portails, sauvegarde quotidienne). Pas à pas : `docs/DEPLOIEMENT.md`.
- **Suivi des erreurs** : Sentry facultatif (`SENTRY_DSN` ; sans valeur, rien n'est envoyé).
- **Pages légales** : `/legal/cgu`, `/legal/conditions-partenaires`, `/legal/confidentialite`, `/legal/mentions-legales`
  (sources dans `apps/portals/src/legal/`). Ce sont des **modèles à compléter** ([crochets]) et à faire valider par un
  juriste ; un bandeau l'indique tant que `LEGAL_VALIDATED=true` n'est pas défini.
- **Applications mobiles** : icône, écran de démarrage, identifiant `fr.xpass.app`, signature et publication dans
  `docs/APPLICATIONS_MOBILES.md`.
- **Connexion avec Google** : bouton « Continuer avec Google » (application et portails), activé avec les identifiants
  Google Cloud du projet : `docs/CONNEXION_GOOGLE.md`.

## Entreprises : paiement en ligne et synchronisation RH

- **Factures** : portail entreprise → Factures → « Payer en ligne » (carte ou prélèvement SEPA via Stripe Checkout ;
  bac à sable sans argent en local). La facture passe « Payée » uniquement sur webhook signé
  (`checkout.session.completed` ou `checkout.session.async_payment_succeeded`), jamais au retour du navigateur.
- **Logiciel RH** : portail entreprise → Salariés → « Import automatique » : création d'une clé `xph_…` (affichée une
  fois, seule l'empreinte SHA-256 est conservée, 5 clés actives au plus). Le logiciel envoie la liste complète :
  `PUT /api/v1/hr-sync/employees` (en-tête `Authorization: Bearer <clé>`, `?dry_run=true` pour simuler,
  `remove_missing` pour retirer les absents, 5 000 lignes au plus). Chaque synchronisation est inscrite au journal d'audit.

## Règles des crédits (principe des plateformes à crédits)

- **Prix variable par créneau** : le partenaire fixe un prix de base ; +20 % aux heures de pointe (18 h – 21 h en
  semaine, week-end), +20 % si le créneau est occupé à 70 % ou plus, −20 % en dernière minute (moins de 6 h avant,
  occupé à moins de 30 %). Prix figé à la réserve ; si le prix affiché a changé, la réserve est refusée
  (`price_changed`). Règles : `backend/app/modules/booking/pricing.py`.
- **Annulation tardive** : la moitié des crédits est rendue, l'autre moitié versée au partenaire.
- **Absence** : tâche `xpass.mark_no_shows` (toutes les 15 min) ; 2 h après la fin du créneau sans validation du QR,
  les crédits sont consommés et versés au partenaire.
- **Report plafonné** : à chaque renouvellement, les crédits d'abonnement non utilisés sont reportés jusqu'à un mois
  de formule ; au-delà, les plus anciens expirent. Fin d'abonnement : les crédits d'abonnement disponibles expirent.
  Crédits employeur et promotionnels jamais concernés.
- **Formules** : portail Administration → Formules (création, retrait ; prix figé dès qu'il y a des abonnés). Le client
  change de formule dans l'application ; la nouvelle s'applique au prochain renouvellement, sans prorata.
- **Réponse immédiate** : favoris, messages, interrupteurs, accès d'équipe et clés d'API s'affichent tout de suite,
  puis sont confirmés (ou annulés avec un message) par le serveur.

