import Link from "next/link";

import { ErrorCard, PageHead } from "@/components/ui";
import { SEO_FIELD_LABEL, SEO_PAGES, type SeoChange } from "@/lib/seo";
import { tryApi } from "@/lib/session";

import { RevertButton } from "../recommendation";

export const metadata = { title: "Historique SEO" };

const fmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short", timeZone: "Europe/Paris" });

/** Toutes les balises appliquées, avec l’ancienne valeur, l’auteur, la date et l’éventuelle annulation. */
export default async function SeoHistoryPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const { page } = await searchParams;
  const path = page && page in SEO_PAGES ? page : undefined;
  const loaded = await tryApi<SeoChange[]>(`/admin/seo/history${path ? `?path=${encodeURIComponent(path)}` : ""}`);
  return (
    <>
      <PageHead
        eyebrow="SEO"
        title="Historique des modifications"
        subtitle="Seule la modification la plus récente d’une balise peut être annulée : l’ancienne valeur est alors restaurée."
        action={<Link className="btn ghost" href="/admin/seo">Rapports</Link>}
      />
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Link className={`btn ${!path ? "outline" : "ghost"}`} href="?">Toutes les pages</Link>
        {Object.keys(SEO_PAGES).map((p) => (
          <Link key={p} className={`btn ${path === p ? "outline" : "ghost"}`} href={`?page=${encodeURIComponent(p)}`}>{p}</Link>
        ))}
      </div>
      {!loaded.data ? (
        <ErrorCard message={loaded.error ?? "L’historique n’a pas pu être chargé."} />
      ) : (
        <div className="card" style={{ overflowX: "auto" }}>
          <table className="table">
            <thead>
              <tr><th>Appliquée le</th><th>Page</th><th>Balise</th><th>Ancienne valeur</th><th>Nouvelle valeur</th><th>Par</th><th>État</th></tr>
            </thead>
            <tbody>
              {loaded.data.map((c) => (
                <tr key={c.id}>
                  <td>{fmt.format(new Date(c.applied_at))}</td>
                  <td>{c.page_path}</td>
                  <td>{SEO_FIELD_LABEL[c.field] ?? c.field}</td>
                  <td><code className="seo-cell">{c.old_value ?? "(valeur par défaut du code)"}</code></td>
                  <td><code className="seo-cell">{c.new_value}</code></td>
                  <td>{c.applied_by_name ?? "—"}</td>
                  <td>
                    {c.reverted_at ? (
                      <span className="muted">Annulée le {fmt.format(new Date(c.reverted_at))} par {c.reverted_by_name ?? "—"}</span>
                    ) : c.revertible ? (
                      <RevertButton changeId={c.id} />
                    ) : (
                      <span className="muted">Remplacée par une modification plus récente</span>
                    )}
                    {c.report_id && <> · <Link href={`/admin/seo/${c.report_id}`}>rapport</Link></>}
                  </td>
                </tr>
              ))}
              {loaded.data.length === 0 && <tr><td colSpan={7} className="muted">Aucune modification appliquée.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
