import { Badge, PageHead } from "@/components/ui";
import { initials } from "@/lib/roles";
import { apiFetch } from "@/lib/session";
import type { CompanyEmployee, CompanyOverview } from "@/lib/types";

import { CsvImport, EmployeeMenu, InviteForm } from "../forms";
import { ApiKeys, type ApiKeyRow } from "../online-forms";

export const metadata = { title: "Salariés" };

const STATUS: Record<CompanyEmployee["status"], { label: string; tone: "mint" | "lavender" | "coral" | "grey" }> = {
  invited: { label: "En attente", tone: "lavender" },
  active: { label: "Active", tone: "mint" },
  suspended: { label: "Suspendue", tone: "coral" },
  removed: { label: "Retiré(e)", tone: "grey" },
};

/** Maquette 24 — invitations (individuelles, CSV avec aperçu des erreurs) et gestion des salariés. */
export default async function SalariesPage({ searchParams }: { searchParams: Promise<{ statut?: string; q?: string }> }) {
  const { statut, q } = await searchParams;
  const params = new URLSearchParams();
  if (statut && statut in STATUS) params.set("status", statut);
  if (q) params.set("q", q.slice(0, 80));
  const [employees, overview] = await Promise.all([
    apiFetch<CompanyEmployee[]>(`/company/employees?${params}`),
    apiFetch<CompanyOverview>("/company/overview"),
  ]);
  const hasPolicy = Boolean(overview.policy);

  return (
    <>
      <PageHead
        title="Inviter et gérer les salariés"
        image={`${process.env.NEXT_PUBLIC_MEDIA_BASE_URL ?? "http://localhost:3080/xpass-public"}/demo/locations/le-cercle.jpg`}
        subtitle="Ajoutez vos salariés pour leur donner accès à l’avantage XPASS. Ils l’activent dans l’application avec l’adresse e-mail invitée."
      />
      {overview.can_edit && (
        <div className="grid grid-2" style={{ alignItems: "start" }}>
          <CsvImport />
          <InviteForm />
        </div>
      )}
      {overview.can_edit && (
        <ApiKeys rows={await apiFetch<ApiKeyRow[]>("/company/api-keys")} apiBase={process.env.API_PUBLIC_URL ?? "http://localhost:8000"} />
      )}
      <div className="card" style={{ overflowX: "auto" }}>
        <form style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}>
          <h2 style={{ flex: 1 }}>Salariés ({employees.length})</h2>
          <input name="q" defaultValue={q} placeholder="Rechercher un salarié…" aria-label="Rechercher un salarié" className="pill" style={{ padding: 10 }} />
          <select name="statut" defaultValue={statut ?? ""} aria-label="Statut" className="pill" style={{ padding: 10 }}>
            <option value="">Tous les statuts</option>
            {Object.entries(STATUS).map(([k, v]) => (
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>
          <button className="btn outline">Filtrer</button>
        </form>
        <table className="table">
          <thead>
            <tr>
              <th>Nom</th>
              <th>E-mail</th>
              <th>Statut</th>
              <th>Crédits ce mois</th>
              <th>Ajouté le</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {employees.map((e) => {
              const name = `${e.first_name} ${e.last_name}`.trim();
              return (
                <tr key={e.id}>
                  <td>
                    <span style={{ display: "inline-flex", gap: 10, alignItems: "center" }}>
                      <span className="avatar" style={{ width: 34, height: 34, fontSize: 13 }}>{initials(name || e.email)}</span>
                      {name || "—"}
                    </span>
                  </td>
                  <td>{e.email}</td>
                  <td><Badge tone={STATUS[e.status].tone}>{STATUS[e.status].label}</Badge></td>
                  <td>
                    {e.credits_this_month !== null
                      ? `${e.credits_this_month} crédits`
                      : e.status === "active" && hasPolicy
                        ? "En attente de financement"
                        : "—"}
                  </td>
                  <td>{new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(new Date(e.invited_at))}</td>
                  <td>{overview.can_edit && <EmployeeMenu employee={e} />}</td>
                </tr>
              );
            })}
            {employees.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">Aucun salarié pour ces critères.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="muted" style={{ fontSize: 13 }}>
        Aucun e-mail n’est encore envoyé (fournisseur d’e-mail à configurer) : prévenez vos salariés qu’ils peuvent accepter
        l’invitation dans l’application XPASS, rubrique Profil.
      </p>
    </>
  );
}
