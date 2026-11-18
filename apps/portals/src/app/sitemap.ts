import type { MetadataRoute } from "next";

import { SEO_PAGES, SITE_URL } from "@/lib/seo";

/** Plan du site : les pages publiques de xpass.fr (la même liste que la gestion SEO de l’admin). */
export default function sitemap(): MetadataRoute.Sitemap {
  return Object.keys(SEO_PAGES).map((path) => ({
    url: `${SITE_URL}${path === "/" ? "" : path}`,
    changeFrequency: path === "/" ? "weekly" : path.startsWith("/legal/") ? "yearly" : "monthly",
    priority: path === "/" ? 1 : path.startsWith("/legal/") ? 0.3 : 0.7,
  }));
}
