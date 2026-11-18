import type { MetadataRoute } from "next";
import { headers } from "next/headers";

import { SITE_URL } from "@/lib/seo";

/** Hôtes publics dont les pages peuvent apparaître dans les moteurs de recherche. */
const PUBLIC_HOSTS = new Set(["xpass.fr", "www.xpass.fr"]);

/** Espaces privés : jamais explorés, même sur xpass.fr. */
const PRIVATE = ["/admin", "/company", "/partner", "/tableau", "/inscription-partenaire", "/auth", "/login", "/api"];

/**
 * robots.txt selon le domaine : xpass.fr ouvre ses pages publiques et donne son plan du site,
 * admin.xpass.fr et rh.xpass.fr ferment tout.
 */
export default async function robots(): Promise<MetadataRoute.Robots> {
  const h = await headers();
  const host = (h.get("x-forwarded-host") ?? h.get("host") ?? "").split(",")[0].trim().toLowerCase().replace(/:\d+$/, "");
  if (!PUBLIC_HOSTS.has(host)) {
    return { rules: [{ userAgent: "*", disallow: "/" }] };
  }
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: PRIVATE }],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
