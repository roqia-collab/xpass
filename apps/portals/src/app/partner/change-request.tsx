"use client";

import { PencilLine } from "lucide-react";
import { useState, useTransition } from "react";

import { Badge } from "@/components/ui";

import { requestChange } from "./location-actions";

export interface ChangeRow {
  id: string;
  status: "pending" | "approved" | "rejected";
  changes: Record<string, unknown>;
  decision_reason: string | null;
  created_at: string;
}

const LABEL = { pending: "En attente de validation", approved: "Acceptée", rejected: "Refusée" } as const;
const TONE = { pending: "lavender", approved: "mint", rejected: "coral" } as const;
const FIELDS: Record<string, string> = { name: "nom", subcategory: "activité", kind_label: "type", address: "adresse" };

/** Nom, activité et adresse : modifiés après validation XPASS (l'adresse est géocodée dès la demande). */
export function ChangeRequest({
  locationId, current, categories, history,
}: {
  locationId: string;
  current: { name: string; subcategory_slug: string; kind_label: string };
  categories: { name: string; subs: { slug: string; name: string }[] }[];
  history: ChangeRow[];
}) {
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const [f, setF] = useState({ name: current.name, subcategory_slug: current.subcategory_slug, kind_label: current.kind_label, address_line: "", postal_code: "", city: "" });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });
  const last = history[0];
  const waiting = last?.status === "pending";

  return (
    <section className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <h3 style={{ flex: 1 }}><PencilLine size={18} aria-hidden /> Nom, activité et adresse</h3>
        {last && <Badge tone={TONE[last.status]}>{LABEL[last.status]}</Badge>}
      </div>
      {last && (
        <p className="muted" style={{ fontSize: 14 }}>
          Dernière demande : {Object.keys(last.changes).map((k) => FIELDS[k] ?? k).join(", ")}
          {last.status === "rejected" && last.decision_reason ? ` — motif : ${last.decision_reason}` : ""}
        </p>
      )}
      {!open && !waiting && (
        <button className="btn outline" style={{ alignSelf: "flex-start" }} onClick={() => setOpen(true)}>Demander une modification</button>
      )}
      {open && !waiting && (
        <form
          style={{ display: "flex", flexDirection: "column", gap: 12 }}
          onSubmit={(e) => {
            e.preventDefault();
            setMsg(undefined);
            start(async () => {
              const r = await requestChange(locationId, f);
              setMsg(r.ok ? { ok: true, text: "Demande envoyée : la fiche sera mise à jour après validation par XPASS." } : { ok: false, text: r.error });
              if (r.ok) setOpen(false);
            });
          }}
        >
          <div className="signup-grid">
            <label className="field"><span>Nom</span><input value={f.name} onChange={set("name")} maxLength={120} /></label>
            <label className="field">
              <span>Activité</span>
              <select value={f.subcategory_slug} onChange={set("subcategory_slug")}>
                {categories.map((c) => (
                  <optgroup key={c.name} label={c.name}>{c.subs.map((s) => <option key={s.slug} value={s.slug}>{s.name}</option>)}</optgroup>
                ))}
              </select>
            </label>
            <label className="field"><span>Type d’établissement</span><input value={f.kind_label} onChange={set("kind_label")} maxLength={80} /></label>
            <label className="field full"><span>Nouvelle adresse (laisser vide si inchangée)</span><input value={f.address_line} onChange={set("address_line")} placeholder="Numéro et rue" /></label>
            <label className="field"><span>Code postal</span><input value={f.postal_code} onChange={set("postal_code")} inputMode="numeric" maxLength={5} /></label>
            <label className="field"><span>Commune</span><input value={f.city} onChange={set("city")} /></label>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn primary" type="submit" disabled={pending}>{pending ? "Envoi…" : "Envoyer la demande"}</button>
            <button className="btn ghost" type="button" onClick={() => setOpen(false)}>Annuler</button>
          </div>
        </form>
      )}
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
    </section>
  );
}
