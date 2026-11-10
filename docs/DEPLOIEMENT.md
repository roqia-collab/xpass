# Mise en production de XPASS

Guide pas à pas pour un premier déploiement sur **un serveur** (Docker). Les fichiers sont dans
`infra/production/`. Rien ici n'est « prêt » tant que les vérifications de la fin ne sont pas faites.

## 1. Ce qu'il vous faut (à votre nom)

| Élément | Exemple | Pourquoi |
|---|---|---|
| Serveur Linux (4 vCPU, 8 Go, 80 Go SSD) avec Docker | Scaleway, OVHcloud, Hetzner | héberger l'API, les portails, Keycloak, la base |
| Nom de domaine | `xpass.fr` | sous-domaines : `app.` (XPASS), `admin.`, `rh.`, `pro.` (commerçant), `api.`, `auth.` |
| Fournisseur d'e-mails (SMTP) | Brevo, Mailjet, Amazon SES | confirmations, rappels, réinitialisation de mot de passe |
| Stockage compatible S3 | Scaleway Object Storage, OVHcloud | photos des établissements |
| Compte Stripe (Connect activé) | stripe.com | abonnements et versements aux commerçants |
| Fournisseur de fonds de carte | MapTiler, Stadia Maps | la carte « Autour de moi » (les serveurs publics OSM sont interdits en production) |
| *(facultatif)* Projet Firebase | console.firebase.google.com | notifications sur téléphone |
| *(facultatif)* Sentry | sentry.io | suivi des erreurs |

## 2. DNS

Créez des enregistrements de type **A** vers l'adresse IP du serveur : `app` (application XPASS), `admin`, `rh`, `pro` (commerçant), `api`, `auth`.

## 3. Configuration

```bash
git clone <votre dépôt> xpass && cd xpass/XPASS
cp infra/production/.env.production.example infra/production/.env.production
# Remplir le fichier (secrets : python3 -c "import secrets; print(secrets.token_urlsafe(48))")
python3 infra/production/make_realm.py --domain xpass.fr --portals-secret "<même valeur que OIDC_PORTALS_CLIENT_SECRET>" \
  --smtp-host <hôte SMTP> --smtp-user <utilisateur> --smtp-from no-reply@xpass.fr
```

Construisez la version web de l'application (les adresses sont figées à la compilation) :

```bash
cd apps/mobile
flutter build web --release --dart-define=API_BASE_URL=https://api.xpass.fr \
  --dart-define=MEDIA_BASE_URL=<adresse publique du bucket> \
  --dart-define=OIDC_ISSUER=https://auth.xpass.fr/realms/xpass \
  --dart-define=MAP_TILE_URL=<URL des tuiles de votre fournisseur> \
  --dart-define=TERMS_URL=https://pro.xpass.fr/legal/cgu --dart-define=PRIVACY_URL=https://pro.xpass.fr/legal/confidentialite
cd ../..
```

## 4. Démarrage

```bash
docker compose -f infra/production/docker-compose.prod.yml --env-file infra/production/.env.production up -d --build
docker compose -f infra/production/docker-compose.prod.yml --env-file infra/production/.env.production logs -f api
```

Caddy obtient les certificats HTTPS tout seul (ports 80 et 443 ouverts). Les migrations de la base
s'appliquent au démarrage de l'API. Le catalogue est vide : **pas de données de démonstration en production**.

## 5. Premier administrateur

1. Créez votre compte : `https://app.xpass.fr` → Profil → « Créer un compte » (e-mail vérifié).
2. Donnez-lui le rôle d'administrateur :
   ```bash
   docker compose -f infra/production/docker-compose.prod.yml --env-file infra/production/.env.production \
     exec api python -m app.seed.accounts create-admin --email vous@xpass.fr --name "Prénom Nom"
   ```
3. Connectez-vous sur `https://pro.xpass.fr`.

La console Keycloak n'est **pas** publique. Pour y accéder (mot de passe SMTP, réglages) :
`ssh -L 8080:localhost:8080 serveur` puis, sur le serveur, `docker compose … exec keycloak` n'est pas
nécessaire : ajoutez temporairement `ports: ["127.0.0.1:8080:8080"]` au service keycloak et ouvrez
`http://localhost:8080/admin` via le tunnel. Retirez ce port ensuite.

## 6. Stripe

1. Mode **test** d'abord (`sk_test_…`). Activez Connect (comptes Express).
2. Webhook « compte » vers `https://api.xpass.fr/api/v1/payments/webhooks/stripe` (événements `checkout.session.completed`,
   `invoice.*`, `customer.subscription.*`, `transfer.*`) → secret dans `PSP_WEBHOOK_SECRET`.
3. Webhook « comptes connectés » vers la même adresse (événement `account.updated`) → `PSP_CONNECT_WEBHOOK_SECRET`.
4. Créez le tarif de la formule et reportez son identifiant dans `PSP_PRICE_ESSENTIEL`.
5. Faites un abonnement test et l'ouverture d'un compte de versement test, puis passez en `sk_live_…`.

## 7. Sauvegardes

Le service `backup` fait un `pg_dump` quotidien des bases `xpass` et `keycloak` (14 jours). **Copiez-les hors du
serveur** (par exemple chaque nuit vers votre stockage S3) :

```bash
docker run --rm -v xpass-prod_backups:/b alpine ls -lh /b      # vérifier
```

Restauration : `pg_restore --clean --if-exists -d xpass <fichier>.dump`. **Testez une restauration** avant d'ouvrir.

## 8. Vérifications avant d'ouvrir au public

- [ ] `https://api.xpass.fr/health` répond `ok` ; certificats valides sur les 4 sous-domaines.
- [ ] Inscription client, connexion, réinitialisation du mot de passe (e-mail reçu).
- [ ] Inscription d'un commerçant avec un vrai SIRET, validation, publication, réservation, scan du QR, reçu.
- [ ] Abonnement Stripe en mode test ; compte de versement test ; versement hebdomadaire.
- [ ] Une sauvegarde restaurée sur une base de test.
- [ ] Documents légaux validés par un juriste et en ligne (`/legal/...`).
- [ ] Photos de démonstration remplacées par des photos dont vous avez les droits.

## 9. Mises à jour

```bash
git pull
docker compose -f infra/production/docker-compose.prod.yml --env-file infra/production/.env.production up -d --build
```
