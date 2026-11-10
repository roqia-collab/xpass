"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState, useTransition } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { devLogin } from "./actions";

const schema = z.object({ email: z.string().email("Adresse e-mail invalide.") });
type Values = z.infer<typeof schema>;

const DEMO_ACCOUNTS = [
  { email: "partenaire@xpass.demo", label: "Commerçant", detail: "Atelier Belle venue · Paris 11e" },
  { email: "rh@xpass.demo", label: "Entreprise (RH)", detail: "Entreprise Démo Horizon" },
  { email: "admin@xpass.demo", label: "Administration", detail: "Opérations XPASS" },
];

export function LoginForm() {
  const [serverError, setServerError] = useState<string>();
  const [pending, startTransition] = useTransition();
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  const submit = (values: Values) =>
    startTransition(async () => {
      setServerError(undefined);
      const result = await devLogin(values);
      if (result?.error) setServerError(result.error);
    });

  return (
    <form onSubmit={handleSubmit(submit)} style={{ display: "flex", flexDirection: "column", gap: 16 }} noValidate>
      <div className="field">
        <label htmlFor="email">Adresse e-mail</label>
        <input id="email" type="email" autoComplete="email" placeholder="vous@exemple.fr" {...register("email")} />
        {errors.email && <span className="error">{errors.email.message}</span>}
      </div>
      {serverError && (
        <p className="error" role="alert">
          {serverError}
        </p>
      )}
      <button className="btn primary" type="submit" disabled={pending}>
        {pending ? "Connexion…" : "Se connecter"}
      </button>
      <div className="demo-accounts" aria-label="Comptes de démonstration">
        <p className="muted" style={{ fontSize: 13 }}>
          Comptes de démonstration
        </p>
        {DEMO_ACCOUNTS.map((a) => (
          <button
            key={a.email}
            type="button"
            disabled={pending}
            onClick={() => {
              setValue("email", a.email);
              void handleSubmit(submit)();
            }}
          >
            <strong>{a.label}</strong>
            <span className="muted" style={{ display: "block", fontSize: 13 }}>
              {a.email} · {a.detail}
            </span>
          </button>
        ))}
      </div>
    </form>
  );
}
