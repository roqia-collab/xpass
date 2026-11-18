import Link from "next/link";

import { Badge, ErrorCard, Notice, PageHead } from "@/components/ui";
import { REPORT_STATUS_LABEL, reportQuery, type SeoReportRow, type SeoReportStatus } from "@/lib/seo";
import { tryApi } from "@/lib/session";

export const metadata = { title: "SEO" };

const fmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/Paris" });

/** Rapports SEO quotidiens reçus de l’outil externe. Rien n’est appliqué sans validation humaine. */
export default async function SeoReportsPage({ searchParams }: { searchParams: Promise<{ statut?: string; du?: string; au?: string }> }) {
  const params = await searchParams;
  const loaded = await tryApi<SeoReportRow[]>(`/admin/seo/reports${reportQuery(params)}`);
  return (
    <>
      <PageHead
        eyebrow="Admin"
        title="SEO"
        subtitle="Rapports quotidiens sur xpass.fr. Chaque recommandation est validée ou rejetée par un administrateur avant d’être appliquée."
        action={<Link className="btn outline" href="/admin/seo/historique">Historique des modifications</Link>}
      />
      <form className="card seo-filters" method="get">
        <label className="field">
          <span>Statut</span>
          <select name="statut" defaultValue={params.statut ?? ""}>
            <option value="">Tous</option>
            {Object.entries(REPORT_STATUS_LABEL).map(([k, v]) => (
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Du</span>
          <input type="date" name="du" defaultValue={params.du ?? ""} />
        </label>
        <label className="field">
          <span>Au</span>
          <input type="date" name="au" defaultValue={params.au ?? ""} />
        </label>
        <div className="seo-filter-actions">
          <button className="btn primary" type="submit">Filtrer</button>
          <Link className="btn ghost" href="/admin/seo">Effacer</Link>
        </div>
      </form>
      {!loaded.data ? (
        <ErrorCard message={loaded.error ?? "Les rapports n’ont pas pu être chargés."} />
      ) : loaded.data.length === 0 ? (
        <Notice>Aucun rapport pour ces critères. Les rapports arrivent automatiquement chaque jour.</Notice>
      ) : (
        <div className="card" style={{ overflowX: "auto" }}>
          <table className="table">
            <thead>
              <tr><th>Date du rapport</th><th>Statut</th><th>Score</th><th>Recommandations</th><th>Résumé</th><th /></tr>
            </thead>
            <tbody>
              {loaded.data.map((r) => {
                const status = REPORT_STATUS_LABEL[r.status as SeoReportStatus] ?? REPORT_STATUS_LABEL.new;
                return (
                  <tr key={r.id}>
                    <td><Link href={`/admin/seo/${r.id}`}><strong>{fmt.format(new Date(r.report_created_at))}</strong></Link></td>
                    <td><Badge tone={status.tone}>{status.label}</Badge></td>
                    <td>{r.overall_score === null ? "—" : `${r.overall_score} / 100`}</td>
                    <td>{r.recommendation_count}</td>
                    <td className="muted" style={{ maxWidth: 360 }}>{r.summary.slice(0, 160) || "—"}</td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      <Link className="btn ghost" href={`/admin/seo/${r.id}`}>Ouvrir</Link>
                      <a className="btn ghost" href={`/admin/seo/${r.id}/markdown`} download>Markdown</a>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
