"use client";

import { useState, useTransition } from "react";

import { createRhService, setStaffPassword } from "./actions";

/** L'admin ouvre un service RH et donne l'accès à la personne qui le gère. */
export function CreateRhForm() {
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const [form, setForm] = useState({ name: "", city_label: "Paris", hr_email: "", password: "" });
  const [handover, setHandover] = useState<{ email: string; password: string }>();
  if (!open) return <button className="btn primary" onClick={() => setOpen(true)}>Ajouter</button>;
  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
      onSubmit={(e) => {
        e.preventDefault();
        setMsg(undefined);
        start(async () => {
          const given = { email: form.hr_email.trim(), password: form.password };
          const res = await createRhService({ name: form.name, city_label: form.city_label, hr_email: form.hr_email });
          const access = await setStaffPassword(given.email, given.password);
          if (!access.ok) {
            setHandover(undefined);
            setMsg({
              ok: false,
              text: res.ok
                ? `Service RH créé, mais le mot de passe n’a pas été enregistré : ${access.error}`
                : res.error,
            });
            return;
          }
          setHandover(given);
          setMsg({
            ok: true,
            text: res.ok
              ? "Service RH créé. Le mot de passe est affiché ci-dessous : copiez-le, il ne sera plus affiché."
              : "Mot de passe enregistré. Il est affiché ci-dessous.",
          });
          setForm({ name: "", city_label: "Paris", hr_email: "", password: "" });
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
      <label className="field"><span>Gmail de l’administrateur RH, c’est son identifiant</span><input type="email" value={form.hr_email} onChange={(e) => setForm({ ...form, hr_email: e.target.value })} required /></label>
      <label className="field"><span>Mot de passe à lui remettre</span><input type="text" autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8} /><small>8 caractères minimum, avec une lettre et un chiffre. Il s’affiche après la création.</small></label>
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
      {handover && (
        <div className="notice mint" role="status">
          <p style={{ margin: 0 }}>Identifiant : <strong>{handover.email}</strong></p>
          <p style={{ margin: "6px 0 0" }}>Mot de passe : <strong>{handover.password}</strong></p>
          <p style={{ margin: "6px 0 0" }}>Ouvrez https://rh.xpass.fr et entrez ce Gmail et ce mot de passe.</p>
        </div>
      )}
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button type="button" className="btn ghost" onClick={() => setOpen(false)}>Fermer</button>
        <button
          type="button"
          className="btn outline"
          disabled={pending}
          onClick={() => {
            setMsg(undefined);
            start(async () => {
              const given = { email: form.hr_email.trim(), password: form.password };
              const access = await setStaffPassword(given.email, given.password);
              if (!access.ok) {
                setHandover(undefined);
                setMsg({ ok: false, text: access.error });
                return;
              }
              setHandover(given);
              setMsg({ ok: true, text: "Mot de passe enregistré. Il est affiché ci-dessous." });
            });
          }}
        >
          Enregistrer le mot de passe
        </button>
        <button className="btn primary" disabled={pending}>Créer</button>
      </div>
    </form>
  );
}
