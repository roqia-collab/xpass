"use client";

import { useState, useTransition } from "react";

import { decideRequest } from "./actions";

export function DecideRequest({ id, gmail }: { id: string; gmail: string }) {
  const [password, setPassword] = useState("");
  const [pending, start] = useTransition();
  const [error, setError] = useState("");
  const [done, setDone] = useState("");

  if (done) return <p className="notice mint">{done}</p>;

  return (
    <form
      style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}
      onSubmit={(e) => {
        e.preventDefault();
        setError("");
        start(async () => {
          const res = await decideRequest(id, "accept", password);
          if (!res.ok) setError(res.error);
          else setDone(`Accepté. Identifiant : ${gmail}. Donnez-lui le mot de passe que vous venez de choisir.`);
        });
      }}
    >
      <label className="field" style={{ margin: 0, minWidth: 220 }}>
        <input type="text" aria-label={`Mot de passe pour ${gmail}`} autoComplete="new-password" placeholder="Mot de passe à remettre" value={password} onChange={(e) => setPassword(e.target.value)} required />
      </label>
      <button className="btn primary" disabled={pending}>Accepter</button>
      <button
        type="button"
        className="btn ghost"
        disabled={pending}
        onClick={() => {
          setError("");
          start(async () => {
            const res = await decideRequest(id, "refuse");
            if (!res.ok) setError(res.error);
            else setDone("Demande refusée.");
          });
        }}
      >
        Refuser
      </button>
      {error && <p className="error" role="alert" style={{ flexBasis: "100%" }}>{error}</p>}
    </form>
  );
}
