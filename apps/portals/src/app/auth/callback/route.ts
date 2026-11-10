import { NextResponse, type NextRequest } from "next/server";

import {
  AFTER_LOGIN,
  ID_TOKEN_COOKIE,
  PENDING_COOKIE,
  exchangeCode,
  isState,
  oidcCookieOpts,
  pendingCookie,
  requestOrigin,
} from "@/lib/oidc";
import { spacesFor } from "@/lib/roles";
import { SESSION_COOKIE, apiFetch } from "@/lib/session";
import type { Me } from "@/lib/types";

/** Retour du fournisseur : vérifie l'état, échange le code (secret côté serveur) et ouvre la session. */
export async function GET(req: NextRequest) {
  const origin = requestOrigin(req);
  const state = req.nextUrl.searchParams.get("state");
  const code = req.nextUrl.searchParams.get("code");
  const cookieName = state && isState(state) ? pendingCookie(state) : PENDING_COOKIE;
  const fail = (reason: string) => {
    const res = NextResponse.redirect(new URL(`/login?erreur=${reason}`, origin));
    res.cookies.delete({ name: cookieName, path: "/auth" });
    return res;
  };
  if (!state || !code) return fail("annule");
  const raw = req.cookies.get(cookieName)?.value;
  // Code reçu mais plus de connexion en attente (lien trop ancien, autre navigateur, ou cookie posé sur localhost) : à recommencer.
  if (!raw) return fail("etat");
  let pending: { state: string; verifier: string; next?: string };
  try {
    pending = JSON.parse(raw);
  } catch {
    return fail("etat");
  }
  if (pending.state !== state) return fail("etat");

  let tokens: Awaited<ReturnType<typeof exchangeCode>>;
  let me: Me;
  try {
    tokens = await exchangeCode(code, pending.verifier, origin);
  } catch (err) {
    console.error("[auth/callback] échange code Keycloak échoué", err);
    return fail("refus");
  }
  try {
    me = await apiFetch<Me>("/me", { token: tokens.access_token });
  } catch (err) {
    console.error("[auth/callback] /me refusé", err);
    return fail("refus");
  }
  const spaces = spacesFor(me);
  // Google (ou toute connexion) sans espace pro : ouvrir le dossier commerçant, pas une page d'erreur.
  const signup = pending.next === AFTER_LOGIN.inscription || spaces.length === 0;
  const target = signup && !spaces.includes("partner") ? AFTER_LOGIN.inscription : "/";

  const res = NextResponse.redirect(new URL(target, origin));
  const https = origin.startsWith("https://");
  const opts = {
    httpOnly: true,
    secure: https || process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
  };
  res.cookies.set(SESSION_COOKIE, tokens.access_token, { ...opts, maxAge: tokens.expires_in });
  if (tokens.id_token) res.cookies.set(ID_TOKEN_COOKIE, tokens.id_token, { ...opts, maxAge: 60 * 60 * 12 });
  // Connexion ouverte : les autres tentatives en attente ne servent plus.
  const clear = oidcCookieOpts(0);
  for (const c of req.cookies.getAll()) {
    if (c.name.startsWith(PENDING_COOKIE)) res.cookies.delete({ name: c.name, path: clear.path });
  }
  return res;
}
