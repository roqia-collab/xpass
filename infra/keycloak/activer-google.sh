#!/bin/sh
# Active (ou met à jour) « Continuer avec Google » dans le realm xpass. Sans effet sur les comptes existants.
#
# 1. Renseigner GOOGLE_CLIENT_ID et GOOGLE_CLIENT_SECRET dans .env (identifiant OAuth « Application Web »
#    créé dans Google Cloud ; voir docs/CONNEXION_GOOGLE.md). Ne jamais les publier.
# 2. docker compose up -d keycloak
# 3. docker compose exec -T keycloak sh -s < infra/keycloak/activer-google.sh
#
# Désactiver : docker compose exec -T keycloak sh -s desactiver < infra/keycloak/activer-google.sh
set -e
K=/opt/keycloak/bin/kcadm.sh
$K config credentials --server http://localhost:8080 --realm master \
  --user "${KC_BOOTSTRAP_ADMIN_USERNAME:-admin}" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null

if [ "$1" = "desactiver" ]; then
  $K update identity-provider/instances/google -r xpass -s enabled=false
  echo "Connexion Google désactivée."
  exit 0
fi

: "${GOOGLE_CLIENT_ID:?GOOGLE_CLIENT_ID manquant dans .env (puis docker compose up -d keycloak)}"
: "${GOOGLE_CLIENT_SECRET:?GOOGLE_CLIENT_SECRET manquant dans .env (puis docker compose up -d keycloak)}"

# trustEmail : l'adresse est déjà vérifiée par Google, pas de second e-mail de vérification.
# Flux « google » : si l'adresse existe, le compte est relié tout de suite ; sinon il est créé.
# Pas de formulaire, pas de mot de passe, pas de lien de confirmation.
if ! $K get authentication/flows/google -r xpass >/dev/null 2>&1; then
  $K create authentication/flows -r xpass -s alias=google -s providerId=basic-flow -s topLevel=true -s builtIn=false \
    -s "description=Connexion Google : relie ou crée le compte, sans mot de passe."
  $K create authentication/flows/google/executions/execution -r xpass -s provider=idp-auto-link
  $K create authentication/flows/google/executions/execution -r xpass -s provider=idp-create-user-if-unique
fi
$K get authentication/flows/google/executions -r xpass --fields id,providerId --format csv --noquotes | while IFS=, read -r id prov _; do
  case "$prov" in
    idp-auto-link|idp-create-user-if-unique)
      [ -n "$id" ] && $K update "authentication/flows/google/executions" -r xpass -b "{\"id\":\"$id\",\"requirement\":\"ALTERNATIVE\"}"
      ;;
  esac
done

if $K get identity-provider/instances/google -r xpass >/dev/null 2>&1; then
  $K update identity-provider/instances/google -r xpass -s enabled=true -s trustEmail=true \
    -s firstBrokerLoginFlowAlias=google \
    -s "config.clientId=$GOOGLE_CLIENT_ID" -s "config.clientSecret=$GOOGLE_CLIENT_SECRET" -s config.prompt=select_account
else
  $K create identity-provider/instances -r xpass -s alias=google -s providerId=google -s displayName=Google \
    -s enabled=true -s trustEmail=true -s storeToken=false -s firstBrokerLoginFlowAlias=google \
    -s "config.clientId=$GOOGLE_CLIENT_ID" -s "config.clientSecret=$GOOGLE_CLIENT_SECRET" \
    -s "config.defaultScope=openid profile email" -s config.syncMode=IMPORT -s config.prompt=select_account
fi
echo "Connexion Google activée. Adresse de retour à déclarer chez Google : <adresse Keycloak>/realms/xpass/broker/google/endpoint"
