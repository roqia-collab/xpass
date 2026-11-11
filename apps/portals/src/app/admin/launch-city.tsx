"use client";

import { useState, useTransition } from "react";

import { openCity } from "./actions";

/** Une autre ville reste fermée tant que Paris n'est pas un vrai réseau. */
export function OpenCityForm({ allowed }: { allowed: boolean }) {
  const [pending, start] = useTransition();
  const [slug, setSlug] = useState("");
  const [reason, setReason] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        setMsg(undefined);
        start(async () => {
          const res = await openCity(slug, reason);
          setMsg(res.ok
            ? { ok: true, text: "Ville ouverte. Elle apparaît maintenant dans l’application." }
            : { ok: false, text: res.error });
        });
      }}
      style={{ display: "flex", flexDirection: "column", gap: 8 }}
    >
      <h3>Ouvrir une autre ville</h3>
      <p className="muted" style={{ fontSize: 14 }}>
        {allowed
          ? "Paris a démarré. Vous pouvez ouvrir la ville suivante."
          : "Pas encore. Une entreprise doit avoir payé, Stripe doit être en mode réel, et un commerçant doit avoir un compte de versement."}
      </p>
      <label className="field"><span>Identifiant de la ville</span><input value={slug} placeholder="lyon" onChange={(e) => setSlug(e.target.value)} required /></label>
      <label className="field"><span>Motif</span><input value={reason} onChange={(e) => setReason(e.target.value)} required /></label>
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
      <button className="btn outline" disabled={pending}>Ouvrir</button>
    </form>
  );
}
