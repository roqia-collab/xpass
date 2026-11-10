"use client";

import type { ChangeRequestRow } from "@/lib/admin-types";

import { decideChange } from "./actions";
import { DecisionPanel } from "./forms";

/** Demandes de modification d'établissement : avant / après, décision motivée (appliquée si acceptée). */
export function ChangeRequests({ rows }: { rows: ChangeRequestRow[] }) {
  if (rows.length === 0) return <p className="muted">Aucune demande de modification en attente.</p>;
  return (
    <>
      {rows.map((r) => {
        const c = r.changes;
        const lines = [
          c.name && `Nom : ${r.location_name} → ${c.name}`,
          c.subcategory && `Activité → ${c.subcategory.name}`,
          c.kind_label && `Type → ${c.kind_label}`,
          c.address && `Adresse : ${c.address.previous} → ${c.address.label} (confiance ${Math.round(c.address.score * 100)} %)`,
        ].filter(Boolean) as string[];
        return (
          <DecisionPanel
            key={r.id}
            title={`${r.location_name} · ${r.merchant_name}`}
            description={`Demandé par ${r.requested_by}. ${lines.join(" · ")}`}
            buttons={[
              { label: "Accepter et appliquer", tone: "primary", run: (why) => decideChange(r.id, true, why) },
              { label: "Refuser", run: (why) => decideChange(r.id, false, why) },
            ]}
          />
        );
      })}
    </>
  );
}
