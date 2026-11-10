"use client";

import { ChevronDown, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { selectLocation } from "./location-actions";

export interface SwitcherLocation {
  id: string;
  name: string;
  district_label: string;
  status: string;
  cover: string | null;
}

const STATUS: Record<string, string> = { published: "Publié", draft: "Brouillon", hidden: "Masqué" };

/** Sélecteur d'établissement (en-tête du portail) et accès à l'ajout d'un établissement. */
export function LocationSwitcher({ locations, currentId }: { locations: SwitcherLocation[]; currentId: string }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const current = locations.find((l) => l.id === currentId) ?? locations[0]!;
  return (
    <details className="loc-switcher">
      <summary className="card" aria-label="Changer d’établissement">
        {current.cover ? <img className="thumb" src={current.cover} alt="" style={{ width: 40, height: 40 }} /> : <span className="thumb" style={{ width: 40, height: 40 }} />}
        <span style={{ lineHeight: 1.2 }}>
          <strong style={{ display: "block" }}>{current.name}</strong>
          <span className="muted" style={{ fontSize: 13 }}>{current.district_label}{locations.length > 1 ? ` · ${locations.length} établissements` : ""}</span>
        </span>
        <ChevronDown size={18} aria-hidden />
      </summary>
      <div className="loc-menu" role="menu">
        {locations.map((l) => (
          <button
            key={l.id}
            role="menuitemradio"
            aria-checked={l.id === current.id}
            disabled={pending}
            className={l.id === current.id ? "active" : ""}
            onClick={(e) => {
              (e.currentTarget.closest("details") as HTMLDetailsElement).open = false;
              start(async () => {
                await selectLocation(l.id);
                router.refresh();
              });
            }}
          >
            <strong>{l.name}</strong>
            <span className="muted">{l.district_label} · {STATUS[l.status] ?? l.status}</span>
          </button>
        ))}
        <a className="add" href="/partner/etablissement/nouveau" role="menuitem"><Plus size={16} aria-hidden /> Ajouter un établissement</a>
      </div>
    </details>
  );
}
