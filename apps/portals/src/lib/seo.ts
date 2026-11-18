import type { Metadata } from "next";

/**
 * Balises SEO des pages publiques de xpass.fr.
 *
 * Les valeurs par défaut restent dans le code (ci-dessous et dans les `metadata` existantes). L’administration
 * peut, après validation humaine d’une recommandation SEO, enregistrer une valeur pour UNE balise d’UNE page
 * (API : GET /api/v1/seo/pages). Ce module fusionne ces valeurs avec les valeurs par défaut. Sans valeur
 * enregistrée, ou si l’API ne répond pas, la page garde exactement ses balises d’origine.
 *
 * La liste des pages doit rester identique à `PAGES` dans backend/app/modules/seo/service.py.
 */

export type SeoField =
  | "title"
  | "description"
  | "canonical"
  | "og_title"
  | "og_description"
  | "og_image"
  | "twitter_card"
  | "twitter_title"
  | "twitter_description"
  | "twitter_image"
  | "robots"
  | "json_ld";

export type SeoValues = Partial<Record<SeoField, string>>;

export const SEO_FIELD_LABEL: Record<SeoField, string> = {
  title: "Balise title",
  description: "Meta description",
  canonical: "URL canonique",
  og_title: "Open Graph · titre",
  og_description: "Open Graph · description",
  og_image: "Open Graph · image",
  twitter_card: "Twitter Card · type",
  twitter_title: "Twitter Card · titre",
  twitter_description: "Twitter Card · description",
  twitter_image: "Twitter Card · image",
  robots: "Meta robots",
  json_ld: "Données structurées JSON-LD",
};

const SITE_DESCRIPTION = "Le pass crédits du sport, de la culture, de la beauté et des sorties.";
const SITE_ROBOTS = "noindex"; // app/layout.tsx : robots: { index: false }

/** Titres actuels des pages (repris de leurs `metadata`, gabarit « %s · XPASS » du layout). */
export const SEO_PAGES: Record<string, { title: string }> = {
  "/": { title: "XPASS" },
  "/demande": { title: "Demander un accès" },
  "/devenir-partenaire": { title: "Devenir partenaire" },
  "/legal/cgu": { title: "Conditions générales d’utilisation" },
  "/legal/partenaires": { title: "Conditions partenaires" },
  "/legal/confidentialite": { title: "Politique de confidentialité" },
  "/legal/mentions-legales": { title: "Mentions légales" },
};

/** Valeur que la page affiche quand aucune valeur n’est enregistrée (null = balise absente). */
export function defaultSeoValue(path: string, field: SeoField): string | null {
  const page = SEO_PAGES[path];
  if (!page) return null;
  if (field === "title") return path === "/" ? page.title : `${page.title} · XPASS`;
  if (field === "description") return SITE_DESCRIPTION;
  if (field === "robots") return SITE_ROBOTS;
  return null;
}

/** Fusionne les valeurs enregistrées avec les métadonnées par défaut d’une page. */
export function buildSeoMetadata(base: Metadata, values: SeoValues): Metadata {
  const meta: Metadata = { ...base };
  if (values.title) meta.title = { absolute: values.title };
  if (values.description) meta.description = values.description;
  if (values.robots) meta.robots = values.robots;
  if (values.canonical) meta.alternates = { ...base.alternates, canonical: values.canonical };
  if (values.og_title || values.og_description || values.og_image) {
    meta.openGraph = {
      ...base.openGraph,
      ...(values.og_title ? { title: values.og_title } : {}),
      ...(values.og_description ? { description: values.og_description } : {}),
      ...(values.og_image ? { images: [{ url: values.og_image }] } : {}),
      ...(values.canonical ? { url: values.canonical } : {}),
    };
  }
  if (values.twitter_card || values.twitter_title || values.twitter_description || values.twitter_image) {
    const card = values.twitter_card === "summary" ? "summary" : "summary_large_image";
    meta.twitter = {
      card,
      ...(values.twitter_title ? { title: values.twitter_title } : {}),
      ...(values.twitter_description ? { description: values.twitter_description } : {}),
      ...(values.twitter_image ? { images: [values.twitter_image] } : {}),
    };
  }
  return meta;
}

/**
 * Contenu sûr d’une balise <script type="application/ld+json"> : JSON re-sérialisé, `<`, `>` et `&` échappés
 * pour qu’aucune valeur ne puisse fermer la balise. Renvoie null si le JSON est invalide.
 */
export function safeJsonLd(raw: string | undefined): string | null {
  if (!raw) return null;
  try {
    const data: unknown = JSON.parse(raw);
    if (!data || typeof data !== "object") return null;
    return JSON.stringify(data)
      .replace(/</g, "\\u003c")
      .replace(/>/g, "\\u003e")
      .replace(/&/g, "\\u0026")
      .replace(/\u2028/g, "\\u2028")
      .replace(/\u2029/g, "\\u2029");
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------- administration

export type SeoReportStatus = "new" | "in_review" | "validated" | "applied" | "rejected";
export type SeoRecoStatus = "new" | "validated" | "rejected" | "applied" | "reverted";

export const REPORT_STATUS_LABEL: Record<SeoReportStatus, { label: string; tone: "lavender" | "coral" | "mint" | "grey" }> = {
  new: { label: "Nouveau", tone: "lavender" },
  in_review: { label: "En cours de validation", tone: "coral" },
  validated: { label: "Validé", tone: "mint" },
  applied: { label: "Appliqué", tone: "mint" },
  rejected: { label: "Rejeté", tone: "grey" },
};

export const RECO_STATUS_LABEL: Record<SeoRecoStatus, { label: string; tone: "lavender" | "coral" | "mint" | "grey" }> = {
  new: { label: "À décider", tone: "lavender" },
  validated: { label: "Validée, à appliquer", tone: "coral" },
  rejected: { label: "Rejetée", tone: "grey" },
  applied: { label: "Appliquée", tone: "mint" },
  reverted: { label: "Annulée", tone: "grey" },
};

export const PRIORITY_LABEL: Record<string, string> = {
  critical: "Critique",
  high: "Haute",
  medium: "Moyenne",
  low: "Basse",
};

/** Nom du fichier téléchargé : rapport-seo-xpass-AAAA-MM-JJ.md (date du rapport, heure de Paris). */
export function markdownFileName(createdAt: string): string {
  const day = new Intl.DateTimeFormat("fr-CA", { timeZone: "Europe/Paris", year: "numeric", month: "2-digit", day: "2-digit" }).format(
    new Date(createdAt),
  );
  return `rapport-seo-xpass-${day}.md`;
}

export type SeoReportRow = {
  id: string;
  report_id: string;
  site_url: string;
  report_created_at: string;
  received_at: string;
  status: SeoReportStatus;
  overall_score: number | null;
  recommendation_count: number;
  summary: string;
};

export type SeoRecommendation = {
  id: string;
  external_id: string;
  priority: string;
  category: string;
  field: SeoField | null;
  page_url: string;
  page_path: string | null;
  issue: string;
  current_value: string | null;
  suggested_value: string | null;
  edited_value: string | null;
  proposed_value: string | null;
  live_value: string | null;
  reason: string;
  status: SeoRecoStatus;
  applicable: boolean;
  not_applicable_reason: string | null;
  decision_note: string | null;
  decided_by_name: string | null;
  decided_at: string | null;
  applied_by_name: string | null;
  applied_at: string | null;
  last_error: string | null;
  last_error_at: string | null;
  active_change_id: string | null;
};

export type SeoReportDetail = SeoReportRow & { source: string; markdown_report: string; recommendations: SeoRecommendation[] };

export type SeoChange = {
  id: string;
  recommendation_id: string | null;
  report_id: string | null;
  page_path: string;
  field: SeoField;
  old_value: string | null;
  new_value: string;
  applied_by_name: string | null;
  applied_at: string;
  reverted_by_name: string | null;
  reverted_at: string | null;
  revertible: boolean;
};

/** Filtres de la liste : seules des valeurs attendues partent vers l’API. */
export function reportQuery(params: { statut?: string; du?: string; au?: string }): string {
  const qs = new URLSearchParams();
  if (params.statut && params.statut in REPORT_STATUS_LABEL) qs.set("status", params.statut);
  const day = /^\d{4}-\d{2}-\d{2}$/;
  if (params.du && day.test(params.du)) qs.set("date_from", params.du);
  if (params.au && day.test(params.au)) qs.set("date_to", params.au);
  const s = qs.toString();
  return s ? `?${s}` : "";
}
