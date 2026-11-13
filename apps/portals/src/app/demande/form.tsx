"use client";

import { useState, useTransition } from "react";

import { submitAccessRequest } from "./actions";

const empty = { kind: "rh" as "rh" | "merchant", gmail: "", full_name: "", place_name: "", city: "Paris", message: "", website: "" };

export function AccessForm() {
  const [form, setForm] = useState(empty);
  const [pending, start] = useTransition();
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const set = (key: keyof typeof empty) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [key]: e.target.value });

  if (done) {
    return (
      <p className="notice mint" role="status">
        Demande envoyée. L’administrateur la voit dans son espace. S’il l’accepte, il vous remet votre Gmail comme identifiant et un mot de passe.
        Vous vous connecterez avec « Continuer avec un e-mail ».
      </p>
    );
  }

  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 14 }}
      onSubmit={(e) => {
        e.preventDefault();
        setError("");
        start(async () => {
          const res = await submitAccessRequest(form);
          if (!res.ok) setError(res.error);
          else setDone(true);
        });
      }}
    >
      <fieldset style={{ border: 0, padding: 0, display: "flex", gap: 16 }}>
        <legend className="muted" style={{ marginBottom: 8 }}>Vous demandez un accès</legend>
        <label><input type="radio" name="kind" checked={form.kind === "rh"} onChange={() => setForm({ ...form, kind: "rh" })} /> Service RH</label>
        <label><input type="radio" name="kind" checked={form.kind === "merchant"} onChange={() => setForm({ ...form, kind: "merchant" })} /> Commerçant</label>
      </fieldset>
      <label className="field"><span>Votre Gmail</span><input type="email" required value={form.gmail} onChange={set("gmail")} placeholder="prenom.nom@gmail.com" /></label>
      <label className="field"><span>Votre nom</span><input required value={form.full_name} onChange={set("full_name")} /></label>
      <label className="field">
        <span>{form.kind === "rh" ? "Nom du service RH" : "Nom de l’établissement"}</span>
        <input required value={form.place_name} onChange={set("place_name")} />
      </label>
      <label className="field"><span>Ville</span><input required value={form.city} onChange={set("city")} /></label>
      <label className="field"><span>Message, facultatif</span><textarea value={form.message} onChange={set("message")} rows={4} /></label>
      <input tabIndex={-1} autoComplete="off" aria-hidden value={form.website} onChange={set("website")} style={{ position: "absolute", left: -9999 }} />
      {error && <p className="error" role="alert">{error}</p>}
      <button className="btn primary" disabled={pending}>{pending ? "Envoi…" : "Envoyer à l’administrateur"}</button>
    </form>
  );
}
