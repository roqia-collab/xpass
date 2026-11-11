import { Badge, PageHead } from "@/components/ui";
import { money } from "@/lib/money";
import { apiFetch } from "@/lib/session";
import type { CompanyOverview } from "@/lib/types";

export const metadata = { title: "Paramètres" };

const CONTRACT: Record<string, string> = {
  active: "Actif",
  suspended: "Suspendu",
  ended: "Terminé",
};

/** Informations réelles de l’organisation : même contrat et même nom que les budgets. */
export default async function CompanySettingsPage() {
  const o = await apiFetch<CompanyOverview>("/company/overview");
  const c = o.contract;
  return (
    <>
      <PageHead
        eyebrow="RH"
        title="Paramètres"
        subtitle="Les informations de votre organisation, telles qu’elles sont enregistrées chez XPASS."
        image={`${process.env.NEXT_PUBLIC_MEDIA_BASE_URL ?? "http://localhost:3080/xpass-public"}/demo/locations/le-cercle.jpg`}
      />
      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <section className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2>Organisation</h2>
          <p style={{ fontSize: 18 }}>{o.organization_name}</p>
          <p className="muted">
            {o.can_edit ? "Vous pouvez inviter des salariés et ajuster la politique de budget." : "Accès en lecture."}
          </p>
        </section>
        <section className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h2>Contrat XPASS</h2>
          {!c && <p className="muted">Aucun contrat n’est actif. Contactez l’équipe XPASS.</p>}
          {c && (
            <>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Badge tone={c.status === "active" ? "mint" : "coral"}>{CONTRACT[c.status] ?? c.status}</Badge>
                {c.is_demo && <Badge tone="grey">Démo</Badge>}
              </div>
              <p>Prix du crédit : {money(c.credit_price_minor, c.currency)}</p>
              <p>Durée : {c.term_months} mois · {c.covered_cities.join(", ")}</p>
              <p>Commission commerçant : {c.commission_bps / 100} % · annulation gratuite {c.free_cancellation_hours} h avant la séance.</p>
              <p className="muted">Début : {c.starts_on} · devise {c.currency}. Les crédits des salariés sont crédités après paiement confirmé de la facture.</p>
            </>
          )}
        </section>
      </div>
    </>
  );
}
