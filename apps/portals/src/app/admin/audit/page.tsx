import Link from "next/link";

import { PageHead } from "@/components/ui";
import { ACTOR_LABEL, type AuditEntry } from "@/lib/admin-types";
import { apiFetch } from "@/lib/session";

export const metadata = { title: "Audit" };

const TYPES: Record<string, string> = {
  merchant: "Partenaires",
  location: "Établissements",
  dispute: "Litiges",
  partner_payout: "Versements",
  payment_event: "Webhooks",
  employer_invoice: "Factures entreprises",
};

/** Journal d'audit en ajout seul (ni modification ni suppression possibles en base). */
export default async function AuditPage({ searchParams }: { searchParams: Promise<{ type?: string }> }) {
  const { type } = await searchParams;
  const qs = type && type in TYPES ? `&object_type=${type}` : "";
  const rows = await apiFetch<AuditEntry[]>(`/admin/audit?limit=200${qs}`);
  const fmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "medium" });
  return (
    <>
      <PageHead title="Journal d’audit" subtitle="Décisions et événements sensibles. Les entrées ne peuvent être ni modifiées ni supprimées." />
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Link className={`btn ${!type ? "outline" : "ghost"}`} href="?">Tout</Link>
        {Object.entries(TYPES).map(([k, l]) => (
          <Link key={k} className={`btn ${type === k ? "outline" : "ghost"}`} href={`?type=${k}`}>{l}</Link>
        ))}
      </div>
      <div className="card" style={{ overflowX: "auto" }}>
        <table className="table">
          <thead><tr><th>Date et heure</th><th>Acteur</th><th>Action</th><th>Objet</th><th>Motif</th><th>Détail</th></tr></thead>
          <tbody>
            {rows.map((a, i) => (
              <tr key={i}>
                <td>{fmt.format(new Date(a.created_at))}</td>
                <td>{a.actor_name ? `${a.actor_name} (${ACTOR_LABEL[a.actor_kind]})` : ACTOR_LABEL[a.actor_kind]}</td>
                <td>{a.action}</td>
                <td>{a.object_label}</td>
                <td>{a.reason ?? "—"}</td>
                <td className="muted" style={{ fontSize: 12 }}>{Object.keys(a.details).length ? JSON.stringify(a.details) : ""}</td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={6} className="muted">Aucune entrée.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
