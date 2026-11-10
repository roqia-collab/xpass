import { ArrowLeftRight, BarChart3, CreditCard, Download, Landmark, Percent, Users, X } from "lucide-react";
import Link from "next/link";

import { Badge, ErrorCard, Kpi, Notice, PageHead } from "@/components/ui";
import { ApiError, apiFetch } from "@/lib/session";
import type { Payout, PayoutDetail, Settlements } from "@/lib/types";

import { PayoutAccount } from "../payout-account";

export const metadata = { title: "Règlements" };

/** Montants en unités mineures, jamais confondus avec des crédits. */
const money = (minor: number, currency: string) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency }).format(minor / 100);

const period = (p: Payout) => {
  const f = (iso: string, withMonth: boolean) =>
    new Intl.DateTimeFormat("fr-FR", withMonth ? { day: "2-digit", month: "short", year: "numeric" } : { day: "2-digit" }).format(
      new Date(`${iso}T12:00:00Z`),
    );
  return `${f(p.period_start, false)} – ${f(p.period_end, true)}`;
};

const STATUS: Record<Payout["status"], { label: string; tone: "mint" | "lavender" | "coral" | "grey" }> = {
  paid: { label: "Virement confirmé", tone: "mint" },
  in_transit: { label: "Virement en cours", tone: "lavender" },
  pending: { label: "En attente", tone: "lavender" },
  to_reconcile: { label: "À rapprocher", tone: "coral" },
  failed: { label: "Échec du virement", tone: "coral" },
};

/** Maquette 22 — règlements commerçant : périodes hebdomadaires, commission, ajustements, net versé. */
export default async function ReglementsPage({ searchParams }: { searchParams: Promise<{ versement?: string; versements?: string }> }) {
  let data: Settlements;
  try {
    data = await apiFetch<Settlements>("/partner/settlements");
  } catch (e) {
    return <ErrorCard message={e instanceof ApiError ? e.message : "Règlements indisponibles."} />;
  }
  const { versement, versements } = await searchParams;
  const selected =
    versement && /^[0-9a-f-]{36}$/.test(versement)
      ? await apiFetch<PayoutDetail>(`/partner/settlements/${versement}`).catch(() => null)
      : null;
  const c = data.currency;
  const open = data.open_period;

  return (
    <>
      <PageHead
        eyebrow="Règlements commerçant"
        title="Vos règlements"
        image="/visuels/reglements.jpg"
        subtitle="Suivez vos versements, consultez le détail de vos prestations et rapprochez-les en toute simplicité."
      />

      {data.terms?.is_demo && (
        <Notice>
          Barème de démonstration : {money(data.terms.gross_minor_per_credit, c)} par crédit, commission{" "}
          {data.terms.commission_bps / 100} %. À remplacer par vos conditions contractuelles.
        </Notice>
      )}
      {!data.terms && <Notice>Aucun barème n’est défini pour votre marché : vos prestations restent à valoriser.</Notice>}

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))" }}>
        <Kpi icon={<CreditCard />} label="À recevoir" value={money(data.to_receive_minor, c)} detail="Versements en attente ou en cours" />
        <Kpi icon={<Percent />} label="Commission" value={money(open.commission_minor, c)} detail="Période en cours" />
        <Kpi icon={<ArrowLeftRight />} label="Ajustements" value={money(open.adjustments_minor, c)} detail="Avoirs et corrections" />
        <Kpi icon={<BarChart3 />} label="Net" value={money(open.net_minor, c)} detail="Période en cours, avant versement" tone="coral" />
        <Kpi icon={<Users />} label="Visites" value={open.visits} detail="Période en cours" />
      </div>
      {open.pending_valuation > 0 && (
        <Notice>{open.pending_valuation} prestation(s) en attente de valorisation (barème manquant à leur date).</Notice>
      )}

      <div style={{ display: "grid", gridTemplateColumns: selected ? "minmax(0,1fr) 340px" : "1fr", gap: 20 }}>
        <div className="card" style={{ overflowX: "auto" }}>
          <h3 style={{ marginBottom: 12 }}>Historique des règlements</h3>
          {data.payouts.length === 0 ? (
            <p className="muted">
              Aucun versement pour l’instant. Les prestations sont regroupées chaque semaine (lundi → dimanche) et versées après
              la clôture de la période.
            </p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Période de référence</th>
                  <th>Montant brut</th>
                  <th>Commission</th>
                  <th>Ajustements</th>
                  <th>Net</th>
                  <th>Statut</th>
                  <th>Date de versement</th>
                  <th aria-label="Relevé" />
                </tr>
              </thead>
              <tbody>
                {data.payouts.map((p) => (
                  <tr key={p.id} aria-selected={selected?.id === p.id}>
                    <td>
                      <Link href={`?versement=${p.id}`}>{period(p)}</Link>
                    </td>
                    <td>{money(p.gross_minor, p.currency)}</td>
                    <td>{money(p.commission_minor, p.currency)}</td>
                    <td>{money(p.adjustments_minor, p.currency)}</td>
                    <td><strong>{money(p.net_minor, p.currency)}</strong></td>
                    <td><Badge tone={STATUS[p.status].tone}>{STATUS[p.status].label}</Badge></td>
                    <td>{p.paid_at ? new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(new Date(p.paid_at)) : "—"}</td>
                    <td>
                      <a href={`/partner/reglements/${p.id}/releve`} aria-label={`Télécharger le relevé ${period(p)}`}>
                        <Download size={18} />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {selected && (
          <aside className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3>Détail du versement</h3>
              <Link href="/partner/reglements" aria-label="Fermer le détail"><X size={20} /></Link>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong>{period(selected)}</strong>
              <Badge tone={STATUS[selected.status].tone}>{STATUS[selected.status].label}</Badge>
            </div>
            <Row label="Montant brut" value={money(selected.gross_minor, c)} />
            <Row label="Commission" value={money(-selected.commission_minor, c)} />
            <Row label="Ajustements" value={money(selected.adjustments_minor, c)} />
            <div className="notice" style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>Net</strong>
              <strong>{money(selected.net_minor, c)}</strong>
            </div>
            {selected.status === "to_reconcile" && selected.confirmed_minor !== null && (
              <p className="error">
                Montant confirmé par le prestataire : {money(selected.confirmed_minor, c)}. L’équipe XPASS examine l’écart.
              </p>
            )}
            {selected.adjustments.length > 0 && (
              <>
                <strong>Éléments d’ajustement</strong>
                {selected.adjustments.map((a) => (
                  <Row key={a.reference} label={`${a.reference} · ${a.label}`} value={money(a.amount_minor, c)} />
                ))}
              </>
            )}
            <strong>Prestations ({selected.lines.length})</strong>
            {selected.lines.slice(0, 12).map((l, i) => (
              <Row
                key={i}
                label={`${new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short" }).format(new Date(l.occurred_at))} · ${l.offer_title}${l.kind === "late_cancellation" ? " (annulation tardive, moitié conservée)" : l.kind === "no_show" ? " (client absent)" : ""}`}
                value={money(l.gross_minor, c)}
              />
            ))}
            {selected.lines.length > 12 && <p className="muted">… et {selected.lines.length - 12} autres dans le relevé.</p>}
            <a className="btn primary" href={`/partner/reglements/${selected.id}/releve`}>
              <Download size={18} /> Télécharger le relevé
            </a>
          </aside>
        )}
      </div>

      <PayoutAccount
        status={data.psp_status}
        hasAccount={data.has_payout_account}
        configured={data.psp_configured}
        isDemo={data.is_demo}
        returning={versements === "retour" || versements === "relancer" ? versements : undefined}
      />
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
      <span className="muted">{label}</span>
      <span>{value}</span>
    </div>
  );
}
