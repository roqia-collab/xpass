import Link from "next/link";

import { Badge, PageHead } from "@/components/ui";
import type { ChangeRequestRow, ModerationRow } from "@/lib/admin-types";
import { COMMERCIAL_LABEL } from "@/lib/roles";
import { apiFetch } from "@/lib/session";

import { ChangeRequests } from "../change-requests";

export const metadata = { title: "Modération" };

const STATUS: Record<string, { label: string; tone: "mint" | "grey" | "coral" }> = {
  published: { label: "Publié", tone: "mint" },
  hidden: { label: "Masqué", tone: "coral" },
  draft: { label: "Brouillon", tone: "grey" },
};

/** Établissements : publication et masquage motivés (depuis la fiche du partenaire). */
export default async function ModerationPage({ searchParams }: { searchParams: Promise<{ statut?: string }> }) {
  const { statut } = await searchParams;
  const qs = statut && statut in STATUS ? `?status=${statut}` : "";
  const [rows, changes] = await Promise.all([
    apiFetch<ModerationRow[]>(`/admin/locations${qs}`),
    apiFetch<ChangeRequestRow[]>("/admin/change-requests"),
  ]);
  return (
    <>
      <PageHead title="Modération" subtitle="Établissements visibles dans le catalogue. Masquer ou publier se fait depuis la fiche partenaire, avec un motif." />
      <h2>Demandes de modification</h2>
      <ChangeRequests rows={changes} />
      <h2>Établissements</h2>
      <div style={{ display: "flex", gap: 8 }}>
        {["", "published", "hidden", "draft"].map((s) => (
          <Link key={s} className={`btn ${statut === s || (!statut && !s) ? "outline" : "ghost"}`} href={s ? `?statut=${s}` : "?"}>
            {s ? STATUS[s].label : "Tous"}
          </Link>
        ))}
      </div>
      <div className="card" style={{ overflowX: "auto" }}>
        <table className="table">
          <thead><tr><th>Établissement</th><th>Partenaire</th><th>Dossier</th><th>Prestations publiées</th><th>Statut</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td><strong>{r.name}</strong></td>
                <td>{r.merchant_name}</td>
                <td><Badge tone={COMMERCIAL_LABEL[r.commercial_status].tone}>{COMMERCIAL_LABEL[r.commercial_status].label}</Badge></td>
                <td>{r.published_offers}</td>
                <td><Badge tone={STATUS[r.status]?.tone ?? "grey"}>{STATUS[r.status]?.label ?? r.status}</Badge></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
