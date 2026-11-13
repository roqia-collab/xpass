import Link from "next/link";

import { Badge, PageHead } from "@/components/ui";
import { DISPUTE_LABEL, type DisputeRow } from "@/lib/admin-types";
import { apiFetch } from "@/lib/session";

export const metadata = { title: "Litiges" };

/** Réclamations clients sur une prestation utilisée ou une annulation tardive. */
export default async function DisputesPage({ searchParams }: { searchParams: Promise<{ vue?: string }> }) {
  const { vue } = await searchParams;
  const scope = vue === "clos" ? "closed" : vue === "tous" ? "all" : "open";
  const rows = await apiFetch<DisputeRow[]>(`/admin/disputes?scope=${scope}`);
  const fmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" });
  return (
    <>
      <PageHead title="Litiges" subtitle="Réclamations des clients : analyse, restitution de crédits, ajustement partenaire." />
      <div style={{ display: "flex", gap: 8 }}>
        {[["", "Ouverts"], ["clos", "Clos"], ["tous", "Tous"]].map(([v, l]) => (
          <Link key={v} className={`btn ${(vue ?? "") === v ? "outline" : "ghost"}`} href={v ? `?vue=${v}` : "?"}>{l}</Link>
        ))}
      </div>
      <div className="card" style={{ overflowX: "auto" }}>
        <table className="table">
          <thead><tr><th>Dossier</th><th>Établissement</th><th>Client</th><th>Motif</th><th>Ouvert le</th><th>Statut</th><th /></tr></thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.id}>
                <td><Link href={`/admin/litiges/${d.id}`}><strong>{d.reference}</strong></Link></td>
                <td>{d.location_name}</td>
                <td>{d.customer_name}</td>
                <td className="muted">{d.reason}</td>
                <td>{fmt.format(new Date(d.created_at))}</td>
                <td><Badge tone={DISPUTE_LABEL[d.status].tone}>{DISPUTE_LABEL[d.status].label}</Badge></td>
                <td><Link className="btn outline" href={`/admin/litiges/${d.id}`}>Modifier</Link></td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={7} className="muted">Aucun litige.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
