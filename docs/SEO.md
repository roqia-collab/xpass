# Rapports SEO et balises des pages publiques

Un outil SEO externe envoie chaque jour un rapport sur https://xpass.fr. Les administrateurs le consultent
dans l’espace admin (menu **SEO**, `https://admin.xpass.fr/admin/seo`), valident ou rejettent chaque
recommandation, puis appliquent celles qui portent sur une balise d’une page.

**Rien n’est appliqué sans validation humaine.** Une recommandation suit trois étapes distinctes :
réception, validation (ou rejet), puis application avec une confirmation explicite.

## 1. Ce qui existe dans le code

| Élément | Où | Remarque |
|---|---|---|
| title, meta description, robots | API Metadata de Next.js (`apps/portals/src/app/layout.tsx` et `metadata` de chaque page) | `robots: { index: false }` est posé sur tout le site par le layout |
| Open Graph, Twitter Card, canonical, JSON-LD | n’existaient pas | ajoutés par page, uniquement quand une valeur a été appliquée |
| robots.txt, sitemap | n’existent pas | catégories validables mais **appliquées à la main** (elles concernent tout le site, pas une page) |

Les valeurs appliquées depuis l’admin se superposent aux valeurs du code, balise par balise et page par page
(`apps/portals/src/lib/seo.ts`). Sans valeur enregistrée, ou si l’API ne répond pas, une page garde
exactement ses balises d’origine.

Pages gérées : `/`, `/demande`, `/devenir-partenaire`, `/legal/cgu`, `/legal/partenaires`,
`/legal/confidentialite`, `/legal/mentions-legales`. Pour en ajouter une, il faut la déclarer dans
`PAGES` (`backend/app/modules/seo/service.py`) **et** dans `SEO_PAGES` (`apps/portals/src/lib/seo.ts`), puis
appeler `seoMetadata()` et `<SeoJsonLd>` dans la page.

## 2. Variables d’environnement

| Variable | Où | Valeur |
|---|---|---|
| `SEO_REPORT_WEBHOOK_SECRET` | API (`.env` en local, `infra/production/.env.production` sur le VPS) | secret partagé avec l’outil SEO, **32 caractères minimum**. Vide = réception désactivée (réponse 503). Une valeur trop courte empêche l’API de démarrer. |
| `SEO_REPORT_MAX_BYTES` | API, facultatif | taille maximale d’un rapport, 1 000 000 octets par défaut |
| `SEO_REPORT_RATE_PER_HOUR` | API, facultatif | envois acceptés par heure et par adresse d’origine, 30 par défaut |

Générer un secret :

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Le secret ne doit jamais être écrit dans Git, ni dans un ticket, ni dans les journaux : l’API ne l’écrit
nulle part et ne le renvoie jamais. Rien n’est à ajouter côté Hostinger (portails).

## 3. Point d’entrée de réception

`POST https://api.xpass.fr/api/v1/admin/seo/reports`

Le chemin suit les conventions de l’API (`/api/v1/admin/...`). L’authentification se fait par le seul secret
partagé : un jeton de session administrateur ne permet pas d’envoyer un rapport, et le secret ne donne pas
accès à la consultation.

En-têtes :

```
Authorization: Bearer <SEO_REPORT_WEBHOOK_SECRET>
Content-Type: application/json
```

Réponses :

| Code | Sens |
|---|---|
| 201 | rapport enregistré : `{"id": "…", "reportId": "…", "status": "new", "recommendations": 3}` |
| 400 `invalid_json` | le corps n’est pas un JSON valide |
| 401 `unauthorized` | en-tête absent ou secret incorrect |
| 409 `duplicate_report` | un rapport avec ce `reportId` a déjà été reçu (rien n’est modifié) |
| 413 `payload_too_large` | rapport plus gros que `SEO_REPORT_MAX_BYTES` |
| 422 `invalid_report` | format invalide ; `detail.errors` liste les champs en cause (20 au plus) |
| 429 `too_many_requests` | trop d’envois dans l’heure (`Retry-After: 3600`) |
| 503 `seo_reports_disabled` | `SEO_REPORT_WEBHOOK_SECRET` n’est pas configuré |

Le rapport est enregistré en entier : date, adresse d’origine (`source`), contenu JSON complet
(`seo_reports.payload`), Markdown et une ligne par recommandation.

## 4. Format JSON

```json
{
  "reportId": "2026-11-17-xpass",
  "siteUrl": "https://xpass.fr",
  "createdAt": "2026-11-17T06:00:00+01:00",
  "summary": "3 points à corriger.",
  "overallScore": 72,
  "recommendations": [
    {
      "id": "r1",
      "priority": "high",
      "category": "title",
      "pageUrl": "https://xpass.fr/demande",
      "issue": "Titre trop court",
      "currentValue": "Demander un accès · XPASS",
      "suggestedValue": "Demander un accès XPASS pour votre entreprise",
      "reason": "Un titre plus descriptif améliore le taux de clic.",
      "status": "open"
    }
  ],
  "markdownReport": "# Rapport SEO du 17 novembre 2026\n…"
}
```

Règles de validation (les champs inconnus sont refusés) :

| Champ | Règle |
|---|---|
| `reportId`, `recommendations[].id` | 1 à 100 caractères `A-Z a-z 0-9 . _ : -`, commençant par une lettre ou un chiffre ; `id` unique dans le rapport |
| `siteUrl` | adresse `https://` |
| `createdAt` | date ISO 8601 **avec fuseau** (`Z` ou `+01:00`) |
| `overallScore` | entier de 0 à 100, ou `null` |
| `recommendations` | 300 au plus |
| `priority` | `critical`, `high`, `medium` ou `low` |
| `category` | voir ci-dessous ; les tirets et espaces deviennent `_` |
| `pageUrl` | adresse `http(s)://` ; seules les pages de `xpass.fr` / `www.xpass.fr` sont applicables |
| `currentValue`, `suggestedValue` | texte ou `null` |
| `status` | facultatif, gardé à titre d’information (le statut de décision est géré par XPASS) |
| `markdownReport` | 800 000 caractères au plus |

Catégories applicables automatiquement, et balise touchée :

| `category` | Balise |
|---|---|
| `title`, `meta_title` | `<title>` (valeur complète, sans le suffixe « · XPASS ») |
| `meta_description`, `description` | `<meta name="description">` |
| `canonical` | `<link rel="canonical">` (https, sur xpass.fr uniquement) |
| `og_title`, `og_description`, `og_image` (ou `open_graph_…`) | Open Graph |
| `twitter_card` (`summary` / `summary_large_image`), `twitter_title`, `twitter_description`, `twitter_image` | Twitter Card |
| `robots`, `meta_robots` | `<meta name="robots">` (ex. `index, follow`) |
| `json_ld`, `jsonld`, `structured_data` | `<script type="application/ld+json">` (objet ou liste JSON) |

Toute autre catégorie (`robots_txt`, `sitemap`, `content`, `performance`…) est acceptée, affichée et
peut être validée ou rejetée, mais doit être appliquée à la main dans le code.

## 5. Valider et appliquer une recommandation

Réservé aux comptes **administrateur** (`platform_admin`). Un opérateur (`platform_operator`) voit le menu
mais l’API lui refuse l’accès (403).

1. **SEO** : la liste montre la date, le statut (Nouveau, En cours de validation, Validé, Appliqué,
   Rejeté), le score et le nombre de recommandations. Les filtres portent sur le statut et sur la date du
   rapport (heure de Paris). **Markdown** télécharge `rapport-seo-xpass-AAAA-MM-JJ.md`.
2. **Ouvrir** un rapport. Pour chaque recommandation :
   - **Valider** : accepte la valeur proposée. Rien ne change encore sur le site.
   - **Modifier avant validation** : corrigez la valeur, puis **Valider la valeur modifiée**.
   - **Rejeter** : une note de 5 caractères au moins est obligatoire.
   - **Appliquer…** (recommandations validées et applicables) : un encadré montre la page, la catégorie,
     la valeur actuelle sur le site et la nouvelle valeur. Il faut cocher la confirmation puis cliquer sur
     **Confirmer l’application**.
3. La page publique affiche la nouvelle valeur au plus tard 5 minutes après (cache de Next.js, vidé
   aussitôt sur le même serveur).

Chaque décision est enregistrée sur la recommandation (qui, quand, note), et dans le journal d’audit
(menu **Audit**, filtre « SEO »). Une erreur d’application, par exemple une valeur refusée, reste affichée
sur la recommandation.

Le statut du rapport se recalcule à chaque décision : Nouveau (rien de décidé), En cours de validation
(une partie décidée), Validé (tout est décidé, il reste des validations à appliquer), Appliqué (tout ce qui
a été validé est appliqué), Rejeté (tout a été rejeté).

## 6. Historique et retour arrière

**SEO → Historique des modifications** liste chaque application : page, balise, ancienne valeur (ou « valeur
par défaut du code »), nouvelle valeur, auteur, date et annulation éventuelle.

**Annuler** restaure l’ancienne valeur, ou supprime la surcharge si la balise venait du code. Seule la
modification la plus récente d’une balise de page peut être annulée : pour revenir plus loin, annulez dans
l’ordre inverse. La recommandation passe en « Annulée » ; elle peut être validée et appliquée de nouveau.

En dernier recours (API indisponible, valeur bloquante), supprimer les surcharges remet toutes les pages sur
les valeurs du code :

```sql
DELETE FROM seo_page_overrides;               -- toutes les pages
DELETE FROM seo_page_overrides WHERE page_path = '/demande';
```

L’historique (`seo_changes`) n’est pas modifié par ces commandes.

## 7. Tester

En local (`docker compose up -d`, portails en `npm run dev`) :

1. Mettez un secret d’au moins 32 caractères dans `SEO_REPORT_WEBHOOK_SECRET` (fichier `.env` à la racine,
   jamais commité), puis `docker compose up -d --build api` pour appliquer la migration `0020`.
2. Envoyez un rapport :

```bash
curl -i -X POST http://localhost:8000/api/v1/admin/seo/reports -H "Authorization: Bearer $SEO_REPORT_WEBHOOK_SECRET" -H "Content-Type: application/json" -d '{"reportId":"test-1","siteUrl":"https://xpass.fr","createdAt":"2026-11-17T06:00:00Z","summary":"Test","overallScore":70,"recommendations":[{"id":"r1","priority":"high","category":"title","pageUrl":"https://xpass.fr/demande","issue":"Titre trop court","currentValue":"Demander un accès · XPASS","suggestedValue":"Demander un accès XPASS","reason":"Test"}],"markdownReport":"# Rapport de test"}'
```

3. Connectez-vous à http://localhost:3000/admin/seo avec `admin@xpass.demo`, validez puis appliquez, et
   vérifiez le `<title>` de http://localhost:3000/demande.

Tests automatiques :

```bash
docker compose exec api pytest -q tests/test_seo.py
```

```bash
cd apps/portals && npx vitest run
```

Les tests backend couvrent : rapport valide, refus sans jeton ou avec un mauvais jeton, réception désactivée,
JSON mal formé et format invalide, doublon, taille, limite de requêtes, droits administrateur, liste et
filtres, téléchargement Markdown, validation, rejet, application limitée à la page choisie, historique,
retour arrière et contrôle des valeurs. Les tests des portails couvrent la fusion des balises,
l’échappement du JSON-LD, le rendu Markdown sans HTML, le nom du fichier, les statuts et les filtres.

## 8. Déploiement

1. **API (VPS)** : ajoutez `SEO_REPORT_WEBHOOK_SECRET` dans `infra/production/.env.production`, puis
   reconstruisez l’API. La migration `0020_rapports_seo` (4 tables, aucune table existante modifiée)
   s’exécute au démarrage, comme les autres (`alembic upgrade head`).
2. **Portails (Hostinger)** : redéploiement automatique depuis `main` de `roqia-collab/xpass`, après
   fusion de la demande de fusion. Aucune variable nouvelle.
3. Donnez l’adresse et le secret à l’outil SEO par un canal sûr, puis envoyez un premier rapport de test.

Retour arrière du déploiement : annulez d’abord les balises appliquées (§ 6). La migration se défait avec
`alembic downgrade 0019`, qui supprime les tables SEO **et leur contenu**.

## 9. Hypothèses

- La limite de requêtes est gardée en mémoire : l’API tourne en un seul processus uvicorn. Elle compte par
  adresse vue par l’API ; derrière le proxy, tous les envois peuvent partager la même adresse, ce qui en fait
  une limite globale de 30 envois par heure.
- Le rapport ne porte que sur xpass.fr : les pages des autres domaines sont enregistrées mais jamais
  appliquées.
- `robots: { index: false }` reste la valeur par défaut du site. Une recommandation `robots` appliquée ne
  rend indexable que sa page.
- Seuls les administrateurs (`platform_admin`) ont accès à la section, pas les opérateurs.
