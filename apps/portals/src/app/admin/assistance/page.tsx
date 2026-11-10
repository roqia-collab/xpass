import Link from "next/link";

import { LiveRefresh } from "@/components/live-refresh";
import { Badge, PageHead } from "@/components/ui";
import { apiFetch } from "@/lib/session";

import { SupportReply } from "../forms";

export const metadata = { title: "Assistance" };

interface VenueThread {
  id: string;
  booking_id: string;
  location_name: string;
  customer_name: string;
  offer_title: string;
  last_message: string;
  last_message_at: string;
  unread_for_venue: boolean;
}

interface SupportRow {
  id: string;
  reference: string;
  category: string;
  subject: string;
  message: string;
  status: "open" | "answered" | "closed";
  reply: string | null;
  replied_at: string | null;
  created_at: string;
  customer_name: string;
  customer_email: string;
}

const CATEGORY: Record<string, string> = {
  booking: "Réservation",
  credits: "Crédits",
  account: "Compte",
  partner: "Établissement",
  other: "Autre",
};
const STATUS: Record<SupportRow["status"], { label: string; tone: "coral" | "lavender" | "grey" }> = {
  open: { label: "À traiter", tone: "coral" },
  answered: { label: "Répondu", tone: "lavender" },
  closed: { label: "Clos", tone: "grey" },
};

/** Demandes d'assistance des clients (écran 16) : réponse envoyée par e-mail et visible dans l'application. */
export default async function SupportPage({ searchParams }: { searchParams: Promise<{ statut?: string }> }) {
  const { statut } = await searchParams;
  const status = statut && ["open", "answered", "closed", "all"].includes(statut) ? statut : "open";
  const [rows, venue] = await Promise.all([
    apiFetch<SupportRow[]>(`/admin/support?status=${status}`),
    apiFetch<VenueThread[]>("/admin/conversations"),
  ]);
  const fmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });
  return (
    <>
      <LiveRefresh />
      <PageHead title="Assistance" subtitle="Demandes des clients et messages envoyés depuis l’application vers les établissements. Même fil partout." />
      {venue.length > 0 && (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <h2>Messages établissements</h2>
          <p className="muted" style={{ fontSize: 13 }}>Les mêmes conversations que dans l’application et le portail commerçant.</p>
          {venue.map((c) => (
            <div key={c.id} className="list-row" style={{ padding: "10px 0" }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <strong>{c.customer_name}</strong> <span className="muted">· {c.location_name} · {c.offer_title}</span>
                <div className="muted" style={{ fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.last_message}</div>
              </div>
              {c.unread_for_venue && <Badge tone="coral">Non lu par le site</Badge>}
              <span className="muted" style={{ fontSize: 12 }}>{fmt.format(new Date(c.last_message_at))}</span>
            </div>
          ))}
        </div>
      )}
      <div style={{ display: "flex", gap: 8 }}>
        {[["open", "À traiter"], ["answered", "Répondu"], ["closed", "Clos"], ["all", "Tout"]].map(([v, l]) => (
          <Link key={v} className={`btn ${status === v ? "outline" : "ghost"}`} href={`?statut=${v}`}>{l}</Link>
        ))}
      </div>
      {rows.length === 0 && <p className="muted">Aucune demande.</p>}
      {rows.map((r) => (
        <div key={r.id} className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
            <strong>{r.reference} · {r.subject}</strong>
            <span style={{ display: "flex", gap: 8 }}>
              <Badge tone="grey">{CATEGORY[r.category] ?? r.category}</Badge>
              <Badge tone={STATUS[r.status].tone}>{STATUS[r.status].label}</Badge>
            </span>
          </div>
          <span className="muted" style={{ fontSize: 13 }}>{r.customer_name} · {r.customer_email} · {fmt.format(new Date(r.created_at))}</span>
          <p style={{ whiteSpace: "pre-wrap" }}>{r.message}</p>
          {r.reply && (
            <div className="notice" style={{ flexDirection: "column" }}>
              <strong>Réponse{r.replied_at ? ` du ${fmt.format(new Date(r.replied_at))}` : ""}</strong>
              <span style={{ whiteSpace: "pre-wrap" }}>{r.reply}</span>
            </div>
          )}
          {r.status !== "closed" && <SupportReply id={r.id} />}
        </div>
      ))}
    </>
  );
}
