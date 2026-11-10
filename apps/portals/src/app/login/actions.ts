"use server";

import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { z } from "zod";

import { ID_TOKEN_COOKIE, logoutUrl, oidcConfigured, originForHost } from "@/lib/oidc";
import { spacesFor } from "@/lib/roles";
import { ApiError, SESSION_COOKIE, apiFetch } from "@/lib/session";
import type { Me } from "@/lib/types";

const loginSchema = z.object({ email: z.string().email("Adresse e-mail invalide.") });

export type LoginState = { error?: string };

/**
 * Connexion de DÉMONSTRATION : l'API n'accepte que les comptes `is_demo` et seulement
 * hors production. La connexion réelle passe par OIDC (/auth/login).
 * Les Server Actions vérifient l'origine de la requête (protection CSRF intégrée à Next.js).
 */
export async function devLogin(input: { email: string }): Promise<LoginState> {
  const parsed = loginSchema.safeParse(input);
  if (!parsed.success) return { error: parsed.error.issues[0]?.message };

  let token: string;
  let expiresIn: number;
  try {
    const res = await apiFetch<{ access_token: string; expires_in: number }>("/auth/dev/login", {
      method: "POST",
      body: JSON.stringify({ email: parsed.data.email }),
      token: "",
    });
    token = res.access_token;
    expiresIn = res.expires_in;
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return { error: "La connexion de démonstration est désactivée." };
    return { error: e instanceof Error ? e.message : "Connexion impossible." };
  }

  const me = await apiFetch<Me>("/me", { token });
  const spaces = spacesFor(me);
  if (spaces.length === 0) return { error: "Ce compte n'a accès à aucun portail." };

  (await cookies()).set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: expiresIn,
  });
  redirect("/");
}

export async function logout(): Promise<void> {
  const jar = await cookies();
  const idToken = jar.get(ID_TOKEN_COOKIE)?.value;
  jar.delete(SESSION_COOKIE);
  jar.delete(ID_TOKEN_COOKIE);
  // Session OIDC : fermeture aussi chez le fournisseur d'identité.
  const h = await headers();
  const host = h.get("x-forwarded-host") ?? h.get("host");
  redirect(idToken && oidcConfigured() ? logoutUrl(idToken, originForHost(host)) : "/login");
}
