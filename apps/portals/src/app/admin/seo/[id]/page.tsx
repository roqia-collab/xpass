import Link from "next/link";
import { notFound } from "next/navigation";

import { Badge, ErrorCard, PageHead } from "@/components/ui";
import { defaultSeoValue, markdownFileName, REPORT_STATUS_LABEL, type SeoReportDetail, type SeoReportStatus } from "@/lib/seo";
import { tryApi } from "@/lib/session";

import { SafeMarkdown } from "../markdown";
import { RecommendationCard } from "../recommendation";

export const metadata = { title: "Rapport SEO" };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const fmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "full", timeStyle: "short", timeZone: "Europe/Paris" });

export default async function SeoReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!UUID.test(id)) notFound();
  const loaded = await tryApi<SeoReportDetail>(`/admin/seo/reports/${id}`);
  if (!loaded.data) {
    return (
      <>
        <PageHead eyebrow="SEO" title="Rapport SEO" />
        <ErrorCard message={loaded.error ?? "Le rapport n’a pas pu être chargé."} />
      </>
    );
  }
  const r = loaded.data;
  const status = REPORT_STATUS_LABEL[r.status as SeoReportStatus] ?? REPORT_STATUS_LABEL.new;
  const pending = r.recommendations.filter((x) => x.status === "new" || x.status === "validated");
  const done = r.recommendations.filter((x) => x.status !== "new" && x.status !== "validated");
  return (
    <>
      <PageHead
        eyebrow="SEO"
        title={`Rapport du ${fmt.format(new Date(r.report_created_at))}`}
        subtitle={<>{r.site_url} · identifiant {r.report_id} · reçu de {r.source}</>}
        action={
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Link className="btn ghost" href="/admin/seo">Tous les rapports</Link>
            <a className="btn outline" href={`/admin/seo/${r.id}/markdown`} download={markdownFileName(r.report_created_at)}>
              Télécharger le Markdown
            </a>
          </div>
        }
      />
      <div className="card" style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "center" }}>
        <Badge tone={status.tone}>{status.label}</Badge>
        <span><strong>{r.overall_score === null ? "—" : `${r.overall_score} / 100`}</strong> <span className="muted">score global</span></span>
        <span><strong>{r.recommendation_count}</strong> <span className="muted">recommandations</span></span>
        <span><strong>{pending.length}</strong> <span className="muted">à traiter</span></span>
      </div>
      {r.summary && (
        <section className="card">
          <h2>Résumé</h2>
          <p style={{ whiteSpace: "pre-line", marginTop: 8 }}>{r.summary}</p>
        </section>
      )}
      <section className="request-list">
        <h2>Recommandations à traiter</h2>
        {pending.length === 0 && <p className="muted">Toutes les recommandations ont été traitées.</p>}
        {pending.map((reco) => (
          <RecommendationCard key={reco.id} reco={reco} defaultValue={reco.page_path && reco.field ? defaultSeoValue(reco.page_path, reco.field) : null} />
        ))}
      </section>
      {done.length > 0 && (
        <section className="request-list">
          <h2>Recommandations traitées</h2>
          {done.map((reco) => (
            <RecommendationCard key={reco.id} reco={reco} defaultValue={reco.page_path && reco.field ? defaultSeoValue(reco.page_path, reco.field) : null} />
          ))}
        </section>
      )}
      <details className="card">
        <summary><strong>Rapport complet (Markdown)</strong></summary>
        <SafeMarkdown source={r.markdown_report} />
      </details>
    </>
  );
}
