"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ID_TOKEN_COOKIE, passwordGrant } from "@/lib/oidc";
import { spacesFor } from "@/lib/roles";
import { SESSION_COOKIE, apiFetch } from "@/lib/session";
import type { Me } from "@/lib/types";

const HOME = { admin: "/admin", company: "/company", partner: "/partner" } as const;

/** Connexion par identifiant et mot de passe, puis ouverture de l'espace correspondant. */
export async function loginWithPassword(identifiant: string, password: string, space: keyof typeof HOME) {
  const id = identifiant.trim();
  const key = id.toLowerCase();
  const username = space === "admin" && (key === "admin" || key === "support@xpass.fr") ? "admin@xpass.fr" : key;
  if (id.length < 2 || password.length < 8) {
    return { ok: false as const, error: "Indiquez l’identifiant et le mot de passe." };
  }
  try {
    const tokens = await passwordGrant(username, password);
    const me = await apiFetch<Me>("/me", { token: tokens.access_token });
    const spaces = spacesFor(me);
    if (!spaces.includes(space)) {
      const where = spaces.includes("company")
        ? "Cet identifiant ouvre l’espace RH : https://rh.xpass.fr"
        : spaces.includes("partner")
          ? "Cet identifiant ouvre l’espace commerçant : https://xpass.fr/login?espace=1"
          : spaces.includes("admin")
            ? "Cet identifiant ouvre l’administration : https://admin.xpass.fr"
            : "Ce compte n’a pas accès à cet espace.";
      return { ok: false as const, error: where };
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
    const message = e instanceof Error ? e.message : "";
    if (/fetch failed|ECONN|ENOTFOUND|timeout/i.test(message)) {
      return { ok: false as const, error: "Le serveur d’identité ne répond pas. Réessayez." };
    }
    return { ok: false as const, error: message || "Connexion impossible." };
  }
  redirect(HOME[space]);
}
