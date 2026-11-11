"use client";

import { DecisionPanel } from "./forms";
import { setDemoLocations } from "./actions";

/** Lieux de démonstration : masqués d'un geste quand les vrais partenaires sont publiés (motif tracé). */
export function DemoLocationsPanel({ counts, canEdit }: { counts: Record<string, number>; canEdit: boolean }) {
  const published = counts.published ?? 0;
  const hidden = counts.hidden ?? 0;
  if (!published && !hidden) return null;
  const description = `${published} lieu(x) de démonstration visible(s) dans l’application, ${hidden} masqué(s). ` +
    "Masquez-les quand les vrais commerçants sont validés et publiés.";
  if (!canEdit) return <p className="muted">{description}</p>;
  return (
    <DecisionPanel
      title="Lieux de démonstration"
      description={description}
      buttons={[
        ...(published ? [{ label: "Masquer les lieux de démo", tone: "primary" as const, confirm: "Masquer tous les lieux de démonstration ?", run: (why: string) => setDemoLocations(false, why) }] : []),
        ...(hidden ? [{ label: "Réafficher les lieux de démo", run: (why: string) => setDemoLocations(true, why) }] : []),
      ]}
    />
  );
}
