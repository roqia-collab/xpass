"use client";

import { useState, useTransition } from "react";

import { loginAdmin } from "./admin-actions";

export function AdminLoginForm() {
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
          const res = await loginAdmin(identifiant, password);
          if (res && !res.ok) setError(res.error);
        });
      }}
    >
      <label className="field">
        <span>Identifiant</span>
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
