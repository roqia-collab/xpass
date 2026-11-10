import { CalendarDays, Coins, Store, Users } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Badge, PageHead } from "@/components/ui";
import { ACTOR_LABEL, DISPUTE_LABEL, type DisputeDetail } from "@/lib/admin-types";
import { money } from "@/lib/money";
import { ApiError, apiFetch, mediaUrl } from "@/lib/session";

import { DisputeActions } from "../../forms";

export const metadata = { title: "Dossier de litige" };

const timeFmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });
const SOURCE: Record<string, string> = { employer: "Employeur", personal: "Personnel", promotional: "Promotionnel" };
const PAYOUT: Record<string, string> = {
  pending: "Versement en préparation",
  in_transit: "Versement en cours",
  paid: "Déjà payé",
  to_reconcile: "Versement à rapprocher",
  failed: "Versement en échec",
};

/** Maquette 28 — dossier de litige : réservation, chronologie, impacts, décision tracée. */
export default async function DisputePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  let d: DisputeDetail;
  try {
    d = await apiFetch<DisputeDetail>(`/admin/disputes/${id}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
  const open = ["open", "in_review", "waiting_customer"].includes(d.status);
  const cover = mediaUrl(d.cover_image_key);
  const start = new Date(`${d.local_start}:00`);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 340px", gap: 24 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 0 }}>
        <p className="muted"><Link href="/admin/litiges">Litiges</Link> › {d.reference}</p>
        <PageHead
          title={`Dossier de litige #${d.reference}`}
          subtitle={`Ouvert le ${timeFmt.format(new Date(d.created_at))} · mis à jour le ${timeFmt.format(new Date(d.updated_at))}`}
          action={<Badge tone={DISPUTE_LABEL[d.status].tone}>{DISPUTE_LABEL[d.status].label}</Badge>}
        />
        <div className="card" style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
          {cover && <img src={cover} alt="" style={{ width: 180, height: 110, objectFit: "cover", borderRadius: 14 }} />}
          <div style={{ flex: 1, minWidth: 200 }}>
            <p className="eyebrow">{d.location_kind}</p>
            <h2>{d.location_name}</h2>
            <p className="muted">{d.location_address}</p>
            <p><CalendarDays size={16} aria-hidden /> {new Intl.DateTimeFormat("fr-FR", { dateStyle: "full", timeStyle: "short" }).format(start)} · {d.offer_title}</p>
            <p><Users size={16} aria-hidden /> {d.party_size} participant(s) · client : {d.customer_name}</p>
          </div>
          <div className="notice" style={{ flexDirection: "column", minWidth: 200 }}>
            <strong><Coins size={16} aria-hidden /> {d.total_credits} crédits utilisés</strong>
            {Object.entries(d.funding).map(([s, n]) => (
              <span key={s}>{SOURCE[s] ?? s} : {n} crédits</span>
            ))}
            <Badge tone="grey">{d.booking_status === "redeemed" ? "Consommée" : "Annulation tardive"}</Badge>
          </div>
        </div>
        <div className="grid grid-2" style={{ alignItems: "start" }}>
          <div className="card">
            <h3>Motif du client</h3>
            <p style={{ whiteSpace: "pre-wrap" }}>{d.reason}</p>
          </div>
          <div className="card">
            <h3>Notes opérateur</h3>
            <p className="muted" style={{ whiteSpace: "pre-wrap" }}>{d.operator_notes ?? "—"}</p>
          </div>
        </div>
        <div className="card">
          <h3>Impacts {open ? "proposés" : "appliqués"}</h3>
          <div className="grid grid-3" style={{ marginTop: 10 }}>
            <div className="notice" style={{ flexDirection: "column" }}>
              <strong>Crédits client</strong>
              <span>{open ? `Restitution possible : ${d.total_credits} crédits` : d.credits_restored ? `${d.credits_restored} crédits restitués` : "Aucune restitution"}</span>
              <span className="muted">Même source que les crédits consommés.</span>
            </div>
            <div className="notice" style={{ flexDirection: "column", background: "#ffe7e2" }}>
              <strong>Dette partenaire</strong>
              <span>
                {d.payable_net_minor !== null ? `Revenant au partenaire : ${money(d.payable_net_minor, d.currency)}` : "Non valorisée"}
              </span>
              {d.partner_adjustment_minor ? <span>Ajustement appliqué : −{money(d.partner_adjustment_minor, d.currency)}</span> : null}
            </div>
            <div className="notice" style={{ flexDirection: "column" }}>
              <strong>Paiement client</strong>
              <span>Aucun remboursement monétaire : la réservation a été réglée en crédits.</span>
            </div>
          </div>
        </div>
        <div className="card" style={{ overflowX: "auto" }}>
          <h3>Chronologie et audit</h3>
          <table className="table">
            <thead><tr><th>Date</th><th>Acteur</th><th>Action</th><th>Motif / détail</th></tr></thead>
            <tbody>
              {d.redeemed_at && (
                <tr><td>{timeFmt.format(new Date(d.redeemed_at))}</td><td>Partenaire</td><td>Réservation consommée (scan)</td><td>—</td></tr>
              )}
              {d.timeline.map((a, i) => (
                <tr key={i}>
                  <td>{timeFmt.format(new Date(a.created_at))}</td>
                  <td>{a.actor_name ?? ACTOR_LABEL[a.actor_kind]}</td>
                  <td>{a.action}</td>
                  <td>{a.reason ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {d.resolution_reason && <p style={{ marginTop: 8 }}><strong>Décision :</strong> {d.resolution_reason}</p>}
        </div>
      </div>
      <aside style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <h3><Store size={18} aria-hidden /> Versement partenaire</h3>
          <Badge tone={d.payout_status === "paid" ? "mint" : "lavender"}>{d.payout_status ? PAYOUT[d.payout_status] ?? d.payout_status : "Pas encore versé"}</Badge>
          <p className="muted" style={{ fontSize: 14 }}>
            {d.payout_status === "paid"
              ? "Cette réservation a déjà été versée : un ajustement sera déduit d’un prochain versement, sans modifier le versement réalisé."
              : "Un ajustement éventuel sera déduit du prochain versement du partenaire."}
          </p>
          <Link className="btn outline" href={`/admin/partenaires/${d.merchant_id}`}>Voir la fiche partenaire</Link>
        </div>
        <DisputeActions id={d.id} netMinor={d.payable_net_minor} open={open} />
      </aside>
    </div>
  );
}
