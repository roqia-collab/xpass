"use client";

import { useState, useTransition } from "react";

import { loginWithPassword } from "./admin-actions";

export function PasswordLoginForm({ space }: { space: "admin" | "company" | "partner" }) {
  const [identifiant, setIdentifiant] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, start] = useTransition();

  return (
    <form
      className="login-cta"
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
      onSubmit={(e) => {
        e.preventDefault();
        setError("");
        start(async () => {
          const res = await loginWithPassword(identifiant, password, space);
          if (res && !res.ok) setError(res.error);
        });
      }}
    >
      <label className="field">
        <span>{space === "admin" ? "Identifiant" : "Adresse Gmail"}</span>
        <input autoComplete="username" value={identifiant} onChange={(e) => setIdentifiant(e.target.value)} required />
      </label>
      <label className="field">
        <span>Mot de passe</span>
        <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      </label>
      {error && <p className="login-alert" role="alert">{error}</p>}
      <button className="btn primary" disabled={pending}>{pending ? "Connexion…" : "Entrer"}</button>
    </form>
  );
}
