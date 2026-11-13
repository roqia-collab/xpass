import { NextResponse, type NextRequest } from "next/server";

import {
  AFTER_LOGIN,
  OIDC,
  PENDING_MAX_AGE,
  authorizeUrl,
  oidcConfigured,
  oidcCookieOpts,
  pendingCookie,
  newPending,
  requestOrigin,
} from "@/lib/oidc";

/** Démarre la connexion OIDC : état + vérificateur PKCE dans un cookie HttpOnly propre à cette tentative. */
export async function GET(req: NextRequest) {
  if (!oidcConfigured()) {
    return NextResponse.redirect(new URL("/login?erreur=oidc", requestOrigin(req)));
  }

  // Le cookie PKCE doit être posé sur la même origine que /auth/callback (tunnel HTTPS).
  // Sinon : connexion depuis localhost → retour sur le tunnel → « état » invalide.
  // Derrière Caddy, Host = tunnel mais nextUrl.protocol peut rester http → on compare seulement le host.
  const origin = requestOrigin(req);
  const publicHost = new URL(origin).host;
  const requestHost = (req.headers.get("x-forwarded-host") ?? req.headers.get("host") ?? req.nextUrl.host)
    .split(",")[0]
    .trim()
    .toLowerCase();
  if (requestHost !== publicHost.toLowerCase()) {
    const target = new URL(req.nextUrl.pathname + req.nextUrl.search, OIDC.publicUrl);
    return NextResponse.redirect(target);
  }

  const p = newPending();
  const suite = req.nextUrl.searchParams.get("suite");
  const next =
    suite === "inscription" ? AFTER_LOGIN.inscription
    : suite === "espace" ? AFTER_LOGIN.espace
    : suite === "admin" ? AFTER_LOGIN.admin
    : suite === "rh" ? AFTER_LOGIN.rh
    : undefined;
  const register = req.nextUrl.searchParams.get("creer") === "1";
  const method = req.nextUrl.searchParams.get("methode") === "email" ? "email" : "google";
  const res = NextResponse.redirect(authorizeUrl(p.state, p.challenge, register, origin, method));
  res.cookies.set(
    pendingCookie(p.state),
    JSON.stringify({ state: p.state, verifier: p.verifier, next }),
    oidcCookieOpts(PENDING_MAX_AGE, origin),
  );
  return res;
}
