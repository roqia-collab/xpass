# Connexion « Continuer avec Google »

Le bouton « Continuer avec Google » apparaît en haut des pages de connexion et d'inscription (application,
portails) **dès que Google est activé** dans Keycloak. Tant que ce n'est pas fait, il n'est pas affiché.

Avec Google, l'adresse e-mail est déjà vérifiée par Google : pas de mot de passe à créer, pas d'e-mail de
vérification à attendre. Le compte XPASS est créé automatiquement à la première connexion.

## 1. Créer l'identifiant chez Google (gratuit, 10 minutes)

1. Aller sur <https://console.cloud.google.com/> avec le compte Google de l'entreprise et créer un projet « XPASS ».
2. **Google Auth Platform → Branding** (écran de consentement) : nom « XPASS », e-mail d'assistance, logo facultatif,
   liens vers la politique de confidentialité et les conditions (`https://<portails>/legal/confidentialite`, `/legal/cgu`).
3. **Audience** : « Externe ». Tant que l'application est en mode « Test », seuls les comptes ajoutés dans
   « Utilisateurs de test » peuvent se connecter. Cliquer « Publier l'application » pour l'ouvrir à tous
   (les autorisations demandées — nom, e-mail — ne nécessitent pas de vérification approfondie par Google).
4. **Clients → Créer un client** : type « Application Web », nom « XPASS Keycloak ».
   **URI de redirection autorisés** :
   - en local : `http://localhost:8080/realms/xpass/broker/google/endpoint`
   - en production : `https://auth.<votre-domaine>/realms/xpass/broker/google/endpoint`
5. Copier l'**ID client** et le **code secret du client**.

## 2. Activer Google dans XPASS

1. Dans `.env` (jamais dans Git, jamais dans un message) :
   ```
   GOOGLE_CLIENT_ID=…apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=…
   ```
2. Dans PowerShell, depuis le dossier `XPASS` :
   ```powershell
   docker compose up -d keycloak
   Get-Content infra/keycloak/activer-google.sh -Raw | docker compose exec -T keycloak sh -s
   ```
   Le script crée ou met à jour le fournisseur « google » (relancer après un changement de secret).
3. Désactiver : `Get-Content infra/keycloak/activer-google.sh -Raw | docker compose exec -T keycloak sh -s desactiver`

En production, mêmes variables dans `infra/production/.env`, puis la même commande avec
`docker compose -f docker-compose.prod.yml`.

## Comptes existants

Si une personne a déjà un compte XPASS avec la même adresse, Google le relie tout de suite : pas de mot de passe,
pas de lien de confirmation. Sinon le compte est créé. Le bouton des portails ouvre Google directement.

## Application mobile

L'application ouvre la page de connexion dans le navigateur du système (onglet sécurisé), ce que Google autorise ;
le bouton y apparaît donc aussi. À vérifier sur un vrai téléphone une fois Google activé.
