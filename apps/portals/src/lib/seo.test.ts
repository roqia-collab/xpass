import { describe, expect, it } from "vitest";

import { parseMarkdown, parseInline } from "./markdown";
import { canAccess } from "./roles";
import { buildSeoMetadata, defaultSeoValue, markdownFileName, REPORT_STATUS_LABEL, reportQuery, safeJsonLd } from "./seo";

describe("métadonnées SEO", () => {
  it("garde la page d’origine sans valeur enregistrée", () => {
    const base = { title: "Demander un accès" };
    expect(buildSeoMetadata(base, {})).toEqual(base);
  });

  it("applique les valeurs validées à la page", () => {
    const meta = buildSeoMetadata(
      { title: "Demander un accès" },
      {
        title: "Accès XPASS entreprise",
        description: "Desc",
        canonical: "https://xpass.fr/demande",
        og_title: "OG",
        og_image: "https://xpass.fr/logo.png",
        twitter_title: "TW",
        robots: "index, follow",
      },
    );
    expect(meta.title).toEqual({ absolute: "Accès XPASS entreprise" });
    expect(meta.description).toBe("Desc");
    expect(meta.robots).toBe("index, follow");
    expect(meta.alternates?.canonical).toBe("https://xpass.fr/demande");
    expect(meta.openGraph).toMatchObject({ title: "OG", url: "https://xpass.fr/demande", images: [{ url: "https://xpass.fr/logo.png" }] });
    expect(meta.twitter).toMatchObject({ card: "summary_large_image", title: "TW" });
  });

  it("donne la valeur par défaut affichée avant application", () => {
    expect(defaultSeoValue("/demande", "title")).toBe("Demander un accès · XPASS");
    expect(defaultSeoValue("/", "robots")).toBe("noindex");
    expect(defaultSeoValue("/admin", "title")).toBeNull();
  });

  it("échappe le JSON-LD pour qu’il ne puisse pas fermer la balise script", () => {
    const out = safeJsonLd('{"name":"</script><script>alert(1)</script>"}');
    expect(out).not.toContain("<");
    expect(JSON.parse(out!)).toEqual({ name: "</script><script>alert(1)</script>" });
    expect(safeJsonLd("{oops")).toBeNull();
    expect(safeJsonLd("42")).toBeNull();
  });
});

describe("rapport Markdown", () => {
  it("n’interprète aucun HTML", () => {
    const blocks = parseMarkdown("# Titre\n\n<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>");
    expect(blocks[0]).toMatchObject({ t: "h", level: 1 });
    expect(blocks[1]).toEqual({ t: "p", c: [{ t: "text", v: "<script>alert(1)</script>" }] });
    expect(JSON.stringify(blocks)).not.toContain('"t":"html"');
  });

  it("ne garde que les liens http(s)", () => {
    expect(parseInline("[ok](https://xpass.fr)")).toEqual([{ t: "link", v: "ok", href: "https://xpass.fr" }]);
    expect(parseInline("[ko](javascript:alert(1))")[0].t).toBe("text");
  });

  it("reconnaît listes, tableaux et code", () => {
    const blocks = parseMarkdown("- a\n- **b**\n\n| Page | Score |\n|---|---|\n| / | 72 |\n\n```\n<b>x</b>\n```");
    expect(blocks.map((b) => b.t)).toEqual(["ul", "table", "code"]);
    expect(blocks[2]).toEqual({ t: "code", v: "<b>x</b>" });
  });

  it("nomme le fichier téléchargé selon la date du rapport (heure de Paris)", () => {
    expect(markdownFileName("2026-11-16T23:30:00Z")).toBe("rapport-seo-xpass-2026-11-17.md");
  });
});

describe("liste des rapports", () => {
  it("propose les cinq statuts du cahier des charges", () => {
    expect(Object.values(REPORT_STATUS_LABEL).map((s) => s.label)).toEqual([
      "Nouveau",
      "En cours de validation",
      "Validé",
      "Appliqué",
      "Rejeté",
    ]);
  });

  it("ne transmet que des filtres valides", () => {
    expect(reportQuery({ statut: "applied", du: "2026-11-01", au: "2026-11-17" })).toBe("?status=applied&date_from=2026-11-01&date_to=2026-11-17");
    expect(reportQuery({ statut: "drop table", du: "hier" })).toBe("");
  });

  it("réserve l’espace admin aux rôles d’administration", () => {
    expect(canAccess({ memberships: [{ role: "hr_admin" }] } as never, "admin")).toBe(false);
    expect(canAccess({ memberships: [{ role: "platform_admin" }] } as never, "admin")).toBe(true);
  });
});
