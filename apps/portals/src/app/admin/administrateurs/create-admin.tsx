"use client";

import { useState, useTransition } from "react";

import { createAdministrator } from "./actions";

export function CreateAdminForm() {
  const [form, setForm] = useState({ email: "", full_name: "", password: "" });
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const [handover, setHandover] = useState<{ email: string; password: string }>();
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value });

  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
      onSubmit={(e) => {
        e.preventDefault();
        setMsg(undefined);
        start(async () => {
          const created = { email: form.email.trim(), password: form.password };
          const res = await createAdministrator(form);
          if (!res.ok) {
            setHandover(undefined);
            setMsg({ ok: false, text: res.error });
            return;
          }
          setHandover(created);
          setMsg({ ok: true, text: "Admin créé. Copiez le mot de passe ci-dessous : il ne sera plus affiché." });
          setForm({ email: "", full_name: "", password: "" });
        });
      }}
    >
      <h3>Nouvel admin</h3>
      <label className="field"><span>Nom</span><input value={form.full_name} onChange={set("full_name")} required /></label>
      <label className="field"><span>Gmail, c’est son identifiant</span><input type="email" value={form.email} onChange={set("email")} placeholder="prenom.nom@gmail.com" required /></label>
      <label className="field"><span>Mot de passe à lui remettre</span><input type="text" autoComplete="new-password" value={form.password} onChange={set("password")} required minLength={8} /><small>8 caractères minimum, avec une lettre et un chiffre. Gmail uniquement. Il s’affiche après la création.</small></label>
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
      {handover && (
        <div className="notice mint" role="status">
          <p style={{ margin: 0 }}>Identifiant : <strong>{handover.email}</strong></p>
          <p style={{ margin: "6px 0 0" }}>Mot de passe : <strong>{handover.password}</strong></p>
          <p style={{ margin: "6px 0 0" }}>Connexion : admin.xpass.fr, avec ce Gmail et ce mot de passe.</p>
        </div>
      )}
      <button className="btn primary" disabled={pending}>Créer l’admin</button>
    </form>
  );
}
