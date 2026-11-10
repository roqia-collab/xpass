import { Star } from "lucide-react";

import { ErrorCard, Notice, PageHead } from "@/components/ui";
import { apiFetch } from "@/lib/session";

import { getCurrentLocation, getManagedLocation } from "../data";
import { replyToReview } from "../engagement-actions";
import { ReplyBox } from "../reply-box";

export const metadata = { title: "Avis" };

interface Reviews { average: number | null; count: number; items: { id: string; rating: number; comment: string | null; author: string; created_at: string; partner_reply: string | null }[] }

const day = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" });
const stars = (n: number) => "★".repeat(n) + "☆".repeat(5 - n);

/** Avis notés laissés par les clients après une prestation consommée ; le responsable peut répondre publiquement. */
export default async function ReviewsPage() {
  const [location, managed] = await Promise.all([getCurrentLocation(), getManagedLocation()]);
  if (!location) return <ErrorCard message="Aucun établissement n’est rattaché à ce compte." />;
  const r = await apiFetch<Reviews>(`/partner/locations/${location.id}/reviews`);
  return (
    <>
      <PageHead
        eyebrow={`${location.name} · ${location.district_label}`}
        title="Avis clients"
        subtitle="Seuls les clients venus chez vous (QR validé) peuvent noter, une fois par prestation. Les avis s’affichent sur votre fiche."
        action={r.count > 0 ? <span className="badge lavender" style={{ fontSize: 16 }}><Star size={16} aria-hidden /> {r.average?.toLocaleString("fr-FR")} / 5 · {r.count} avis</span> : undefined}
      />
      {r.count === 0 && <Notice>Pas encore d’avis. Les clients peuvent noter leur prestation depuis leur reçu dans l’application.</Notice>}
      {r.items.map((x) => (
        <section key={x.id} className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "baseline", flexWrap: "wrap" }}>
            <span aria-label={`${x.rating} sur 5`} style={{ color: "var(--coral)", fontSize: 18 }}>{stars(x.rating)}</span>
            <strong>{x.author}</strong>
            <span className="muted" style={{ fontSize: 13 }}>{day.format(new Date(x.created_at))}</span>
          </div>
          {x.comment && <p>{x.comment}</p>}
          {x.partner_reply ? (
            <p className="notice"><strong>Votre réponse :</strong>&nbsp;{x.partner_reply}</p>
          ) : managed?.can_edit ? (
            <ReplyBox label="Répondre publiquement" placeholder="Merci pour votre visite…" max={1000} submit={replyToReview.bind(null, location.id, x.id)} />
          ) : null}
        </section>
      ))}
    </>
  );
}
