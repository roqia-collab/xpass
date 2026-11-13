"use client";

import { useState, useTransition } from "react";

import { createRhService, setStaffPassword } from "./actions";

/** L'admin ouvre un service RH et donne l'accès à la personne qui le gère. */
export function CreateRhForm() {
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const [form, setForm] = useState({ name: "", city_label: "", hr_email: "", password: "" });
  if (!open) return <button className="btn primary" onClick={() => setOpen(true)}>Créer un service RH</button>;
  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
      onSubmit={(e) => {
        e.preventDefault();
        setMsg(undefined);
        start(async () => {
          const res = await createRhService({ name: form.name, city_label: form.city_label, hr_email: form.hr_email });
          const access = await setStaffPassword(form.hr_email, form.password);
          if (!res.ok && !access.ok) {
            setMsg({ ok: false, text: res.error });
            return;
          }
          if (!access.ok) {
            setMsg({ ok: false, text: `Service RH créé. Le mot de passe n’a pas été enregistré : ${access.error}` });
            return;
          }
          setMsg({
            ok: true,
            text: res.ok
              ? `Service RH créé. Sur rh.xpass.fr, identifiant : ${form.hr_email}. Donnez-lui ce mot de passe.`
              : `Mot de passe enregistré pour ${form.hr_email}. Ouvrez rh.xpass.fr et entrez ce Gmail et ce mot de passe.`,
          });
          if (access.ok) setForm({ name: "", city_label: "", hr_email: "", password: "" });
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
      <label className="field"><span>Mot de passe à lui remettre</span><input type="text" autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8} /></label>
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button type="button" className="btn ghost" onClick={() => setOpen(false)}>Fermer</button>
        <button
          type="button"
          className="btn outline"
          disabled={pending}
          onClick={() => {
            setMsg(undefined);
            start(async () => {
              const access = await setStaffPassword(form.hr_email, form.password);
              setMsg(access.ok
                ? { ok: true, text: `Mot de passe enregistré pour ${form.hr_email}. Ouvrez rh.xpass.fr et entrez ce Gmail et ce mot de passe.` }
                : { ok: false, text: access.error });
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
