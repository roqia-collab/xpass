# XPASS — Plan d'implémentation

Développeuse : Benaboud Roqia · Directeur : Zaki Mohamed Mehri

Ce document est la référence d'avancement. Il est mis à jour à la fin de chaque lot.

## 0. Analyse du dossier (31 octobre 2026)

| Élément | État |
|---|---|
| `PROMPT_CLAUDE_CODE_XPASS.md` | Lu, appliqué (architecture, invariants, méthode). |
| `28_interfaces/*.png` | 28 maquettes lues. Ce sont des références visuelles, pas des composants. |
| `logo/XPASS_logo_proposition.png` | Logo raster (pas de vectoriel). Recadré pour les apps. |
| **Cahier des charges technique PDF** | **Absent du dossier.** Le plan s'appuie sur le prompt et les maquettes. À ajouter dans `docs/` puis à confronter à ce plan (voir §6). |
| Code existant | Aucun : projet créé de zéro. |

### Direction visuelle retenue

- Couleurs : crème `#FAF8F3` (fond), bleu nuit `#121A35` (texte, sidebar RH), corail `#FF674F` (action principale), lavande `#ECEAFB` / `#C9C3F5` (puces, cartes secondaires), vert doux `#E8F1EA` (politique d'annulation).
- Titres en serif à fort contraste (type « Fraunces / DM Serif »), texte en sans-serif géométrique (type « Inter / DM Sans »).
- Grandes photos, cartes arrondies (16–24 px), puces arrondies, un bouton corail principal par écran.
- Mobile : navigation fixe Explorer · Réservations · Mes crédits · Profil.
- Portails : sidebar gauche (crème pour commerçant/admin, bleu nuit pour RH), barre de recherche en haut, cartes KPI.

### Photos

Les photos des maquettes sont des images générées intégrées aux PNG. Pour le développement, des **recadrages de placeholder** sont extraits des maquettes dans `infra/seed-media/` (script `infra/seed-media/extract_placeholders.py`) et servis par le stockage S3 local (bucket public). Ils sont marqués « placeholder » et doivent être remplacés par des photos dont les droits sont acquis. Les noms de marques réelles visibles dans les maquettes (salle d'escalade, réseau de cinéma, musées) ont été remplacés par des noms fictifs.

## 1. Architecture

```
XPASS/
  apps/mobile/           Flutter (Riverpod, go_router, Dio, flutter_secure_storage)
  apps/portals/          Next.js + TypeScript : /partner, /company, /admin (+ BFF /api/session)
  backend/app/api/v1/    Routeurs HTTP FastAPI
  backend/app/modules/   Modules métier : modèles, schémas, repositories, services
  backend/app/core/      Configuration, sécurité, erreurs
  backend/app/db/        Session, base déclarative
  backend/app/workers/   Celery (worker + beat)
  backend/migrations/    Alembic
  backend/tests/         Pytest contre un vrai PostgreSQL/PostGIS
  contracts/             OpenAPI exporté
  infra/                 Init PostgreSQL, médias de démo
  docs/
  docker-compose.yml     postgres(PostGIS) · redis · minio · api · worker · scheduler
```

### Décisions explicites

1. **SQLAlchemy synchrone + psycopg 3.** Les transactions de crédits/réservations (lots suivants) reposent sur des verrous `SELECT … FOR UPDATE` et des contraintes ; le mode synchrone est plus simple à raisonner et suffisant (FastAPI exécute les routes sync dans un pool).
2. **Marché = devise + fuseau.** `markets` porte `currency` et `timezone`. Les crédits sont des `INTEGER` ; l'argent sera stocké en `BIGINT` unités mineures + `currency` (lot 3). Les deux ne partagent aucune colonne.
3. **Offres versionnées.** `offers` pointe vers `offer_versions` (prix en crédits, durée, politique d'annulation). Une réservation conservera l'`offer_version_id` (lot 2).
4. **Statut commercial ≠ statut PSP** sur `merchants`. Un établissement n'est public que si le marchand est `approved` et le site `published`. La réservation exigera en plus `psp_status = verified` (lot 3).
5. **« Prochain créneau » indicatif.** En lot 1 il est calculé à partir des horaires et exceptions uniquement (aucune réservation n'existe encore). L'API le marque `"indicative": true`. Le moteur de disponibilité réel (capacité, occupations, blocages externes) arrive au lot 2.
6. **Authentification.** Production : OIDC (issuer/JWKS configurables). Développement : endpoint `POST /api/v1/auth/dev/login` qui n'existe que si `APP_ENV=development` **et** `AUTH_DEV_LOGIN_ENABLED=true` ; la configuration refuse de démarrer si ce drapeau est vrai en production.
7. **BFF portails.** Le navigateur ne voit jamais le jeton : Next.js le garde dans un cookie `HttpOnly`, `SameSite=Lax`, `Secure` en production. Les mutations passent par des Server Actions (protection CSRF intégrée par vérification d'origine de Next.js).
8. **Médias.** Le backend stocke des clés d'objet (`cover_image_key`) ; chaque client compose l'URL avec sa propre base (`MEDIA_BASE_URL`), ce qui marche aussi depuis l'émulateur Android (`10.0.2.2`).
9. **Stockage local : SeaweedFS au lieu de MinIO.** Les images Docker MinIO ne sont plus téléchargeables publiquement (accès refusé sur Docker Hub et quay.io au 31/10/2026). SeaweedFS expose la même API S3 ; le code utilise boto3 et ne dépend pas du fournisseur. Config : `infra/storage/s3.json`.
10. **Pas de faux succès.** Les écrans dont le backend n'existe pas encore affichent « Bientôt disponible » ; aucun bouton ne simule réservation, paiement ou consommation.

## 2. Lots

| Lot | Contenu | État |
|---|---|---|
| **1** | Environnement local, migrations catalogue/identité, données de démo, API catalogue, mobile Explorer + 4 univers + fiche partenaire, structure des 3 portails avec connexion | **Livré (voir §4)** |
| 2 | Disponibilités réelles (capacité, occupations exclusives `EXCLUDE USING gist`, blocages externes), portefeuille (`wallets`, `credit_lots`, journal append-only équilibré + trigger différé), réservation HELD 5 min → CONFIRMED, annulation, idempotence, outbox. Écrans 09–11, 14. Tests de concurrence. | **Livré (voir §4 bis)** |
| 3 | QR opaque éphémère (empreinte serveur), scan → aperçu → consommation atomique (mouvement crédits + reçu + dette partenaire + outbox), reçu et avis Google neutre, ajout à l'agenda (ICS sans jeton). Écrans 12, 13, 17, 19, 20. | **Livré (voir §4 ter)** |
| 4 | Paiements PSP (adaptateur + webhooks signés, persistés, dédupliqués), abonnements, factures, dettes et versements partenaires. Écrans 15, 22. | **Livré en bac à sable (voir §4 quater)** — Stripe écrit, non testé faute de clés |
| 5 | Portail commerçant complet : établissement, offres, horaires/exceptions, équipe/ressources, planning jour/semaine. Écrans 18, 21. | **Livré (voir §4 quinquies)** — invitations de collaborateurs au lot 8 |
| 6 | RH : organisation, invitations individuelles + CSV avec aperçu d'erreurs, politiques, allocations uniques par membre/période, financement, rapports agrégés (masquage < 10). Écrans 23–25. | **Livré (voir §4 sexies)** — e-mails non envoyés (fournisseur à configurer) |
| 7 | Administration : validation commerciale/PSP, modération, litiges, restitution de crédits, ajustements, rapprochement, audit. Écrans 26–28. | **Livré (voir §4 septies)** — justificatifs et rapprochement bancaire automatique à venir |
| 8 | Connexion/inscription mobile OIDC (écran 02), profil et assistance (16), carte « Autour de moi » (07), i18n EN/AR RTL, accessibilité, finitions. | **Livré** — 8a (§4 octies) : connexion OIDC, profil et assistance, e-mails ; 8b (§4 nonies) : carte, EN/AR partiel, accessibilité |

Dépendances : 2 → 3 → 4 ; 6 dépend de 2 (portefeuille) et 4 (financement) ; 7 dépend de 3 et 4 ; 5 peut avancer en parallèle après 2.

## 3. Correspondance maquettes → lots

| # | Écran | Lot |
|---|---|---|
| 01 | Accueil client | 1 ✅ |
| 02 | Connexion et inscription | 8a ✅ |
| 03–06 | Divertissement, Sport, Culture, Beauté | 1 ✅ |
| 07 | Autour de moi (carte) | 8 |
| 08 | Fiche partenaire | 1 ✅ |
| 09–11 | Calendrier, confirmation, mes réservations | 2 ✅ |
| 12–13 | Réservation et QR, reçu et avis | 3 ✅ |
| 14 | Mes crédits | 2 ✅ |
| 15 | Abonnement | 4 ✅ |
| 16 | Profil et assistance | 8a ✅ |
| 17 | Ajouter à l'agenda | 3 ✅ |
| 18 | Commerçant planning | 5 ✅ |
| 19–20 | Scanner, vérification commerçant | 3 ✅ |
| 21 | Prestations et équipe | 5 ✅ |
| 22 | Règlements commerçant | 4 ✅ |
| 23–25 | Portail RH | 6 ✅ |
| 26–28 | Administration | 7 ✅ |

## 4. Lot 1 — détail

- `docker-compose.yml` : PostgreSQL 16 + PostGIS 3.4 (extensions `postgis`, `btree_gist`, `unaccent`, `pgcrypto`), Redis 7, stockage S3 SeaweedFS (buckets `xpass-public` / `xpass-private` créés par `app.seed.media`), API, worker Celery, scheduler Celery beat.
- Migration `0001` : `markets`, `cities`, `categories`, `subcategories`, `merchants`, `locations` (géographie PostGIS + index GiST), `opening_hours`, `schedule_exceptions`, `resources`, `offers`, `offer_versions`, `offer_resources`, `users`, `organizations`, `memberships`.
- Données de démo synthétiques (`is_demo = true`) : marché France, 4 villes, 4 univers, 13 sous-catégories, 12 établissements parisiens publiés, 3 marchands en attente de validation, 3 utilisateurs de démo (admin, commerçant, RH).
- API : `/health`, `/health/ready`, `/api/v1/catalog/categories`, `/api/v1/catalog/categories/{slug}`, `/api/v1/catalog/locations` (recherche texte sans accents, filtres univers/sous-catégorie/ville/budget, tri distance PostGIS), `/api/v1/catalog/locations/{slug}`, `/api/v1/geo/cities`, `/api/v1/auth/dev/login`, `/api/v1/me`, `/api/v1/partner/locations`, `/api/v1/admin/merchants`, `/api/v1/company/organization`.
- Mobile : Accueil (01), écran d'univers paramétré pour les 4 univers (03–06), fiche partenaire (08), barre de navigation ; états chargement / erreur réseau / aucun résultat.
- Portails : connexion de démo, layouts commerçant / RH / admin, pages branchées sur l'API (établissements & prestations du commerçant, liste des partenaires admin, organisation RH), autres pages marquées « Lot X ».

### Vérifications réellement exécutées (31/10/2026)

| Vérification | Résultat |
|---|---|
| `pytest` backend contre PostgreSQL 16/PostGIS 3.4 réel | 28 tests réussis (catalogue, recherche sans accents, filtres, tri PostGIS, créneau indicatif, authentification, isolation des rôles, refus du mode démo en production) |
| `flutter analyze` (Flutter 3.29.3 en conteneur Docker) | Aucun problème |
| `flutter test` | 4 tests réussis, dont le rendu de toutes les cartes avec une réponse réelle de l'API |
| `flutter build web` + contrôle visuel | Accueil, univers Beauté, fiche partenaire affichés avec les données PostgreSQL |
| Portails : `tsc --noEmit`, `vitest`, `next build` | OK, 5 tests réussis |
| Portails : contrôle manuel | Connexion démo commerçant/admin, planning, tableau partenaires via BFF + TanStack Query ; RH refusé sur /admin, BFF 403, sans session → /login |
| **Non vérifié** | Exécution sur émulateur Android / appareil iOS (aucun SDK Android/Xcode sur ce poste) |

### Limites connues du lot 1

- « Prochain créneau » : calcul indicatif à partir des horaires uniquement (pas de capacité ni de réservation).
- Localisation de l'utilisateur non demandée : distances calculées depuis le centre de la ville choisie.
- Recherche de la barre supérieure des portails désactivée (branchée avec les modules concernés).
- Textes de l'app en français ; locales `en` / `ar` déclarées mais non traduites.
- Médias : placeholders recadrés des maquettes, à remplacer.

## 4 bis. Lot 2 — détail (31 octobre 2026)

### Modèle (migration `0002`)

- `wallets` (un par client et par marché), `credit_lots` (source personnelle / employeur / promotionnelle, origine, expiration, univers éligibles), `credit_lot_balances` (projection : disponible, réservé, consommé, expiré, chacun `CHECK >= 0`).
- `credit_journals` + `credit_journal_lines` : écritures `grant`, `reserve`, `release`, `capture`, `expire`. **Trigger de contrainte différé** : la somme des lignes d'une écriture doit valoir 0 au commit. **Ajout seul** : UPDATE/DELETE refusés par trigger ; corrections par contre-écriture (`reverses_journal_id`).
- `bookings` : version d'offre conservée, prix par personne, total (`CHECK total = prix × participants`), échéance de la réserve, limite d'annulation gratuite. Index unique partiel : un même client ne peut pas avoir deux réservations actives pour la même offre et la même heure, quelle que soit la clé d'idempotence.
- `resource_occupancies` : réservation **ou** blocage externe (`CHECK num_nonnulls = 1`), contrainte `EXCLUDE USING gist (resource_id =, during &&) WHERE is_active`.
- `session_inventories` : capacité collective, mise à jour conditionnelle atomique (`reserved + n <= capacity`), `CHECK reserved <= capacity`.
- `external_blocks`, `idempotency_keys` (empreinte SHA-256 du corps), `outbox_events`.

### Règles appliquées

- Réserve HELD de 5 minutes : capacité ET crédits bloqués, rien n'est consommé. Expirée par Celery beat (toutes les 20 s) et avant chaque nouvelle réserve.
- Confirmation : la réserve devient CONFIRMED, les crédits restent **réservés** ; ils seront consommés au scan QR (lot 3).
- Annulation gratuite avant la limite : crédits restitués. Annulation tardive (règle de la maquette 10) : crédits consommés ; la dette partenaire correspondante arrive au lot 4.
- Ordre de consommation : promotionnel → employeur → personnel, expiration la plus proche d'abord ; lots expirés à la date de la prestation exclus.
- Verrous : portefeuille → réservation → inventaire/occupation → lots (évite les interblocages).
- Commandes `POST /bookings`, `/confirm`, `/cancel` : en-tête `Idempotency-Key` obligatoire. Même clé + même corps = réponse rejouée (`Idempotent-Replayed: true`) ; même clé + autre corps = 422.
- Outbox écrite dans la transaction métier, diffusée par Celery (journalisée ; aucun service externe branché).

### Crédits de démonstration

Le compte `client@xpass.demo` reçoit 50 crédits personnels, 70 « employeur » et 20 promotionnels par une écriture `grant` d'origine `demo_grant`. **Ce ne sont ni des paiements ni de vraies allocations employeur** : l'app les signale comme crédits de démonstration. Achat de crédits : lot 4 ; allocations employeur : lot 6.

### Vérifications réellement exécutées (lot 2)

| Vérification | Résultat |
|---|---|
| `pytest` (PostgreSQL réel) | 48 tests réussis, dont 20 pour le lot 2 ; suite des réservations relancée 3 fois sans échec |
| Concurrence | 8 clients sur la même ressource → 1 seul gagnant ; 12 clients sur une séance de 8 places → exactement 8 ; 5 réserves parallèles d'un client à 20 crédits → 1 seule, solde jamais négatif |
| Idempotence | rejeu, clé réutilisée avec un autre corps (422), même effet avec une autre clé (409) |
| Journal | écriture déséquilibrée refusée au commit ; UPDATE/DELETE refusés ; projections = reconstruction depuis le journal |
| Flutter | `flutter analyze` sans problème, 7 tests réussis |
| Parcours réel (navigateur) | connexion démo → calendrier → réserve (compte à rebours 04:56, crédits promotionnels) → confirmation → « Mes réservations » → planning commerçant |
| Portails | `tsc`, `vitest`, `next build` OK |

### Limites du lot 2

- Pas de consommation au scan ni de QR (lot 3) : une réservation confirmée passée reste « Passées » sans statut « utilisée ».
- Pas de dette partenaire ni de règlement sur annulation tardive (lot 4).
- Blocages externes : service et contrainte en place, bouton « Bloquer une plage » du portail au lot 5.
- Vue semaine du planning et notifications (e-mail/push) non développées.
- Connexion client : mode démonstration uniquement (OIDC au lot 8).

## 4 ter. Lot 3 — détail (31 octobre 2026)

### Modèle (migration `0003`)

- `qr_tokens` : empreintes SHA-256 du jeton (QR) et du code court, réservation, site, expiration (60 s), révocation, scan (opérateur + heure), utilisation. Le jeton et le code ne sont jamais stockés en clair. Code court unique parmi les jetons actifs d'un même site.
- `redemptions` (unique par réservation), `receipts` (unique par réservation, références `XP-10001…` via une séquence), `partner_payables` (unique par réservation, en crédits, `amount_minor`/`currency` vides et statut `pending_valuation` tant que le barème monétaire n'est pas défini).
- `bookings.redeemed_at`.

### Règles appliquées

- QR et code émis uniquement pour une réservation **confirmée** ; chaque nouvel affichage révoque le précédent ; l'app le renouvelle automatiquement 5 s avant expiration.
- Scan (QR ou code) = **aperçu sans effet** : aucun crédit ne bouge. Le jeton est réservé 5 minutes à l'opérateur qui l'a scanné pour confirmer.
- Refus explicites : code inconnu, expiré ou renouvelé, autre établissement, déjà consommé, réservation non confirmée, hors fenêtre (1 h avant à 2 h après la prestation).
- Confirmation : dans **une seule transaction** — capture des crédits (réservé → consommé), statut REDEEMED, consommation, reçu, dette partenaire, événement outbox. Clé d'idempotence obligatoire.
- Anti force brute : 20 codes invalides par opérateur et par 10 minutes (Redis) ; si Redis est indisponible, la vérification est refusée plutôt que non protégée.
- Annulation tardive (lot 2) : crée désormais aussi une dette partenaire `late_cancellation`.
- Agenda : fichier `.ics` généré par l'API (titre, horaire, adresse, rappel 1 h) et lien Google Calendar — **jamais** de jeton ni de code dans l'événement.
- Avis : bouton vers le lien d'avis de l'établissement s'il est renseigné (`locations.review_url`), sans récompense ni publication automatique. Aucun lien n'est renseigné dans les données de démo (établissements fictifs) : l'écran l'indique.

### Vérifications réellement exécutées (lot 3)

| Vérification | Résultat |
|---|---|
| `pytest` (PostgreSQL réel) | 60 tests réussis, dont 12 pour le lot 3 ; suites réservation + consommation relancées 2 fois sans échec |
| Concurrence | 5 opérateurs confirment le même QR en parallèle → 1 seule consommation, 1 reçu, 1 dette |
| Sécurité | jeton stocké en empreinte ; ancien QR refusé après renouvellement ; autre site refusé ; client ou partenaire étranger → 403 ; 21e code invalide → 429 ; ICS sans jeton ni code |
| Flutter | `flutter analyze` sans problème, 10 tests réussis |
| Portails | `tsc`, `vitest`, `next build` OK |
| Parcours réel (navigateur) | QR + code affichés dans l'app → code saisi dans le portail commerçant → aperçu (crédits inchangés en base) → confirmation (reçu XP-10001, dette `pending_valuation`, outbox diffusée) → l'app bascule seule sur le reçu |

Pour ce test, l'horaire de la réservation de démonstration a été avancé en base afin d'entrer dans la fenêtre de consommation.

### Corrigé pendant le lot 3

- Ouverture directe d'une réservation : la requête partait avant la restauration de la session et le 401 effaçait la session. Les données protégées attendent maintenant la session, et seul un jeton refusé déconnecte.

### Limites du lot 3

- Scan caméra dans le portail : testé sans caméra (saisie du code). Le décodage QR (jsQR) nécessite HTTPS hors localhost et l'autorisation caméra ; refus et absence de caméra sont gérés.
- « Calendrier du téléphone » passe par le partage du fichier `.ics` (pas d'insertion native directe).
- Valorisation en euros des dettes, versements et rapprochement : lot 4. Absences (no-show) : à définir avec le cahier des charges.
- Lien d'avis : saisie par le partenaire au lot 5.

## 4 quater. Lot 4 — détail (31 octobre 2026)

### Modèle (migration `0004`)

- `subscription_plans` (par marché, prix en unités mineures + devise, crédits par période, validité), `subscriptions` (un seul abonnement vivant par client et par marché), `invoices` (unique par facture du prestataire, `livemode`).
- `payment_webhook_events` : chaque webhook est stocké **après** vérification de signature et **avant** traitement, unique par (prestataire, identifiant d'événement), suppression interdite. Issue, tentatives et dernière erreur conservées.
- `money_journals` / `money_journal_lines` : journal monétaire en ajout seul, équilibré **par devise** (trigger différé). Comptes : trésorerie PSP, encaissements clients, coût des prestations, dettes partenaires, commission.
- `settlement_terms` : barème par marché (valeur d'un crédit reversée au partenaire, commission en points de base, date d'effet).
- `partner_payables` : brut, commission, devise, date de la prestation, versement ; `partner_payouts` (un par marchand, semaine et devise ; `net = brut − commission + ajustements` imposé par contrainte) ; `partner_adjustments` (avoirs et compléments, références `AV-1001…`).
- `credit_lots` : **une seule allocation par facture** (index unique sur la référence de facture).
- `merchants.psp_account_id` : compte connecté destinataire des versements.

### Règles appliquées

- Aucun crédit n'est ajouté au retour du navigateur : seul le traitement d'un webhook signé « facture payée » crée le lot de crédits, la facture et l'écriture monétaire, dans une transaction.
- Signature au format Stripe (`t=…,v1=HMAC-SHA256`), comparaison à temps constant, refus au-delà de 5 minutes.
- Montant et devise de la facture contrôlés contre la formule : en cas d'écart, rien n'est appliqué et l'événement reste en anomalie (non retenté automatiquement, à examiner au lot 7).
- Événement arrivé avant celui qui crée le lien : retenté par la tâche périodique (30 s), jusqu'à 10 fois.
- Traitement concurrent d'un même événement : verrou de ligne, appliqué une seule fois.
- Valorisation à la consommation (et à l'annulation tardive) avec le barème en vigueur à la date de la prestation ; commission arrondie au centime (demi vers le haut).
- Versements : chaque heure, la semaine fermée (lundi → dimanche, fuseau du marché) est regroupée par marchand ; transfert demandé au prestataire seulement si le marchand est vérifié ; **seul le webhook du prestataire** marque « Virement confirmé ». Montant différent → « À rapprocher ». Net négatif → jamais prélevé, « À rapprocher ».
- Renouvellement automatique désactivable ou réactivable ; l'abonnement reste actif jusqu'à la fin de la période.

### Bac à sable (`PSP_PROVIDER=sandbox`)

Prestataire local **sans argent**, refusé au démarrage si `APP_ENV=production`. Sa page de paiement est marquée « aucun argent n'est débité ». Il produit des webhooks au format Stripe, signés avec `PSP_WEBHOOK_SECRET`, qui suivent exactement le même chemin (vérification, persistance, déduplication, traitement Celery) que de vrais webhooks. Les crédits ainsi obtenus sont signalés comme crédits de démonstration dans l'application.

### Valeurs illustratives

La formule « XPASS Essentiel » (100,00 €/mois, 100 crédits) et le barème (1,00 € par crédit, commission 10 %) reprennent les maquettes 15 et 22 et sont marqués **démonstration**. Ce ne sont pas des conditions commerciales : à remplacer avant toute mise en production.

### Vérifications réellement exécutées (lot 4)

| Vérification | Résultat |
|---|---|
| `pytest` (PostgreSQL réel) | 76 tests réussis, dont 16 pour le lot 4 ; suite complète relancée sans échec |
| Webhooks | signature absente, fausse, périmée, corps modifié, mauvais prestataire → 400 et rien n'est stocké ; même événement reçu deux fois → stocké une fois |
| Crédits | rien au retour navigateur ni avant traitement ; même facture annoncée par deux événements → une seule allocation ; 5 traitements parallèles → appliqué une fois ; montant faux → jamais appliqué |
| Règlements | 18 crédits → 18,00 € brut / 1,80 € de commission ; versement hebdomadaire idempotent avec avoir ; transfert → webhook → « Virement confirmé » ; écart de montant → « À rapprocher » ; relevé CSV |
| Journaux | écriture monétaire déséquilibrée refusée ; modification refusée ; toutes les écritures équilibrées par devise |
| Flutter | `flutter analyze` sans problème, 13 tests réussis |
| Portails | `tsc`, `vitest`, `next build` OK |
| Parcours réel (navigateur) | app → « S'abonner » → page du bac à sable → paiement → 2 webhooks signés traités par le worker Celery → abonnement actif, solde 100 → 200 ; portail → Règlements : période en cours, puis versement de 16,20 € « Virement confirmé » et relevé CSV |

Pour ce dernier point, le cycle de règlement a été lancé une fois sur la base de démo en simulant la clôture de la semaine en cours (26 oct. – 1er nov.).

### Limites du lot 4

- **Stripe non testé** : l'adaptateur (Checkout abonnement, annulation en fin de période, transferts Connect) est écrit mais n'a jamais été exécuté faute de clés. À valider en mode test Stripe, y compris le format des webhooks selon la version d'API du compte.
- Pas d'intégration du compte Connect partenaire (création, vérification d'identité) : `psp_account_id` est à renseigner (lots 5 et 7).
- Pas de remboursement ni d'avoir client (litiges : lot 7) ; pas de factures PDF ni de TVA (règles fiscales à définir) ; pas de facturation entreprise (lot 6).
- Anomalies de paiement visibles en base uniquement ; écran d'administration au lot 7.
- Une erreur « No implementation found for method … » apparaît une fois au démarrage de l'app web dans la console, sans effet visible observé ; pas encore diagnostiquée.

## 4 quinquies. Lot 5 — détail (2 novembre 2026)

Aucune migration : le modèle des lots 1 et 2 (offres versionnées, ressources, horaires, exceptions, blocages) suffisait.

### Fonctions

- **Prestations** (maquette 21) : création (brouillon ou publiée), modification, publication et dépublication, choix des professionnels. Modes : rendez-vous, séance à capacité, accès libre ; les billets externes restent configurés par XPASS.
- **Équipe** : ajout de professionnels, salles et équipements ; renommage ; désactivation et réactivation.
- **Établissement** : description, accès, point de rendez-vous, accessibilité, lien d'avis Google (repris sur le reçu client).
- **Horaires** : plusieurs plages par jour ; **fermetures et horaires exceptionnels** par date.
- **Planning** (maquette 18) : vue jour par ressource et **vue semaine** ; plages bloquées affichées ; formulaire « Bloquer une plage » et déblocage.

### Règles appliquées

- Seul le responsable (`merchant_owner`) modifie le catalogue ; le personnel (`merchant_staff`) consulte et peut bloquer ou débloquer des plages. Contrôle côté API, l'interface passe en lecture seule.
- Chaque modification d'une prestation crée une **nouvelle version** : les réservations existantes gardent prix, durée et conditions d'annulation. Le mode de réservation ne change pas après création.
- Une ressource avec des réservations à venir ne peut pas être désactivée ; si une prestation n'a plus aucune ressource active, elle est retirée de la vente.
- Changer les horaires ou ajouter une fermeture **n'annule jamais** de réservation : le nombre de réservations à venir hors des nouveaux horaires est signalé au commerçant.
- Les blocages utilisent la contrainte d'exclusion du lot 2 : un chevauchement avec une réservation ou un autre blocage est refusé.
- Mutations du portail par Server Actions (origine vérifiée, jeton jamais exposé au navigateur).

### Vérifications réellement exécutées (lot 5)

| Vérification | Résultat |
|---|---|
| `pytest` (PostgreSQL réel) | 85 tests réussis, dont 9 pour le lot 5 |
| Droits | responsable : écriture ; personnel : lecture et blocages seulement ; client, RH, autre établissement → 403 |
| Versions | réservation à 12 crédits conservée après passage de la prestation à 20 crédits (version 2) |
| Horaires | chevauchement ou fin avant début refusés ; réduction des horaires signalant les réservations concernées, aucune annulée |
| Fermeture | créneaux supprimés le jour fermé, rétablis après suppression ; date passée refusée |
| Blocages | création par le personnel, chevauchement refusé, déblocage libérant la plage |
| Portails | `tsc`, `vitest`, `next build` OK |
| Navigateur | création d'une prestation « Barbe et rasage » en brouillon ; blocage 12:00–13:00 affiché dans les vues jour et semaine puis retiré ; page Établissement avec horaires modifiables |

La prestation « Barbe et rasage » créée pendant ce test est restée en **brouillon** dans la base de démo (invisible des clients).

### Limites du lot 5

- Pas d'invitation de collaborateurs ni de comptes par site : ils dépendent de la connexion sécurisée (lot 8).
- Pas de téléversement de photos par le commerçant (validation de contenu à définir) ; ni de modification de l'adresse ou de la catégorie (validées par XPASS, lot 7).
- Pas d'annulation par le commerçant d'une réservation client (remboursement des crédits et notification : lots 6 à 8).
- Un seul établissement par compte affiché (le premier) ; le sélecteur multi-sites reste à faire.
- Pas de journal d'audit des modifications (lot 7) ; les changements émettent des événements dans l'outbox.

## 4 sexies. Lot 6 — détail (2 novembre 2026)

### Modèle (migration `0005`)

- `employer_contracts` : statut contractuel (brouillon, actif, suspendu, terminé), prix d'un crédit facturé à l'entreprise (unités mineures + devise du marché), délai de paiement.
- `employees` : salariés invités (e-mail normalisé, unique par organisation), statut (invité, actif, suspendu, retiré), compte utilisateur lié à l'acceptation.
- `budget_policies` : politique **versionnée** (une ligne par mois de début) : crédits par salarié et par mois, univers éligibles, validité des crédits.
- `employer_invoices` : factures de financement `FAC-AAAA-MM-NNNN` ; seule une facture **payée** alimente le financement disponible.
- `employer_allocations` : **une seule allocation par salarié et par mois** (index unique), liée au lot de crédits créé.
- Journal monétaire : nouveaux comptes `bank_cash` et `employer_prepaid` (virement reçu → financement prépayé → allocation).

### Règles appliquées

- Invitation individuelle ou **import CSV avec aperçu** : correspondance des colonnes (détection automatique ou choix manuel), lignes valides, doublons (dans le fichier ou déjà dans l'équipe), e-mails invalides ; l'aperçu ne crée rien, l'import revalide côté serveur et n'insère que les lignes valides (rejouable sans doublon).
- Le salarié accepte dans l'application, **connecté avec l'adresse invitée** : un autre compte ne voit ni ne peut accepter l'invitation.
- Allocation à l'acceptation, au paiement d'une facture et chaque heure (Celery) pour le mois en cours, uniquement si le **contrat est actif**, si la **politique** existe et si le **financement reçu couvre** le coût ; sinon le salarié attend et un événement « financement insuffisant » est émis. Verrou par organisation : des exécutions concurrentes ne dépassent jamais le financement.
- Crédits employeur : source « employeur », univers éligibles et expiration de la politique ; consommés selon l'ordre du lot 2.
- Suspendre ou retirer un salarié arrête les allocations **futures** ; les crédits déjà attribués restent acquis.
- Une politique ne change pas un mois déjà attribué : elle s'applique au mois choisi suivant.
- Confirmation d'un virement : réservée à l'administration XPASS (API prête, écran au lot 7).
- **Confidentialité** : les RH ne voient que des agrégats ; aucun détail de visite ; détail par catégorie masqué sous 10 salariés, y compris dans l'export CSV (protégé contre l'injection de formules).

### Données de démonstration

« Entreprise Démo Horizon » : contrat actif (1,00 € par crédit), politique de 100 crédits par mois, facture de financement de 5 000 € marquée démonstration et payée, six salariés invités dont `client@xpass.demo` (qui peut accepter dans l'application). Valeurs illustratives, aucun virement réel.

### Vérifications réellement exécutées (lot 6)

| Vérification | Résultat |
|---|---|
| `pytest` (PostgreSQL réel) | 95 tests réussis, dont 10 pour le lot 6 ; suite relancée deux fois |
| Droits | RH administrateur : écriture ; RH lecteur : lecture ; commerçant, client → 403 ; confirmation de virement réservée à l'administration |
| CSV | 2 valides, 2 doublons, 1 e-mail invalide détectés ; aperçu sans effet ; réimport sans doublon ; correspondance manuelle |
| Allocations | une seule par mois ; financement insuffisant → salarié en attente puis servi après paiement ; contrat suspendu → rien ; 4 exécutions parallèles → exactement 3 allocations |
| Rapports | consommation de 18 crédits employeur visible en total, détail par catégorie masqué ; export CSV |
| Flutter | `flutter analyze` sans problème, 14 tests réussis |
| Portails | `tsc`, `vitest`, `next build` OK |
| Navigateur | portail RH (indicateurs réels) → acceptation par `client@xpass.demo` dans l'app → 100 crédits employeur alloués → portail : salarié actif, 100 crédits, financement 4 900 €, calendrier et export CSV |

### Limites du lot 6

- **Aucun e-mail d'invitation envoyé** : l'événement est dans l'outbox, l'envoi attend la configuration d'un fournisseur d'e-mail. Les salariés acceptent depuis le Profil de l'application.
- La vérification de l'adresse e-mail repose sur la connexion : en démonstration, connexion sans mot de passe (lot 8 : OIDC).
- Pas de facture PDF ni de paiement en ligne par l'entreprise ; confirmation des virements par l'administration (écran au lot 7).
- Pas de modification individuelle du montant alloué à un salarié ; pas de répartition par taille d'équipe (maquette 25).
- Import CSV testé par l'API et par les tests ; le téléversement de fichier n'a pas été manipulé dans le navigateur.

## 4 septies. Lot 7 — détail (2 novembre 2026)

### Modèle (migration `0006`)

- `audit_events` : journal d'audit **en ajout seul** (modification et suppression refusées par trigger) : acteur (opérateur, système, client…), action, objet, motif, détails.
- `disputes` : réclamations `L-1001…`, une seule ouverte par réservation, statut, notes internes, restitution et ajustement appliqués, décision motivée.
- `credit_lots` : une seule restitution par (litige, lot d'origine).

### Fonctions

- **Vue d'ensemble** (maquette 26) : partenaires à vérifier, litiges ouverts, écarts de rapprochement, statut des versements, derniers événements du journal.
- **Validation d'un partenaire** (maquette 27) : contrôles calculés sur les données réelles, statut PSP distinct, décisions **motivées** (valider, demander des compléments, suspendre) et historique d'audit. Le statut PSP vient du webhook `account.updated` du prestataire ; en bac à sable seulement, l'administration peut simuler la vérification.
- **Modération** : masquer ou publier un établissement, avec motif.
- **Litiges** (maquette 28) : le client réclame depuis le reçu dans l'application (prestation utilisée ou annulation tardive, sous 30 jours) ; l'équipe met en analyse, demande des justificatifs, rejette ou **restitue** : les crédits consommés sont recréés **source par source** (validité d'au moins 30 jours) ; un ajustement partenaire, plafonné à ce qui lui revient, est déduit d'un prochain versement (un versement déjà payé n'est jamais modifié). Les notes internes ne sont jamais montrées au client.
- **Paiements et rapprochement** : versements en écart (clos avec motif) ou en échec (relancés), webhooks non appliqués (retraités ou classés avec motif), factures entreprises en attente (« Virement reçu »).
- **Audit** : journal filtrable ; écarts détectés et changements de statut PSP tracés comme événements « Système ».

### Droits

- `platform_admin` : toutes les actions.
- `platform_operator` : lecture, modération et litiges ; pas de validation commerciale ni d'action financière de rapprochement.

### Vérifications réellement exécutées (lot 7)

| Vérification | Résultat |
|---|---|
| `pytest` (PostgreSQL réel) | 104 tests réussis, dont 9 pour le lot 7 ; suite relancée deux fois |
| Droits | commerçant et RH → 403 ; opérateur sans décision commerciale ni rapprochement |
| Audit | motif obligatoire ; modification et suppression refusées en base |
| PSP | validation commerciale sans effet sur le statut PSP ; webhook `account.updated` → vérifié, tracé « Système » |
| Modération | établissement masqué → absent du catalogue, puis republié |
| Litiges | règles d'ouverture (non utilisée, autre client, doublon) ; restitution par source ; ajustement plafonné ; pas de seconde restitution ; rejet |
| Rapprochement | écart de transfert et webhook en attente visibles ; actions motivées et tracées |
| Flutter | `flutter analyze` sans problème, 16 tests réussis |
| Portails | `tsc`, `vitest`, `next build` OK |
| Navigateur | réclamation L-1001 envoyée depuis le reçu de l'app → dossier dans l'administration → restitution de 18 crédits (promotionnels) et ajustement de 15,00 € (`AV-1001`) déduit du prochain versement, journal d'audit à jour |

### Limites du lot 7

- Pas de téléversement ni d'examen de justificatifs (Kbis, identité) : contrôle d'identité délégué au prestataire de paiement.
- Pas de rapprochement bancaire automatique des virements entreprises : confirmation manuelle après contrôle du relevé.
- Pas de remboursement monétaire au client (paiements en crédits uniquement) ni d'échange de messages avec le client dans le dossier ; notification de la décision : lot 8.
- Pas de recherche globale dans l'administration ni de gestion des utilisateurs.

## 4 octies. Lot 8a — détail (2 novembre 2026)

Choix validés : **Keycloak** (fournisseur d'identité), **OpenStreetMap** (carte, lot 8b), lot 8 en deux étapes.

### Infrastructure locale

- `keycloak` (26.0.7) dans docker compose, realm `xpass` importé depuis `infra/keycloak/xpass-realm.json` : client public `xpass-mobile` (PKCE), client confidentiel `xpass-portals` (PKCE + secret côté serveur), audience `xpass-api`, inscription et vérification d'e-mail activées, langues fr/en/ar, comptes de **test** (`client@`, `partenaire@`, `rh@`, `admin@xpass.demo`, mot de passe de développement dans le fichier du realm). Console : http://localhost:8080 (admin de développement).
- `mailpit` : capture tous les e-mails (http://localhost:8025), n'envoie rien vers l'extérieur.

### Connexion (écran 02)

- Application : Authorization Code + **PKCE**, mot de passe saisi uniquement sur la page Keycloak. Web : redirection pleine page, le code est retiré de l'adresse dès le retour. Mobile : navigateur système (`flutter_web_auth_2`, retour `xpass://auth/callback`, configuré pour Android). Jetons dans le stockage sécurisé, renouvellement automatique 30 s avant expiration, déconnexion aussi chez Keycloak.
- Portails : flux serveur (Next.js), secret du client et jetons uniquement en cookies HttpOnly ; déconnexion chez Keycloak.
- API : à la première connexion, un compte existant (invitation RH, commerçant, démo) est **relié uniquement si l'e-mail est vérifié** par Keycloak ; sinon un compte client est créé. Un compte déjà relié à une autre identité n'est jamais repris. E-mail non vérifié, mauvaise audience, jeton expiré ou falsifié → 401.
- La connexion de démonstration reste disponible en développement (« Mode démonstration ») et est refusée en production.

### Profil et assistance (écran 16)

- Informations personnelles (nom affiché), pays, langue (enregistrée ; traduction de l'app au lot 8b), e-mails de réservation activables.
- Centre d'aide (questions fréquentes), **Contacter le support** (demandes `S-1001…`, 5 en cours au maximum), **Mes demandes** avec la réponse de l'équipe.
- **Exporter mes données** (JSON : compte, réservations, lots et mouvements de crédits, demandes, réclamations).
- **Supprimer mon compte** (confirmation « SUPPRIMER ») : refusée s'il reste des réservations à venir ou un accès professionnel ; efface l'identité, ferme le compte, conserve les écritures financières sans identité.
- Administration : nouvelle rubrique **Assistance** (réponse, clôture, audit).

### E-mails transactionnels

Envoyés **après commit** depuis l'outbox par Celery, uniquement si SMTP est configuré : réservation confirmée ou annulée, reçu, décision de réclamation, réponse du support, invitation salarié (non envoyée pour les salariés de démonstration). Préférence respectée pour les e-mails de réservation. Échec SMTP → nouvel essai (10 au plus). Jamais de QR, de code ni de lien de connexion dans un e-mail.

### Vérifications réellement exécutées (lot 8a)

| Vérification | Résultat |
|---|---|
| `pytest` (PostgreSQL réel) | 113 tests réussis, dont 9 pour le lot 8a (jetons RS256 réels, envoi SMTP réel vers Mailpit) |
| OIDC | première connexion crée un compte une seule fois ; liaison par e-mail vérifié ; refus : e-mail non vérifié, audience, expiration, signature, reprise par une autre identité |
| Compte | préférences ; export limité à l'utilisateur ; suppression refusée avec réservation à venir ou accès professionnel, puis effective |
| Flutter | `flutter analyze` sans problème, 21 tests réussis (PKCE, URL d'autorisation, renouvellement, écrans 02 et 16) |
| Portails | `tsc`, `vitest`, `next build` OK |
| Navigateur | portail : connexion Keycloak de `partenaire@xpass.demo` → compte commerçant existant relié ; app : écran 02 → Keycloak → `client@xpass.demo` relié, solde réel affiché, profil « Adresse e-mail vérifiée » ; demande S-1001 envoyée depuis l'app → réponse dans l'administration → e-mail reçu dans Mailpit |

### Corrigé pendant le lot 8a

- Realm : déclarer un « client scope » personnalisé supprimait les scopes standard (`profile`, `email`) ; l'audience est désormais un mappeur sur chaque client.
- Application : la demande `offline_access` était refusée aux comptes importés ; un jeton de rafraîchissement classique est utilisé.
- Application web : le retour de connexion est traité avant le démarrage du routeur (ouverture directe du Profil).

### Limites du lot 8a

- Connexion **mobile native** (Android/iOS) écrite mais non testée sur appareil ; la connexion par téléphone (onglet de la maquette 02) n'est pas proposée.
- Page Keycloak : thème XPASS ajouté après le lot 8b ; documents légaux (CGU, confidentialité) à rédiger, puis à renseigner via `TERMS_URL` / `PRIVACY_URL`.
- La suppression du compte XPASS ne supprime pas le compte chez Keycloak (à faire par l'API d'administration de Keycloak ou manuellement).
- Invitations des collaborateurs commerçants (comptes par site) : pas encore développées.
- Pas de notifications push ni de SMS.

## 4 nonies. Lot 8b — détail (2 novembre 2026)

Choix validé : **corail plus profond** pour le texte et les boutons (`#C73E28`, contraste 5,06:1 sur blanc) ; le corail de marque `#FF674F` (2,87:1, insuffisant pour du texte) reste réservé à la décoration. Texte lavande : `#5B53B8` (6,22:1).

### Ce qui fonctionne

- **Carte « Autour de moi » (écran 07)** : `/explore/autour`, accessible depuis l'accueil (icône carte) et depuis une catégorie (« Voir sur la carte », catégorie présélectionnée).
  - Tuiles OpenStreetMap (`MAP_TILE_URL`, attribution « © contributeurs OpenStreetMap » affichée).
  - Rayon 1 / 5 / 10 / 25 km (cercle dessiné), filtres catégorie et budget, prix en crédits sur chaque marqueur, bouton « Rechercher dans cette zone » après déplacement.
  - « Me localiser » : la permission n'est demandée qu'au clic ; refus ou service coupé → message clair, la carte reste sur la ville.
  - Fiche résumée du lieu sélectionné : distance, prix, itinéraire (ouvre Google Maps), « Voir la fiche ».
  - API : `GET /catalog/locations?lat&lng&radius_m` (100 m à 50 km, filtre PostGIS `ST_DWithin`) ; les cartes renvoient `latitude`/`longitude`. `radius_m` sans position → 422 `invalid_radius`.
- **Traductions FR / EN / AR** (fichiers ARB, `flutter gen-l10n`) : navigation, accueil, carte, connexion (02), profil (16), réservations et crédits (en-têtes). La langue choisie dans le Profil s'applique immédiatement et est enregistrée sur le compte ; l'arabe passe toute l'interface de droite à gauche.
- **Accessibilité** :
  - contrastes corrigés (app et portails) ;
  - marqueurs de carte annoncés comme boutons (« nom, N crédits ») ;
  - écran de connexion lisible avec un texte agrandi ×1,6 (test automatique) ;
  - portails : lien « Aller au contenu », contour de focus visible au clavier, animations réduites si le système le demande.

### Vérifications réellement exécutées (lot 8b)

| Commande | Résultat |
|---|---|
| `pytest` (PostgreSQL réel) | 114 tests réussis (dont recherche par rayon avec coordonnées) |
| `flutter analyze` / `flutter test` / `flutter build web` | aucun problème / 24 tests réussis (profil en arabe et en anglais avec sens de lecture, texte ×1,6) / build OK |
| Portails | `tsc`, `vitest` (5), `next build` OK |
| Navigateur (375 × 812) | carte : 11 lieux dans 5 km autour de Paris, sélection d'un marqueur → fiche ; profil et carte en arabe (RTL) ; retour en français |

### Corrigé pendant le lot 8b

- Écran de connexion : débordement de 262 px avec un grand texte (en-tête rendu extensible).
- Libellés coupés sur écran étroit (rayon « 25 km », boutons de la fiche).

### Passe de fidélité aux maquettes (après le lot 8b)

- Icônes au trait des maquettes (paquet `lucide_icons_flutter`) : pile de pièces pour les crédits, boussole, calendrier ; barre du bas refaite (Explorer actif en pastille corail, onglet actif souligné).
- « Autour de moi » refait d'après la maquette 07 : bulles « N crédits », filtres sur deux lignes (Date et Participants marqués « Bientôt »), piste des rayons, grande fiche avec « Itinéraire » et « Voir la fiche », bouton de recentrage, fond de carte adouci.
- Photos d'en-tête fondues à droite (univers 04 à 06, connexion 02, réservation 12, reçu 13, crédits 14, abonnement 15, profil 16), extraites des maquettes par `infra/seed-media/extract_placeholders.py` (dossier `screens/`) ; la Galerie des Lumières a désormais une photo.
- Portails (maquettes 18 à 28) : en-têtes à photo fondue (Règlements 22, Budgets 23, Salariés 24, Factures 25, vue d’ensemble commerçant), visuel dans l’encart du menu (commerçant, administration), vignettes d’établissement dans les files de l’administration (champ `image_key` ajouté aux files de `GET /admin/overview`), bouton « Examiner les demandes », encart « Prestations rapides » au planning, photos des prestations Brushing, Coloration et Barbe. Visuels dans `apps/portals/public/visuels/`.
- Écarts restants assumés : pas de photos de membres d’équipe ni de clients au planning (initiales), pas de cases « Capacité du jour », barre latérale claire ou sombre selon l’espace (les maquettes ne sont pas homogènes).
- Pages sécurisées (connexion, inscription, mot de passe oublié) : thème Keycloak `xpass` (`infra/keycloak/themes/xpass/login`, monté par docker-compose, `loginTheme` du realm) d’après la maquette 02 : photo d’accueil, onglets E-mail / Téléphone (téléphone marqué « Bientôt », non développé), bouton corail, « Créer un compte », « Explorer sans compte » (adresse `baseUrl` du client), FR / EN / AR (droite à gauche), photo à gauche et formulaire à droite sur grand écran.
- Comptes : comptes de démonstration fermés (`python -m app.seed.accounts remove-demo`), administrateur réel créé (`create-admin`), connexion sans mot de passe coupée, Keycloak persistant (volume `keycloak-data`). Accès commerçant et RH attribués par l’administration (`GET/POST /admin/access`, `POST /admin/access/{id}/revoke`, `GET /admin/organizations`) : compte préparé pour l’adresse, relié à la première connexion (e-mail vérifié), audit et e-mail `access.granted`.
- Réseau de commerçants réel : page publique `/devenir-partenaire`, candidature `/inscription-partenaire` (`GET /partners/siret/{siret}`, `POST /partners/applications`), SIRET contrôlé (clé de Luhn + annuaire SIRENE), adresse géocodée (Base Adresse Nationale, score conservé), partenaire « à vérifier » + établissement en brouillon + rôle responsable, e-mail `merchant.applied`, photos envoyées par le commerçant (`POST /partner/locations/{id}/cover`, `/offers/{id}/image`), contrôles SIRENE et adresse dans la fiche admin, lieux de démo masquables (`POST /admin/demo-locations`). Migration 0008.
- Équipe gérée par le commerçant : `GET/POST /partner/locations/{id}/access`, `POST …/access/{membership_id}/revoke` (responsable uniquement), rôles « Équipe » / « Responsable », e-mail d’invitation nommant l’invitant, garde-fous (pas d’auto-retrait, au moins un responsable), audit `actor_kind=partner`.
- Versements Stripe Connect : compte Express créé à la demande du responsable (`POST /partner/payout-account/onboarding`, clé d’idempotence par commerçant), lien d’inscription Stripe à usage unique, relecture du compte au retour (`/refresh`), espace Stripe (`/dashboard`), webhook `account.updated` accepté sur le secret principal ou Connect (`PSP_CONNECT_WEBHOOK_SECRET`), page de démonstration en bac à sable, carte « Compte de versement » dans Règlements. Non testé contre Stripe réel (clés de test nécessaires).
- Réseau et relation client : établissements multiples (`POST /partner/locations/{id}/siblings`, sélecteur), demandes de modification validées (`location_change_requests`, migration 0009), statistiques (`GET /partner/locations/{id}/stats`), messagerie par réservation, favoris, avis notés, appareils de notification, rappel de la veille (migration 0010, module `engagement`), filtres `day` et `participants` sur la recherche. Notifications Firebase : serveur prêt, **non configuré** (projet Firebase et intégration native à faire) ; enregistrement du téléphone dans l’app non branché.
- Ces photos restent des **recadrages des maquettes** (placeholders) à remplacer par des photos dont les droits sont acquis.

### Limites du lot 8b

- Traduction **partielle** : la fiche établissement, le calendrier, la réservation, le QR, les reçus, les réclamations et les catégories restent en français ; les contenus des établissements restent dans leur langue d'origine ; les unités (m, km) ne sont pas traduites. Les portails ne sont pas traduits.
- Filtres « Date » et « Participants » de la maquette 07 non développés.
- Les serveurs publics `tile.openstreetmap.org` ne doivent **pas** servir en production (politique d'usage) : prendre un fournisseur de tuiles (MapTiler, Stadia…) via `MAP_TILE_URL`.
- Interaction avec la carte non couverte par les tests automatiques (vérifiée à la main dans le navigateur) ; géolocalisation et carte non testées sur appareil natif.
- Pas d'audit d'accessibilité complet avec lecteur d'écran (TalkBack / VoiceOver / NVDA).

## 4 decies. Préparation au lancement — détail (2 novembre 2026)

Mise en œuvre de la liste « indispensable avant le lancement / fonctionnalités incomplètes / vérifications ».
Ce lot ne rend pas la plateforme « prête pour la production » : plusieurs étapes demandent des comptes et des
validations externes (voir « Reste à faire »).

### Ce qui fonctionne
- Kit de déploiement `infra/production/` (Caddy, Keycloak `start`, sauvegarde quotidienne, image standalone des
  portails), Sentry facultatif, guide `docs/DEPLOIEMENT.md`.
- Modèles de CGU, conditions partenaires, confidentialité et mentions légales, avec bandeau « à valider ».
- Application : identifiant `fr.xpass.app`, icône, écran de démarrage, permissions de localisation, signature de
  publication via `key.properties`, APK de publication construit (signé avec la clé de débogage faute de clé réelle).
- Traductions fr/en/ar du parcours de réservation (fiche, calendrier, confirmation, détail, reçu) ; « Besoin d'aide ? »
  ouvre le formulaire d'assistance.
- Paiement en ligne des factures entreprise (Stripe Checkout carte + SEPA, webhook signé et dédupliqué).
- Synchronisation RH par clé d'API (simulation, renommage, retrait des absents, audit).
- Dépendances mises à jour : FastAPI 0.162 / Starlette 1.10, pytest 9.0.3, Pillow 13, python-multipart 0.0.31,
  PyJWT 2.15 (fichier `requirements.lock` régénéré) ; portails Next 15.5.28, zod 4.

### Vérifications réellement exécutées
- Backend : 138 tests réussis contre PostgreSQL/PostGIS, avec les nouvelles versions installées dans l'image.
- `pip-audit` sur `requirements.lock` : aucune vulnérabilité connue ; `npm audit` portails : 0.
- Mobile : analyse sans erreur, 25 tests, build web et APK de publication.
- Portails : vérification des types, tests et build ; pages légales affichées ; pages connectées redirigées vers la
  connexion sans session (307).
- Test de charge local (lecture catalogue, recherche géographique, fiches ; Docker Desktop sous Windows) :
  1 client : médiane 15 ms, p95 21 ms ; 50 clients simultanés : 0 erreur, ~61 req/s avec 1 worker,
  ~100 req/s et p95 ≈ 1,4 s avec 4 workers. Mesure **non représentative d'un serveur** : à refaire sur l'hébergement réel.

### Reste à faire
- Vérifier dans le navigateur les pages connectées (commerçant : Messages, Avis, Statistiques, Paramètres,
  multi-établissements ; admin : Modération, Avis) avec un vrai compte : non fait, aucun compte de démonstration.
- Notifications push côté application (projet Firebase nécessaire), connexion par téléphone (fournisseur SMS).
- Traduction des portails et des écrans restants de l'application.
- Clés Stripe de test puis réelles, comptes Google Play / Apple, validation juridique, vraies photos et commerçants,
  essais sur téléphones réels et lecteurs d'écran.

## 4 undecies. Règles des crédits et réponse immédiate (4 novembre 2026)

### Ce qui fonctionne
- Prix variable par créneau (heure de pointe, forte demande, dernière minute), figé à la réserve, contrôle du prix affiché.
- Annulation tardive : moitié rendue ; absence détectée automatiquement (dette partenaire `no_show`).
- Report plafonné à un mois de formule, expiration en fin d'abonnement ; changement de formule au renouvellement
  (Stripe : tarif modifié sans prorata ; facture rattachée à la formule par son tarif ou son montant).
- Administration des formules (portail) ; écran abonnement de l'application (report, changement de formule).
- Réponse immédiate aux clics dans l'application et les portails.
- Migrations 0012 (prix, remboursements, absences) et 0013 (formule programmée).

### Vérifications réellement exécutées
- Backend : 154 tests (dont test_pricing.py et test_plans.py) ; prix neutres par défaut dans les tests, règles réelles
  dans les tests marqués `dynamic_pricing`.
- Mobile : analyse sans erreur, 25 tests. Portails : vérification des types, 5 tests, pages compilées (redirection
  vers la connexion sans session).

### Limites
- Pages connectées (formules, abonnement) non vues dans un navigateur avec une session.
- Prix de vente des formules à fixer par l'administration ; tarifs Stripe à créer.
- Changement de formule non testé contre Stripe réel (bac à sable seulement).

## 5. Services nécessitant des clés ou une configuration

| Service | Variable(s) | État |
|---|---|---|
| Fournisseur OIDC (production) | `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URL` | Adaptateur de vérification prêt ; fournisseur à choisir (Keycloak, Auth0, Cognito…). |
| PSP (paiements, abonnements, versements) | `PSP_PROVIDER=stripe`, `PSP_SECRET_KEY`, `PSP_WEBHOOK_SECRET`, `PSP_PRICE_ESSENTIEL`, `API_PUBLIC_URL`, `APP_PUBLIC_URL` | Adaptateur Stripe écrit (Checkout abonnement, transferts Connect) mais **jamais exécuté contre Stripe** : clés de test nécessaires. En local, `PSP_PROVIDER=sandbox` (refusé en production). |
| Stockage S3 production | `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | SeaweedFS en local. |
| Cartographie (écran 07) | `MAP_TILE_URL` (fournisseur de tuiles OpenStreetMap : MapTiler, Stadia…) | Carte livrée (lot 8b) ; en local, serveurs publics OSM, **à remplacer en production**. |
| E-mail / SMS (invitations RH, reçus) | `EMAIL_PROVIDER_*` | Lot 6. Aucun message externe envoyé. |
| Google Business (lien d'avis) | aucune clé : URL saisie par le partenaire | Lot 3. |

## 6. Points à confirmer avec le cahier des charges

- Règle exacte de conversion crédit ↔ euro par marché et durée de validité des crédits.
- Délai d'annulation par défaut (maquette : 24 h) et pénalités.
- Liste définitive des sous-catégories par univers.
- Fournisseur OIDC et PSP retenus.
- Seuil de masquage RH (prompt : 10 personnes) et périodes d'allocation (mensuelle ?).
