"use client";

import { useState, useTransition } from "react";

import { createMerchant } from "./actions";

export function CreateMerchantForm({ categories }: { categories: { name: string; subs: { slug: string; name: string }[] }[] }) {
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const first = categories[0]?.subs[0]?.slug ?? "";
  const [form, setForm] = useState({
    display_name: "", owner_email: "", location_name: "", subcategory_slug: first,
    address_line: "", postal_code: "", city: "Paris", description: "", price_credits: "8",
  });
  if (!open) return <button className="btn primary" onClick={() => setOpen(true)}>Ajouter un commerçant</button>;
  const set = (key: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [key]: e.target.value });
  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
      onSubmit={(e) => {
        e.preventDefault();
        setMsg(undefined);
        start(async () => {
          const res = await createMerchant(form);
          setMsg(res.ok
            ? { ok: true, text: "Commerçant créé. Son établissement est visible dans l’application client. Le responsable se connecte avec l’adresse indiquée." }
            : { ok: false, text: res.error });
        });
      }}
    >
      <h3>Nouveau commerçant</h3>
      <label className="field"><span>Nom commercial</span><input value={form.display_name} onChange={set("display_name")} required /></label>
      <label className="field"><span>E-mail du responsable</span><input type="email" value={form.owner_email} onChange={set("owner_email")} required /></label>
      <label className="field"><span>Nom de l’établissement</span><input value={form.location_name} onChange={set("location_name")} required /></label>
      <label className="field">
        <span>Activité</span>
        <select value={form.subcategory_slug} onChange={set("subcategory_slug")}>
          {categories.map((c) => (
            <optgroup key={c.name} label={c.name}>
              {c.subs.map((s) => <option key={s.slug} value={s.slug}>{s.name}</option>)}
            </optgroup>
          ))}
        </select>
      </label>
      <label className="field"><span>Adresse</span><input value={form.address_line} onChange={set("address_line")} placeholder="5 rue de la Roquette" required /></label>
      <div className="grid grid-2">
        <label className="field"><span>Code postal</span><input value={form.postal_code} onChange={set("postal_code")} required /></label>
        <label className="field"><span>Ville</span><input value={form.city} onChange={set("city")} required /></label>
      </div>
      <label className="field"><span>Prix de la prestation (crédits)</span><input type="number" min={1} max={500} value={form.price_credits} onChange={set("price_credits")} required /></label>
      <label className="field"><span>Description</span><textarea value={form.description} onChange={set("description")} /></label>
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button type="button" className="btn ghost" onClick={() => setOpen(false)}>Fermer</button>
        <button className="btn primary" disabled={pending}>Publier dans l’application</button>
      </div>
    </form>
  );
}
