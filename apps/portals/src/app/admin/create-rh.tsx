"use client";

import { useState, useTransition } from "react";

import { createRhService } from "./actions";

/** L'admin ouvre un service RH et donne l'accès à la personne qui le gère. */
export function CreateRhForm() {
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const [form, setForm] = useState({ name: "", city_label: "", hr_email: "" });
  if (!open) return <button className="btn primary" onClick={() => setOpen(true)}>Créer un service RH</button>;
  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
      onSubmit={(e) => {
        e.preventDefault();
        setMsg(undefined);
        start(async () => {
          const res = await createRhService(form);
          setMsg(res.ok
            ? { ok: true, text: "Service RH créé. La personne se connecte avec cette adresse pour ouvrir l’espace RH." }
            : { ok: false, text: res.error });
          if (res.ok) setForm({ name: "", city_label: "", hr_email: "" });
        });
      }}
    >
      <h3>Nouveau service RH</h3>
      <p className="muted" style={{ fontSize: 14 }}>
        Contrat écrit : crédit à 1,00 €, durée 12 mois, ville couverte Paris, commission commerçant 10 %, annulation gratuite 24 h avant.
        Les crédits des salariés n’apparaissent dans l’application qu’une fois la facture payée. Ce service crée ensuite ses commerçants.
      </p>
      <label className="field"><span>Nom</span><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
      <label className="field"><span>Ville</span><input value={form.city_label} placeholder="Paris" onChange={(e) => setForm({ ...form, city_label: e.target.value })} /></label>
      <label className="field"><span>E-mail de l’administrateur RH</span><input type="email" value={form.hr_email} onChange={(e) => setForm({ ...form, hr_email: e.target.value })} required /></label>
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button type="button" className="btn ghost" onClick={() => setOpen(false)}>Fermer</button>
        <button className="btn primary" disabled={pending}>Créer</button>
      </div>
    </form>
  );
}
