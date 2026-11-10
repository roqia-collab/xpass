# Prompt de démarrage XPASS pour Claude Code

Tu es le développeur principal du projet XPASS. Travaille dans le dépôt courant et construis une application réelle, maintenable et exécutable. Lis d’abord les fichiers présents, les éventuels AGENTS.md, le cahier des charges technique XPASS et les maquettes fournies. Ne remplace pas un projet existant sans analyser son état.

## Projet

XPASS permet aux clients de découvrir des expériences de divertissement, sport, culture et beauté, de financer leurs réservations avec des crédits personnels, employeur ou promotionnels, puis de présenter un QR éphémère au partenaire. Il comprend une application mobile cliente et trois portails web : commerçant, entreprise RH et administration.

Développeuse : Benaboud Roqia. Directeur : Zaki Mohamed Mehri. Ces noms figurent dans la documentation du projet ; ne les utilise pas comme faux noms de clients dans les interfaces.

## Architecture à appliquer

- Mobile : Flutter et Dart, Riverpod, go_router, Dio, stockage sécurisé des jetons.
- Web : Next.js et TypeScript ; espaces /partner, /company et /admin ; formulaires React Hook Form et Zod ; TanStack Query pour les données clientes.
- Backend : FastAPI et Python, Pydantic, SQLAlchemy, Alembic ; API REST /api/v1 et schéma OpenAPI.
- Données : PostgreSQL avec PostGIS et btree_gist. Redis et Celery pour les tâches différées ; PostgreSQL reste la vérité des crédits et réservations.
- Fichiers : stockage compatible S3 ; MinIO pour le développement local, espaces publics et privés séparés.
- Authentification : OIDC avec un fournisseur configurable. Prévoir un fournisseur local de développement ou une configuration documentée, jamais un contournement d’authentification activé en production.
- Environnement local : Docker Compose pour API, PostgreSQL, Redis, worker, scheduler et stockage. Les frontends peuvent tourner localement avec leurs outils habituels.

Structure attendue :

```text
xpass/
  apps/mobile/
  apps/portals/
  backend/app/api/v1/
  backend/app/modules/
  backend/app/core/
  backend/app/db/
  backend/app/workers/
  backend/migrations/
  backend/tests/
  contracts/
  infra/
  docs/
```

Sépare routeurs HTTP, services métier, repositories, modèles et schémas de réponse. Le mobile et le web n’accèdent jamais directement à PostgreSQL. Les appels privés web passent par une couche serveur BFF avec session protégée et cookie HttpOnly, Secure en production et SameSite. Protège les mutations contre le CSRF. Le mobile utilise son client API authentifié.

## Direction visuelle

Reproduis la direction des 28 maquettes, avec des composants de code et des mises en page responsives. Ne transforme pas une capture d’écran en page interactive en posant des boutons au-dessus d’une image.

Palette : crème #FAF8F3, bleu nuit #121A35, corail #FF674F, lavande secondaire. Grandes photos pour la découverte, cartes arrondies, typographie lisible et professionnelle, icônes cohérentes. Navigation mobile fixe : Explorer, Réservations, Mes crédits, Profil. Un bouton principal par écran lorsque le parcours s’y prête. Interface française, traductions préparées pour anglais et arabe RTL, contrastes et libellés accessibles.

Les maquettes contiennent des données et certains textes illustratifs : harmonise le même établissement, ses photos, sa ville, sa prestation et ses dates pendant tout un parcours. Les règles du cahier technique priment sur une erreur de libellé dans une image. Les PNG sont des références visuelles complètes ; les photos qui y sont intégrées ne sont pas des assets photo indépendants. Prévois des composants média, des fichiers de remplacement explicites et les emplacements d’assets ; n’invente pas de droits sur des photos réelles.

## Périmètre fonctionnel

1. Client : exploration publique, quatre univers, recherche, filtres, carte et liste, fiche partenaire, choix prestation/professionnel/date/heure, récapitulatif, réservation, annulation, QR, reçu, crédits, abonnement, profil et support.
2. Commerçant : établissement, offres, horaires et exceptions, ressources et équipe, planning, scan ou code manuel, aperçu avant consommation, confirmation et règlements.
3. RH : organisation, invitations individuelles et CSV avec aperçu des erreurs, salariés, politiques de budget, financement, factures et rapports agrégés.
4. Administration : validation commerciale et statut PSP distincts, modération, litiges, restitution des crédits, ajustements partenaires, rapprochement et audit.
5. Agenda : ajout volontaire au calendrier natif, Google Calendar ou ICS après confirmation, sans jeton QR dans l’événement.
6. Avis Google : lien neutre de l’établissement après consommation validée, sans récompense et sans publication automatique.

## Invariants métier obligatoires

- Tous les prix, soldes et permissions sont contrôlés côté serveur. Aucun crédit n’est ajouté sur un simple retour de paiement dans le navigateur.
- Isoler les marchés et leurs devises. Les crédits sont des entiers ; l’argent est stocké en unités mineures entières avec devise. Ne jamais confondre les deux.
- Distinguer crédits disponibles, réservés et consommés. Conserver les sources personnelles, employeur et promotionnelles, l’éligibilité et les dates d’expiration.
- Utiliser un journal append-only équilibré et des contre-écritures pour les corrections. Les projections de solde restent transactionnelles et reconstruisibles.
- Une réserve HELD bloque capacité et crédits pendant cinq minutes maximum. La confirmation conserve la version de prix et la politique ; un créneau complet est refusé.
- Utiliser transactions, verrous et contraintes : pas de sur-réservation, pas de solde négatif, pas de double consommation. Ressources exclusives protégées par exclusion de plages actives ; inventaire collectif verrouillé.
- Le QR est opaque, éphémère, rattaché à une réservation et au bon site ; empreinte stockée côté serveur. Le scan ouvre un aperçu ; seule la confirmation consomme. Pas de validation financière hors ligne.
- Chaque commande sensible a une clé d’idempotence et une empreinte du corps. Le même effet métier ne peut pas être créé deux fois avec une autre clé.
- Les webhooks sont signés, persistés durablement et dédupliqués. L’allocation a une unicité par facture ; le financement employeur respecte le statut contractuel prévu.
- Une allocation employeur est unique par membre et période, même si la version de politique change. Les dates de période sont normalisées.
- Les permissions portent sur l’objet, le site, l’organisation et le marché. Le RH n’accède jamais aux visites nominatives ; les agrégats de moins de dix personnes sont masqués, y compris dans les exports.
- Une consommation écrit atomiquement le mouvement de crédits, le reçu, la dette partenaire et l’outbox. Les appels externes sont réalisés après commit par des tâches rejouables.
- Prévoir refus de permission caméra/localisation, absence de résultats, réseau indisponible et timeout après commit. Ne jamais afficher un succès inventé.

## Base de données

Construis les migrations et les relations pour users, markets, merchants, locations, memberships, offers, offer_versions, categories, resources, horaires et exceptions, inventaire, bookings, occupations de ressources, blocages externes, qr_tokens, redemptions, wallets, credit_lots, credit_reservations, projections, journaux et lignes de crédits, journaux monétaires, abonnements, factures, webhooks, dettes et versements partenaires, organizations, politiques, invitations, salariés, allocations, dossiers de support, audit, idempotence et outbox.

Une occupation exclusive correspond à une réservation OU un blocage externe, jamais aux deux. Un trigger différé ou un mécanisme transactionnel équivalent vérifie l’équilibre des journaux. Les CHECK de ligne seuls ne suffisent pas à vérifier une somme interlignes.

## Méthode de travail et première livraison

1. Analyse le dépôt et les documents. Crée docs/PLAN_IMPLEMENTATION.md avec les lots, les décisions explicites et les points restant à configurer. Résume ton plan brièvement puis commence le code sans attendre une validation de chaque fichier.
2. Réalise d’abord une tranche verticale fonctionnelle : infrastructure locale, FastAPI, migrations de catalogue, fixtures synthétiques, endpoints de recherche/fiche, application Flutter Explorer et catégories, layout et connexion des portails. Les offres affichées proviennent de l’API et de PostgreSQL, pas de tableaux factices enfouis dans les widgets.
3. Prépare les contrats des modules suivants sans prétendre que réservation, QR ou paiements sont terminés. Une fonction non développée doit être clairement identifiée et ne doit jamais simuler un vrai succès financier.
4. Poursuis ensuite par disponibilités, portefeuille et réservation transactionnelle, QR, paiements et règlements, RH, administration puis finitions. Maintiens la liste d’avancement et les dépendances entre lots.
5. Pour les services nécessitant des clés, crée l’adaptateur et les variables d’environnement, documente la configuration manquante et continue les tâches indépendantes. Un mode sandbox ou démonstration doit être explicitement identifié et impossible à activer accidentellement en production.
6. Ne remplace pas Flutter par une simple page web. Si Flutter ou un autre outil manque dans l’environnement, écris le projet attendu, indique précisément les vérifications impossibles et ne déclare pas ces tests réussis.

## Qualité et livraison

Fournis .env.example sans secrets, dépendances verrouillées, scripts de démarrage, healthchecks, README et procédure de migration. Utilise des données synthétiques marquées comme démonstration ; aucun vrai paiement ni message externe n’est envoyé sans configuration et autorisation.

Exécute les vérifications disponibles et pertinentes : backend avec PostgreSQL réel pour les transactions, analyse et tests Flutter, TypeScript et tests des portails. Les tests de concurrence et d’idempotence sont indispensables avant d’annoncer le parcours financier terminé.

À la fin de chaque lot, indique ce qui fonctionne, les fichiers importants, les commandes exactes pour démarrer et tester, les tests réellement exécutés et les limites restantes. Ne dis pas « prêt pour production » si les paiements, la sécurité ou les tests de reprise restent à réaliser.

Commence maintenant par l’analyse du dépôt, puis implémente la première tranche verticale exécutable.
