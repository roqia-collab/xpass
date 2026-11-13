"use client";

import { hideReview } from "./actions";
import { DecisionPanel } from "./forms";

export interface AdminReview { id: string; rating: number; comment: string | null; author: string; created_at: string; status: string; location_name: string; partner_reply: string | null }

/** Masquage d'un avis (propos injurieux, hors sujet, données personnelles) : motif obligatoire, tracé. */
export function ReviewModeration({ rows }: { rows: AdminReview[] }) {
  return (
    <>
      {rows.map((r) => (
        r.status === "hidden" ? (
          <div key={r.id} className="card muted">{r.location_name} · {r.author} · {r.rating}/5 — avis masqué.</div>
        ) : (
          <DecisionPanel
            key={r.id}
            title={`${r.location_name} · ${"★".repeat(r.rating)}${"☆".repeat(5 - r.rating)} · ${r.author}`}
            description={r.comment ?? "(sans commentaire)"}
            buttons={[{ label: "Supprimer", confirm: "Retirer cet avis de la fiche publique ?", run: (why) => hideReview(r.id, why) }]}
          />
        )
      ))}
    </>
  );
}
