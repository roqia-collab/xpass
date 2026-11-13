"use client";

import { useState, useTransition } from "react";

import { createAdministrator } from "./actions";

export function CreateAdminForm() {
  const [form, setForm] = useState({ email: "", full_name: "", password: "" });
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value });

  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
      onSubmit={(e) => {
        e.preventDefault();
        setMsg(undefined);
        start(async () => {
          const res = await createAdministrator(form);
          setMsg(res.ok
            ? { ok: true, text: `Admin créé. Identifiant : ${form.email}. Donnez-lui ce mot de passe. Il se connecte sur la page admin.` }
            : { ok: false, text: res.error });
          if (res.ok) setForm({ email: "", full_name: "", password: "" });
        });
      }}
    >
      <h3>Nouvel admin</h3>
      <label className="field"><span>Nom</span><input value={form.full_name} onChange={set("full_name")} required /></label>
      <label className="field"><span>Gmail, c’est son identifiant</span><input type="email" value={form.email} onChange={set("email")} placeholder="prenom.nom@gmail.com" required /></label>
      <label className="field"><span>Mot de passe à lui remettre</span><input type="text" autoComplete="new-password" value={form.password} onChange={set("password")} required minLength={8} /></label>
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
      <button className="btn primary" disabled={pending}>Créer l’admin</button>
    </form>
  );
}
