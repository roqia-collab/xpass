import { Badge, PageHead } from "@/components/ui";
import type { AccessRow, OrganizationRow } from "@/lib/admin-types";
import { apiFetch, getMe, mediaUrl } from "@/lib/session";

import { AccessPanel } from "../access-panel";
import { CreateRhForm } from "../create-rh";

export const metadata = { title: "Entreprises" };

/** Entreprises clientes et personnes qui gèrent leur avantage salarié (espace RH). */
export default async function OrganizationsPage() {
  const [orgs, me] = await Promise.all([apiFetch<OrganizationRow[]>("/admin/organizations"), getMe()]);
  const isAdmin = Boolean(me?.memberships.some((x) => x.role === "platform_admin"));
  const access = await Promise.all(
    orgs.map((o) => apiFetch<AccessRow[]>(`/admin/access?scope_type=organization&scope_id=${o.id}`)),
  );
  return (
    <>
      <PageHead
        eyebrow="Admin"
        title="Services RH"
        subtitle="Vous créez le service RH. Ce service crée ses commerçants. Leurs prestations publiées s’affichent dans l’application client."
        image={mediaUrl("demo/heroes/culture.jpg") ?? undefined}
        action={isAdmin ? <CreateRhForm /> : undefined}
      />
      {orgs.length === 0 && <p className="muted">Aucune entreprise enregistrée.</p>}
      {orgs.map((o, i) => (
        <section key={o.id} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "baseline", flexWrap: "wrap" }}>
            <h2>{o.name}</h2>
            <span className="muted">{o.city_label ?? ""}</span>
            {o.is_demo && <Badge tone="grey">Démo</Badge>}
          </div>
          {(o.merchants ?? []).length > 0 && (
            <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <h3>Commerçants de ce service</h3>
              {o.merchants.map((m) => (
                <div key={m.id} className="list-row" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                  <div style={{ flex: 1 }}>
                    <strong>{m.display_name}</strong>
                    <div className="muted" style={{ fontSize: 13 }}>
                      {m.venues.map((v) => v.name).join(", ") || "Aucun établissement"}
                      {m.owner_email ? ` · ${m.owner_email}` : ""}
                    </div>
                  </div>
                  <Badge tone={m.venues.some((v) => v.status === "published") ? "mint" : "grey"}>
                    {m.venues.some((v) => v.status === "published") ? "Dans l’application" : "Pas encore visible"}
                  </Badge>
                </div>
              ))}
            </div>
          )}
          <AccessPanel scopeType="organization" scopeId={o.id} rows={access[i]!} canEdit={isAdmin} />
        </section>
      ))}
    </>
  );
}
