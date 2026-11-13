"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ID_TOKEN_COOKIE, passwordGrant } from "@/lib/oidc";
import { spacesFor } from "@/lib/roles";
import { SESSION_COOKIE, apiFetch } from "@/lib/session";
import type { Me } from "@/lib/types";

/** Connexion de l'administration : identifiant et mot de passe, sans Gmail. */
export async function loginAdmin(identifiant: string, password: string) {
  const id = identifiant.trim();
  if (id.length < 2 || password.length < 8) {
    return { ok: false as const, error: "Indiquez l’identifiant et le mot de passe." };
  }
  try {
    const tokens = await passwordGrant(id, password);
    const me = await apiFetch<Me>("/me", { token: tokens.access_token });
    if (!spacesFor(me).includes("admin")) {
      return { ok: false as const, error: "Ce compte n’a pas accès à l’administration." };
    }
    const jar = await cookies();
    const opts = {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax" as const,
      path: "/",
    };
    jar.set(SESSION_COOKIE, tokens.access_token, { ...opts, maxAge: tokens.expires_in });
    if (tokens.id_token) jar.set(ID_TOKEN_COOKIE, tokens.id_token, { ...opts, maxAge: 60 * 60 * 12 });
  } catch (e) {
    return { ok: false as const, error: e instanceof Error ? e.message : "Connexion impossible." };
  }
  redirect("/admin");
}
