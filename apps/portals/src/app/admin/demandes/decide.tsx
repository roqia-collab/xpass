"use client";

import { useState, useTransition } from "react";

import { setStaffPassword } from "../actions";
import { decideRequest } from "./actions";

const DOOR = {
  rh: "https://rh.xpass.fr",
  merchant: "https://xpass.fr/login?espace=1",
} as const;

export function DecideRequest({ id, gmail, kind }: { id: string; gmail: string; kind: "rh" | "merchant" }) {
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
          else setDone(`Accepté. Identifiant : ${gmail}. Mot de passe : ${password}. Connexion : ${DOOR[kind]}`);
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

/** Une demande déjà acceptée : le mot de passe peut être réenregistré, il s'affiche ensuite. */
export function ResetAccessPassword({ gmail, kind }: { gmail: string; kind: "rh" | "merchant" }) {
  const [password, setPassword] = useState("");
  const [pending, start] = useTransition();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  return (
    <form
      style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}
      onSubmit={(e) => {
        e.preventDefault();
        setError("");
        start(async () => {
          const res = await setStaffPassword(gmail, password);
          if (!res.ok) {
            setMessage("");
            setError(res.error);
            return;
          }
          setMessage(`Mot de passe enregistré. Identifiant : ${gmail}. Mot de passe : ${password}. Connexion : ${DOOR[kind]}`);
        });
      }}
    >
      <input type="text" aria-label={`Nouveau mot de passe pour ${gmail}`} autoComplete="new-password" placeholder="Nouveau mot de passe" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
      <button className="btn outline" disabled={pending}>Enregistrer le mot de passe</button>
      {message && <p className="notice mint" style={{ flexBasis: "100%", margin: 0 }}>{message}</p>}
      {error && <p className="error" role="alert" style={{ flexBasis: "100%", margin: 0 }}>{error}</p>}
    </form>
  );
}
