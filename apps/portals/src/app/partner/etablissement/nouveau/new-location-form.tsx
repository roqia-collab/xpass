"use client";

import { useState, useTransition } from "react";

import { addLocation } from "../../location-actions";

export function NewLocationForm({ currentId, categories }: { currentId: string; categories: { name: string; subs: { slug: string; name: string }[] }[] }) {
  const [pending, start] = useTransition();
  const [error, setError] = useState<string>();
  const [done, setDone] = useState<string>();
  const [f, setF] = useState({ location_name: "", subcategory_slug: "", kind_label: "", address_line: "", postal_code: "", city: "", description: "" });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });

  if (done) {
    return (
      <div className="card" role="status" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <h2>Établissement ajouté</h2>
        <p>Adresse retenue : <strong>{done}</strong></p>
        <p className="muted">Il est sélectionné dans l’en-tête. Ajoutez photo, prestations et horaires ; XPASS le publiera après relecture.</p>
        <a className="btn primary" href="/partner/etablissement" style={{ alignSelf: "flex-start" }}>Compléter l’établissement</a>
      </div>
    );
  }
  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 14 }}
      onSubmit={(e) => {
        e.preventDefault();
        setError(undefined);
        start(async () => {
          const r = await addLocation(currentId, f);
          if (r.ok) setDone(r.address);
          else setError(r.error);
        });
      }}
    >
      <div className="signup-grid">
        <label className="field"><span>Nom de l’établissement *</span><input value={f.location_name} onChange={set("location_name")} required maxLength={120} /></label>
        <label className="field">
          <span>Activité *</span>
          <select value={f.subcategory_slug} onChange={set("subcategory_slug")} required>
            <option value="">Choisir…</option>
            {categories.map((c) => (
              <optgroup key={c.name} label={c.name}>{c.subs.map((s) => <option key={s.slug} value={s.slug}>{s.name}</option>)}</optgroup>
            ))}
          </select>
        </label>
        <label className="field"><span>Type d’établissement</span><input value={f.kind_label} onChange={set("kind_label")} maxLength={80} /></label>
        <label className="field full"><span>Numéro et rue *</span><input value={f.address_line} onChange={set("address_line")} required autoComplete="street-address" /></label>
        <label className="field"><span>Code postal *</span><input value={f.postal_code} onChange={set("postal_code")} required inputMode="numeric" maxLength={5} /></label>
        <label className="field"><span>Commune *</span><input value={f.city} onChange={set("city")} required /></label>
        <label className="field full"><span>Présentation</span><textarea value={f.description} onChange={set("description")} maxLength={2000} /></label>
      </div>
      <button className="btn primary" type="submit" disabled={pending} style={{ alignSelf: "flex-start" }}>{pending ? "Envoi…" : "Ajouter l’établissement"}</button>
      {error && <p className="error" role="alert">{error}</p>}
    </form>
  );
}
