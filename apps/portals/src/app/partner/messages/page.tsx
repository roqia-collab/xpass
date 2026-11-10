import Link from "next/link";

import { LiveRefresh } from "@/components/live-refresh";
import { Badge, ErrorCard, Notice, PageHead } from "@/components/ui";
import { apiFetch } from "@/lib/session";

import { getCurrentLocation } from "../data";
import { sendPartnerMessage } from "../engagement-actions";
import { ReplyBox } from "../reply-box";

export const metadata = { title: "Messages" };

interface Row { id: string; booking_id: string; customer_name: string; offer_title: string; starts_at: string; last_message_at: string; last_message: string; unread: boolean }
interface Thread { can_write: boolean; closed_reason: string | null; messages: { id: string; sender_kind: string; body: string; created_at: string }[] }

const when = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });

/** Messages des clients au sujet de leurs réservations (maquette 21, entrée « Messages »). */
export default async function MessagesPage({ searchParams }: { searchParams: Promise<{ c?: string }> }) {
  const location = await getCurrentLocation();
  if (!location) return <ErrorCard message="Aucun établissement n’est rattaché à ce compte." />;
  const rows = await apiFetch<Row[]>(`/partner/locations/${location.id}/conversations`);
  const { c } = await searchParams;
  const current = rows.find((r) => r.id === c) ?? rows[0];
  const thread = current ? await apiFetch<Thread>(`/partner/locations/${location.id}/conversations/${current.id}`) : null;
  return (
    <>
      <LiveRefresh />
      <PageHead eyebrow={`${location.name} · ${location.district_label}`} title="Messages" subtitle="Questions de vos clients sur leurs réservations. Répondez depuis ce portail ; le client est prévenu dans l’application." />
      {rows.length === 0 ? (
        <Notice>Aucun message pour le moment. Un client peut vous écrire dès que sa réservation est confirmée.</Notice>
      ) : (
        <div className="grid grid-2" style={{ alignItems: "start", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1.6fr)" }}>
          <section className="card" style={{ display: "flex", flexDirection: "column" }}>
            {rows.map((r) => (
              <Link key={r.id} href={`?c=${r.id}`} className="list-row" style={{ display: "flex", gap: 10, alignItems: "center", background: r.id === current?.id ? "var(--lavender)" : undefined, borderRadius: 12, padding: "10px 12px" }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <strong>{r.customer_name}</strong> <span className="muted" style={{ fontSize: 13 }}>· {r.offer_title}</span>
                  <div className="muted" style={{ fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.last_message}</div>
                </div>
                {r.unread && <Badge tone="coral">Nouveau</Badge>}
              </Link>
            ))}
          </section>
          {current && thread && (
            <section className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <h3>{current.customer_name} · {current.offer_title}</h3>
              <p className="muted" style={{ fontSize: 13 }}>Réservation du {when.format(new Date(current.starts_at))}</p>
              <div className="chat">
                {thread.messages.map((m) => (
                  <div key={m.id} className={`bubble ${m.sender_kind === "partner" ? "mine" : ""} ${m.sender_kind === "system" ? "system" : ""}`}>
                    {m.sender_kind === "system" && <span className="muted">Message automatique</span>}
                    <p>{m.body}</p>
                    <span className="muted">{when.format(new Date(m.created_at))}</span>
                  </div>
                ))}
              </div>
              {thread.can_write ? (
                <ReplyBox label="Votre réponse" placeholder="Écrivez votre réponse…" max={2000} submit={sendPartnerMessage.bind(null, location.id, current.id)} />
              ) : (
                <Notice>{thread.closed_reason}</Notice>
              )}
            </section>
          )}
        </div>
      )}
    </>
  );
}
