"use client";

import { useState, useTransition } from "react";

import { decideMerchantRequest } from "./actions";

export function OpenMerchant({ id, gmail }: { id: string; gmail: string }) {
  const [password, setPassword] = useState("");
  const [pending, start] = useTransition();
  const [error, setError] = useState("");
  const [done, setDone] = useState("");

  if (done) return <p className="notice mint">{done}</p>;

  return (
    <form
      className="request-actions"
      onSubmit={(e) => {
        e.preventDefault();
        setError("");
        start(async () => {
          const res = await decideMerchantRequest(id, "accept", password);
          if (!res.ok) setError(res.error);
          else setDone(`Compte créé. Identifiant : ${gmail}. Mot de passe : ${password}. Connexion : https://xpass.fr/login?espace=1.${res.mailed ? " Un e-mail avec l’identifiant et le mot de passe a été envoyé." : ""}`);
        });
      }}
    >
      <label className="field">
        <span>Mot de passe à remettre</span>
        <input type="text" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      </label>
      <button className="btn primary" disabled={pending}>Créer le compte</button>
      <button
        type="button"
        className="btn ghost"
        disabled={pending}
        onClick={() => {
          setError("");
          start(async () => {
            const res = await decideMerchantRequest(id, "refuse");
            if (!res.ok) setError(res.error);
            else setDone("Demande refusée.");
          });
        }}
      >
        Supprimer
      </button>
      {error && <p className="error" role="alert">{error}</p>}
    </form>
  );
}
