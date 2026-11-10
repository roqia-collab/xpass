import { Download } from "lucide-react";

import { Badge, Notice, PageHead } from "@/components/ui";
import { money } from "@/lib/money";
import { apiFetch } from "@/lib/session";
import type { AllocationDay, CompanyInvoice, CompanyOverview } from "@/lib/types";

import { FundingForm } from "../forms";
import { PayInvoiceButton } from "../online-forms";

export const metadata = { title: "Factures et rapports" };

const day = (iso: string) =>
  new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeZone: "UTC" }).format(new Date(`${iso.slice(0, 10)}T12:00:00Z`));

/** Maquette 25 — factures de financement, vue d'ensemble du mois, calendrier des allocations, export. */
export default async function FacturesPage({ searchParams }: { searchParams: Promise<{ periode?: string }> }) {
  const { periode } = await searchParams;
  const qs = periode && /^\d{4}-\d{2}$/.test(periode) ? `?period=${periode}` : "";
  const [overview, invoices, allocations] = await Promise.all([
    apiFetch<CompanyOverview>(`/company/overview${qs}`),
    apiFetch<CompanyInvoice[]>("/company/invoices"),
    apiFetch<AllocationDay[]>(`/company/allocations${qs}`),
  ]);
  const r = overview.report;
  const c = overview.contract?.currency ?? "EUR";
  const month = r.period.slice(0, 7);
  const label = new Intl.DateTimeFormat("fr-FR", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${r.period}T12:00:00Z`));
  const current = new Date();
  const months = Array.from({ length: 6 }, (_, i) => {
    const d = new Date(Date.UTC(current.getUTCFullYear(), current.getUTCMonth() - i, 1, 12));
    return d.toISOString().slice(0, 7);
  });
  const used = r.allocated_cost_minor ? Math.round((r.consumed_cost_minor * 100) / r.allocated_cost_minor) : 0;

  return (
    <>
      <PageHead title="Factures et reporting" image={`${process.env.NEXT_PUBLIC_MEDIA_BASE_URL ?? "http://localhost:3080/xpass-public"}/demo/locations/galerie-des-lumieres.jpg`} subtitle="Suivez vos factures, vos financements et l’utilisation de vos avantages." />
      <form style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <span className="pill">{overview.organization_name}</span>
        <span className="pill">Devise {c}</span>
        <select name="periode" defaultValue={month} aria-label="Période" className="pill" style={{ padding: 10 }}>
          {months.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <button className="btn outline">Afficher</button>
        <a className="btn primary" href={`/company/rapport?period=${month}`}>
          <Download size={18} /> Exporter le rapport
        </a>
      </form>

      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <div className="card" style={{ overflowX: "auto" }}>
          <h2>Factures</h2>
          <table className="table">
            <thead>
              <tr><th>N° de facture</th><th>Émission</th><th>Échéance</th><th>Montant</th><th>Statut</th></tr>
            </thead>
            <tbody>
              {invoices.map((i) => (
                <tr key={i.id}>
                  <td>
                    {i.reference}
                    {i.is_demo && <span className="muted"> · démo</span>}
                  </td>
                  <td>{day(i.issued_on)}</td>
                  <td>{day(i.due_on)}</td>
                  <td>{money(i.amount_minor, i.currency)}</td>
                  <td>
                    <Badge tone={i.status === "paid" ? "mint" : i.status === "pending" ? "lavender" : "grey"}>
                      {i.status === "paid" ? "Payée" : i.status === "pending" ? "En attente" : "Annulée"}
                    </Badge>
                    {i.status === "pending" && <div style={{ marginTop: 6 }}><PayInvoiceButton invoiceId={i.id} /></div>}
                  </td>
                </tr>
              ))}
              {invoices.length === 0 && (
                <tr><td colSpan={5} className="muted">Aucune facture.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <h2>Vue d’ensemble – {label}</h2>
          <div className="grid grid-2">
            <Stat label="Financement disponible" value={money(r.balance_minor, c)} />
            <Stat label="Crédits alloués utilisés" value={`${used} %`} detail={`${money(r.consumed_cost_minor, c)} / ${money(r.allocated_cost_minor, c)}`} />
            <Stat label="Collaborateurs activés" value={`${r.active} / ${r.eligible}`} />
            <Stat label="Alloué sur la période" value={`${r.allocated_credits} crédits`} />
          </div>
        </div>
      </div>

      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <div className="card" style={{ overflowX: "auto" }}>
          <h2>Calendrier des allocations</h2>
          <table className="table">
            <thead>
              <tr><th>Date</th><th>Libellé</th><th>Salariés</th><th>Montant</th></tr>
            </thead>
            <tbody>
              {allocations.map((a) => (
                <tr key={a.day}>
                  <td>{day(a.day)}</td>
                  <td>Allocations collaborateurs</td>
                  <td>{a.employees}</td>
                  <td>−{money(a.cost_minor, c)}</td>
                </tr>
              ))}
              {allocations.length === 0 && (
                <tr><td colSpan={4} className="muted">Aucune allocation sur la période.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {overview.can_edit && overview.contract && overview.contract.status !== "ended" && (
          <FundingForm creditPriceMinor={overview.contract.credit_price_minor} currency={c} />
        )}
      </div>
      <Notice>
        Une facture en attente se paie avec « Payer en ligne » (carte ou prélèvement). Le financement est disponible dès que
        le paiement est confirmé. Le PDF de facture n’est pas encore généré.
      </Notice>
    </>
  );
}

function Stat({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="notice" style={{ flexDirection: "column", gap: 4 }}>
      <span>{label}</span>
      <strong className="serif" style={{ fontSize: 26 }}>{value}</strong>
      {detail && <span className="muted">{detail}</span>}
    </div>
  );
}
