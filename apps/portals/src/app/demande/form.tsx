"use client";

import { useState, useTransition } from "react";

import { ACTIVITIES, activityName } from "@/lib/activities";

import { submitAccessRequest } from "./actions";

const empty = { kind: "rh" as "rh" | "merchant", activity: "", gmail: "", full_name: "", place_name: "", city: "Paris", message: "", website: "" };

export function AccessForm({ activity, kind = "rh" }: { activity?: string; kind?: "rh" | "merchant" }) {
  const [form, setForm] = useState({ ...empty, activity: activityName(activity), kind });
  const [pending, start] = useTransition();
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const set = (key: keyof typeof empty) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm({ ...form, [key]: e.target.value });

  if (done) {
    return (
      <div className="notice mint stack" role="status">
        <p>Demande envoyée pour <strong>{form.activity}</strong>.</p>
        <p>L’administrateur la voit dans son espace. S’il valide, l’identifiant et le mot de passe sont envoyés à {form.gmail}.</p>
        <a className="btn outline" href="/">Retour</a>
      </div>
    );
  }

  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 14 }}
      onSubmit={(e) => {
        e.preventDefault();
        if (!form.activity) {
          setError("Choisissez une activité.");
          return;
        }
        setError("");
        start(async () => {
          const message = [`Activité : ${form.activity}`, form.message].filter(Boolean).join("\n");
          const res = await submitAccessRequest({ ...form, message });
          if (!res.ok) setError(res.error);
          else setDone(true);
        });
      }}
    >
      <fieldset className="kind-choice">
        <legend className="muted" style={{ marginBottom: 8 }}>Vous demandez un accès</legend>
        <label><input type="radio" name="kind" checked={form.kind === "rh"} onChange={() => setForm({ ...form, kind: "rh" })} /> Service RH</label>
        <label><input type="radio" name="kind" checked={form.kind === "merchant"} onChange={() => setForm({ ...form, kind: "merchant" })} /> Commerçant</label>
      </fieldset>
      <label className="field">
        <span>Activité choisie</span>
        <select required value={form.activity} onChange={set("activity")}>
          <option value="">Choisir…</option>
          {ACTIVITIES.map((item) => <option key={item.slug} value={item.name}>{item.name}</option>)}
        </select>
      </label>
      {form.activity && <p className="notice mint" role="status">Activité retenue : <strong>{form.activity}</strong>. Elle sera envoyée avec la demande.</p>}
      <label className="field"><span>Adresse Gmail</span><input type="email" required value={form.gmail} onChange={set("gmail")} placeholder="prenom.nom@gmail.com" /></label>
      <label className="field"><span>Votre nom</span><input required value={form.full_name} onChange={set("full_name")} /></label>
      <label className="field">
        <span>{form.kind === "rh" ? "Nom du service RH" : "Nom de l’établissement"}</span>
        <input required value={form.place_name} onChange={set("place_name")} />
      </label>
      <label className="field"><span>Ville</span><input required value={form.city} onChange={set("city")} /></label>
      <label className="field"><span>Message, facultatif</span><textarea value={form.message} onChange={set("message")} rows={4} /></label>
      <input tabIndex={-1} autoComplete="off" aria-hidden value={form.website} onChange={set("website")} style={{ position: "absolute", left: -9999 }} />
      <p className="notice" role="status">
        Récapitulatif : {form.activity || "activité non choisie"} · {form.kind === "rh" ? "Service RH" : "Commerçant"} · {form.full_name || "nom"} · {form.place_name || "établissement"} · {form.city || "ville"} · {form.gmail || "Gmail"}
      </p>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="btn primary" disabled={pending}>{pending ? "Envoi…" : "Envoyer à l’administrateur"}</button>
    </form>
  );
}
