import "server-only";

import type { Metadata } from "next";

import { buildSeoMetadata, safeJsonLd, type SeoValues } from "./seo";
import { apiUrl } from "./session";

export const SEO_CACHE_TAG = "seo";

/** Valeurs SEO validées et appliquées pour une page. En cas d’erreur : aucune (la page garde ses balises). */
export async function fetchSeoValues(path: string): Promise<SeoValues> {
  try {
    const res = await fetch(`${apiUrl()}/api/v1/seo/pages?path=${encodeURIComponent(path)}`, {
      headers: { Accept: "application/json" },
      next: { revalidate: 300, tags: [SEO_CACHE_TAG] },
      signal: AbortSignal.timeout(2_000),
    });
    if (!res.ok) return {};
    const body = (await res.json()) as { values?: Record<string, unknown> };
    const values: SeoValues = {};
    for (const [k, v] of Object.entries(body.values ?? {})) {
      if (typeof v === "string") (values as Record<string, string>)[k] = v;
    }
    return values;
  } catch {
    return {};
  }
}

export async function seoMetadata(path: string, base: Metadata): Promise<Metadata> {
  return buildSeoMetadata(base, await fetchSeoValues(path));
}

/** Données structurées de la page, si une valeur JSON-LD a été appliquée. */
export async function SeoJsonLd({ path }: { path: string }) {
  const json = safeJsonLd((await fetchSeoValues(path)).json_ld);
  if (!json) return null;
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: json }} />;
}
