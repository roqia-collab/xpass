import { Badge, Notice, PageHead } from "@/components/ui";
import type { Reconciliation } from "@/lib/admin-types";
import { money } from "@/lib/money";
import { apiFetch } from "@/lib/session";

import { ConfirmInvoice, EventActions, PayoutActions } from "../forms";

export const metadata = { title: "Paiements et rapprochement" };

const fmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" });

/** Rapprochement : écarts de versements, anomalies de webhooks, virements entreprises à confirmer. */
export default async function PaymentsPage() {
  const r = await apiFetch<Reconciliation>("/admin/reconciliation");
  const ro = !r.is_admin;
  return (
    <>
      <PageHead title="Paiements et rapprochement" subtitle="Chaque action exige un motif et est enregistrée dans le journal d’audit." />
      {ro && <Notice>Lecture seule : les actions de rapprochement sont réservées aux administrateurs XPASS.</Notice>}

      <div className="card" style={{ overflowX: "auto" }}>
        <h3>Versements commerçants à rapprocher</h3>
        <table className="table">
          <thead><tr><th>Commerçant</th><th>Semaine du</th><th>Net attendu</th><th>Confirmé par le prestataire</th><th>Statut</th><th /></tr></thead>
          <tbody>
            {r.payouts.map((p) => (
              <tr key={p.id}>
                <td>{p.merchant_name}</td>
                <td>{p.period_start}</td>
                <td>{money(p.net_minor, p.currency)}</td>
                <td>{p.confirmed_minor !== null ? money(p.confirmed_minor, p.currency) : "—"}</td>
                <td><Badge tone="coral">{p.status === "failed" ? "Échec" : "Écart"}</Badge></td>
                <td>{!ro && <PayoutActions id={p.id} status={p.status} />}</td>
              </tr>
            ))}
            {r.payouts.length === 0 && <tr><td colSpan={6} className="muted">Aucun écart.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ overflowX: "auto" }}>
        <h3>Webhooks de paiement non appliqués</h3>
        <p className="muted" style={{ fontSize: 13 }}>Anomalies (montant, devise) ou événements en attente de l’objet lié. Rien n’est appliqué automatiquement.</p>
        <table className="table">
          <thead><tr><th>Reçu le</th><th>Type</th><th>Identifiant</th><th>Tentatives</th><th>Erreur</th><th /></tr></thead>
          <tbody>
            {r.events.map((e) => (
              <tr key={e.id}>
                <td>{fmt.format(new Date(e.received_at))}</td>
                <td>{e.event_type}</td>
                <td className="muted">{e.event_id}</td>
                <td>{e.attempts}{e.blocked ? " (bloqué)" : ""}</td>
                <td className="muted">{e.last_error}</td>
                <td>{!ro && <EventActions id={e.id} />}</td>
              </tr>
            ))}
            {r.events.length === 0 && <tr><td colSpan={6} className="muted">Aucune anomalie.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ overflowX: "auto" }}>
        <h3>Factures entreprises en attente de virement</h3>
        <table className="table">
          <thead><tr><th>Facture</th><th>Entreprise</th><th>Montant</th><th>Émise le</th><th>Échéance</th><th /></tr></thead>
          <tbody>
            {r.employer_invoices.map((i) => (
              <tr key={i.id}>
                <td>{i.reference}{i.is_demo ? " · démo" : ""}</td>
                <td>{i.organization_name}</td>
                <td>{money(i.amount_minor, i.currency)}</td>
                <td>{i.issued_on}</td>
                <td>{i.due_on}</td>
                <td>{!ro && <ConfirmInvoice id={i.id} label={i.reference} />}</td>
              </tr>
            ))}
            {r.employer_invoices.length === 0 && <tr><td colSpan={6} className="muted">Aucune facture en attente.</td></tr>}
          </tbody>
        </table>
      </div>
      <Notice>« Virement reçu » se fait après contrôle du relevé bancaire : le rapprochement bancaire automatique n’est pas encore branché.</Notice>
    </>
  );
}
