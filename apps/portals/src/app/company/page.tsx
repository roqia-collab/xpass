import { ArrowRight, Coins, TrendingUp, UserPlus, Users } from "lucide-react";
import Link from "next/link";

import { Badge, ErrorCard, Kpi, Notice, PageHead } from "@/components/ui";
import { money } from "@/lib/money";
import { VenuePhotos } from "@/components/venue-photos";
import { tryApi } from "@/lib/session";
import { NETWORK_LINE } from "@/lib/roles";
import type { CompanyInvoice, CompanyOverview, CompanyPolicy } from "@/lib/types";

import { PolicyEditor } from "./forms";

export const metadata = { title: "Budgets" };

const monthLabel = (iso: string) =>
  new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${iso}T12:00:00Z`));
const COLORS = ["var(--coral)", "var(--lavender-strong)", "var(--navy)", "#e8b6f0", "#9ad0b5", "#f5c26b"];

/** Maquette 23 — budgets : indicateurs, politique (versionnée), utilisation agrégée par catégorie. */
export default async function CompanyBudgets() {
  const [overview, invoiceLoad] = await Promise.all([
    tryApi<CompanyOverview>("/company/overview"),
    tryApi<CompanyInvoice[]>("/company/invoices"),
  ]);
  if (!overview.data) {
    return (
      <>
        <PageHead eyebrow="RH" title="Espace RH" subtitle="Votre service est ouvert." />
        <ErrorCard message={overview.error ?? "Les budgets n’ont pas pu être chargés."} />
        <Link href="/company/commercants" className="btn primary">Vos commerçants</Link>
      </>
    );
  }
  const o = overview.data;
  const invoices = invoiceLoad.data ?? [];
  if (!o.report || !o.categories) {
    return (
      <>
        <PageHead eyebrow="RH" title="Espace ouvert" subtitle={o.organization_name || "Votre service RH"} />
        <Notice>Les budgets apparaîtront avec les salariés. Vous pouvez déjà ajouter vos commerçants.</Notice>
        <Link href="/company/commercants" className="btn primary">Vos commerçants</Link>
      </>
    );
  }
  const r = o.report;
  const c = o.contract?.currency ?? r.currency ?? "EUR";
  const names = Object.fromEntries(o.categories.map((x) => [x.slug, x.name]));
  const visible = r.categories.filter((x) => !x.masked && x.share !== null);
  let acc = 0;
  const donut = visible.map((x, i) => `${COLORS[i % COLORS.length]} ${acc}% ${(acc += x.share!)}%`).join(", ");

  return (
    <>
      <PageHead
        eyebrow="Budgets"
        title="Les avantages de votre équipe"
        image={`${process.env.NEXT_PUBLIC_MEDIA_BASE_URL ?? "http://localhost:3080/xpass-public"}/demo/heroes/sport.jpg`}
        subtitle={`${o.organization_name} · proposez à vos salariés des avantages bien-être, culture et loisirs.`}
        action={o.contract?.is_demo ? <Badge tone="lavender">Démo</Badge> : undefined}
      />
      {!o.contract && <Notice>Aucun contrat XPASS n’est actif pour votre organisation : contactez l’équipe XPASS.</Notice>}
      {o.contract && o.contract.status !== "active" && (
        <Notice>Contrat {o.contract.status === "suspended" ? "suspendu" : o.contract.status} : aucune allocation n’est effectuée.</Notice>
      )}
      <div className="card" style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <div>
          <h3>Le réseau</h3>
          <p className="muted">{NETWORK_LINE}</p>
        </div>
        <Link href="/company/commercants" className="btn outline">Gérer les commerçants <ArrowRight size={16} /></Link>
      </div>
      <div className="grid grid-3">
        <Kpi href="/company/salaries" icon={<Users />} label="Salariés éligibles" value={r.eligible} detail={`${r.active} ont activé leur avantage`} />
        <Kpi href="/company/salaries" icon={<TrendingUp />} label="Taux d’activation" value={`${r.activation_rate} %`} detail="Invitations acceptées" />
        <Kpi
          href="/company/factures"
          icon={<Coins />}
          label="Budget mensuel"
          value={money(r.monthly_budget_minor, c)}
          detail={`${invoices.filter((i) => i.status === "pending").length} facture(s) à payer · ${money(r.balance_minor, c)} disponibles`}
          tone="coral"
        />
      </div>
      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <section className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>Paiements</h3>
            <Link href="/company/factures">Tout voir <ArrowRight size={14} /></Link>
          </div>
          {invoices.slice(0, 5).map((i) => (
            <div key={i.id} className="list-row" style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <div style={{ flex: 1 }}>
                <strong>{i.reference}</strong>
                <div className="muted" style={{ fontSize: 13 }}>{i.label}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div>{money(i.amount_minor, i.currency)}</div>
                <Badge tone={i.status === "paid" ? "mint" : i.status === "pending" ? "lavender" : "grey"}>
                  {i.status === "paid" ? "Payée" : i.status === "pending" ? "À payer" : "Annulée"}
                </Badge>
              </div>
            </div>
          ))}
          {invoices.length === 0 && <p className="muted">Aucune facture pour le moment.</p>}
        </section>
        <section className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>Contrat</h3>
            <Link href="/company/parametres">Paramètres <ArrowRight size={14} /></Link>
          </div>
          {!o.contract && <p className="muted">Aucun contrat actif.</p>}
          {o.contract && (
            <>
              <p>Statut : {o.contract.status === "active" ? "actif" : o.contract.status}</p>
              <p>Prix du crédit : {money(o.contract.credit_price_minor, o.contract.currency)}</p>
              <p>Durée : {o.contract.term_months} mois · villes : {o.contract.covered_cities.join(", ")}</p>
              <p>Commission commerçant : {o.contract.commission_bps / 100} % · annulation gratuite : {o.contract.free_cancellation_hours} h</p>
              <p className="muted">Début le {o.contract.starts_on}. Les crédits arrivent dans l’application seulement après confirmation du paiement.</p>
            </>
          )}
        </section>
      </div>
      {o.contract && r.balance_minor < r.monthly_budget_minor && (
        <Notice>
          Le financement disponible ne couvre pas tout le budget du mois : certains salariés recevront leurs crédits après le
          prochain virement. <Link href="/company/factures">Demander un financement</Link>
        </Notice>
      )}
      <VenuePhotos title="Ce que vos salariés peuvent réserver" text="Sport, culture, beauté et sorties, avec les photos des établissements." />
      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <h2>Votre politique de budget</h2>
          <PolicyBlock policy={o.policy} names={names} currency={c} price={o.contract?.credit_price_minor ?? 0} active={r.active} />
          {o.next_policy && (
            <div className="notice">
              À partir du {monthLabel(o.next_policy.effective_from)} : {o.next_policy.credits_per_month} crédits par salarié
              {o.next_policy.eligible_categories
                ? ` · ${o.next_policy.eligible_categories.map((s) => names[s] ?? s).join(", ")}`
                : " · tous les univers"}
              .
            </div>
          )}
          <PolicyEditor overview={o} />
        </div>
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <h2>Utilisation du budget par catégorie</h2>
          <p className="muted">
            Crédits employeur utilisés ce mois-ci : {r.consumed_credits} ({money(r.consumed_cost_minor, c)}).
            {r.penalty_credits > 0 && <> Dont {r.penalty_credits} liés à des annulations tardives ou des absences (total, sans détail par salarié).</>}
          </p>
          <p className="muted" style={{ fontSize: 13 }}>
            Règles pour vos salariés : le prix d’un créneau varie (+20 % aux heures de pointe, −20 % en dernière minute) ;
            une annulation tardive rend la moitié des crédits, une absence les consomme. Les crédits employeur ne sont
            jamais reportés d’un abonnement personnel : ils suivent la durée de validité de votre politique.
          </p>
          {r.categories.length === 0 ? (
            <p className="muted">Aucune utilisation pour le moment.</p>
          ) : (
            <div style={{ display: "flex", gap: 24, alignItems: "center", flexWrap: "wrap" }}>
              {visible.length > 0 && (
                <div aria-hidden style={{ width: 160, height: 160, borderRadius: "50%", background: `conic-gradient(${donut})`, flexShrink: 0 }} />
              )}
              <div style={{ flex: 1, minWidth: 200 }}>
                {r.categories.map((x) => {
                  const idx = visible.indexOf(x);
                  return (
                    <div key={x.slug} className="list-row" style={{ display: "flex", gap: 10, alignItems: "center" }}>
                      <span aria-hidden style={{ width: 10, height: 10, borderRadius: 5, background: idx < 0 ? "var(--line)" : COLORS[idx % COLORS.length] }} />
                      <span style={{ flex: 1 }}>{x.name}</span>
                      {x.masked ? (
                        <span className="muted">Détail masqué</span>
                      ) : (
                        <span>
                          <strong>{x.share} %</strong> · {x.employees} salariés
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          <Notice>Données agrégées · aucun détail de visite individuel. Détail masqué sous {r.privacy_threshold} salariés.</Notice>
        </div>
      </div>
      {o.can_edit && (
        <Link className="btn primary" href="/company/salaries">
          <UserPlus size={20} /> Inviter des salariés
        </Link>
      )}
    </>
  );
}

function PolicyBlock({
  policy,
  names,
  currency,
  price,
  active,
}: {
  policy: CompanyPolicy | null;
  names: Record<string, string>;
  currency: string;
  price: number;
  active: number;
}) {
  if (!policy) return <p className="muted">Aucune politique définie : aucun crédit n’est attribué.</p>;
  return (
    <div className="grid grid-2">
      <div>
        <span className="muted">Crédits alloués par mois</span>
        <p className="serif" style={{ fontSize: 28 }}>{policy.credits_per_month} crédits</p>
        <span className="muted">par salarié · {money(policy.credits_per_month * price, currency)}</span>
      </div>
      <div>
        <span className="muted">Budget monétaire (entreprise)</span>
        <p className="serif" style={{ fontSize: 28 }}>{money(policy.credits_per_month * price * active, currency)}</p>
        <span className="muted">par mois ({active} salariés actifs)</span>
      </div>
      <div>
        <span className="muted">Univers éligibles</span>
        <p>{policy.eligible_categories ? policy.eligible_categories.map((s) => names[s] ?? s).join(", ") : "Tous les univers"}</p>
      </div>
      <div>
        <span className="muted">Depuis le</span>
        <p>
          {monthLabel(policy.effective_from)} · validité {policy.credit_validity_days} jours
        </p>
      </div>
    </div>
  );
}
