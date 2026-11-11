import "server-only";

import { createHash, randomBytes } from "node:crypto";

/**
 * OIDC côté serveur pour les portails : Authorization Code + PKCE avec client confidentiel.
 * Le secret du client et les jetons ne quittent jamais le serveur Next.js (cookies HttpOnly).
 */
export const OIDC = {
  issuer: process.env.OIDC_ISSUER ?? "",
  /** Adresse Keycloak vue par le navigateur (tunnel public). Vide = même que issuer. */
  browserIssuer: process.env.OIDC_ISSUER_PUBLIC || process.env.OIDC_ISSUER || "",
  clientId: process.env.OIDC_PORTALS_CLIENT_ID ?? "xpass-portals",
  clientSecret: process.env.OIDC_PORTALS_CLIENT_SECRET ?? "",
  publicUrl: process.env.PORTALS_PUBLIC_URL ?? "http://localhost:3000",
};

export const oidcConfigured = () => Boolean(OIDC.issuer && OIDC.clientSecret);
export const PENDING_COOKIE = "xpass_oidc_pending";
/** Un cookie par tentative (nommé d'après son état) : une connexion relancée n'invalide pas celle en cours. */
export const pendingCookie = (state: string) => `${PENDING_COOKIE}_${state}`;
/** 30 minutes : laisse le temps de confirmer par e-mail la liaison d'un compte Google à un compte existant. */
export const PENDING_MAX_AGE = 30 * 60;
export const isState = (s: string) => /^[A-Za-z0-9_-]{16,64}$/.test(s);
export const ID_TOKEN_COOKIE = "xpass_id_token";
/** Origines autorisées pour la connexion. La première reste l’adresse principale (commerçant). */
export function allowedOrigins(): string[] {
  const extra = (process.env.PORTALS_PUBLIC_URLS ?? "").split(",").map((s) => s.trim()).filter(Boolean);
  return [...new Set([OIDC.publicUrl, ...extra].filter(Boolean))];
}

/** Origine du site qui a reçu la requête, si elle est dans la liste. Sinon l’adresse principale. */
export function originForHost(host: string | null): string {
  const clean = (host ?? "").split(",")[0].trim().toLowerCase();
  const found = allowedOrigins().find((origin) => {
    try {
      return new URL(origin).host.toLowerCase() === clean;
    } catch {
      return false;
    }
  });
  return found ?? OIDC.publicUrl;
}

export function requestOrigin(req: { headers: { get(name: string): string | null }; nextUrl: { host: string } }): string {
  return originForHost(req.headers.get("x-forwarded-host") ?? req.headers.get("host") ?? req.nextUrl.host);
}

export const redirectUri = (origin = OIDC.publicUrl) => `${origin}/auth/callback`;

/** Cookie OIDC : Secure dès que le site public est en HTTPS (même en next dev derrière un tunnel). */
export function oidcCookieOpts(maxAge: number, origin = OIDC.publicUrl) {
  const https = origin.startsWith("https://");
  return {
    httpOnly: true,
    secure: https || process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/auth",
    maxAge,
  };
}

const b64url = (buf: Buffer) => buf.toString("base64url");

export function newPending() {
  const verifier = b64url(randomBytes(48));
  return { state: b64url(randomBytes(16)), verifier, challenge: b64url(createHash("sha256").update(verifier).digest()) };
}

/** Pages autorisées après connexion (liste fermée : pas de redirection ouverte). */
export const AFTER_LOGIN = { inscription: "/inscription-partenaire" } as const;

export function authorizeUrl(
  state: string,
  challenge: string,
  register = false,
  origin = OIDC.publicUrl,
  method: "google" | "email" = "google",
): string {
  const url = new URL(`${OIDC.browserIssuer}/protocol/openid-connect/${register ? "registrations" : "auth"}`);
  const params: Record<string, string> = {
    client_id: OIDC.clientId,
    response_type: "code",
    scope: "openid profile email",
    redirect_uri: redirectUri(origin),
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
    ui_locales: "fr",
  };
  if (method === "google") params.kc_idp_hint = "google";
  url.search = new URLSearchParams(params).toString();
  return url.toString();
}

export async function exchangeCode(code: string, verifier: string, origin = OIDC.publicUrl) {
  const res = await fetch(`${OIDC.issuer}/protocol/openid-connect/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      code,
      redirect_uri: redirectUri(origin),
      client_id: OIDC.clientId,
      client_secret: OIDC.clientSecret,
      code_verifier: verifier,
    }),
    cache: "no-store",
    signal: AbortSignal.timeout(10_000),
  });
  if (!res.ok) throw new Error("Échange du code refusé par le fournisseur d'identité.");
  return (await res.json()) as { access_token: string; expires_in: number; id_token?: string };
}

export function logoutUrl(idToken: string | undefined, origin = OIDC.publicUrl): string {
  const url = new URL(`${OIDC.browserIssuer}/protocol/openid-connect/logout`);
  url.search = new URLSearchParams({
    client_id: OIDC.clientId,
    post_logout_redirect_uri: `${origin}/login`,
    ...(idToken ? { id_token_hint: idToken } : {}),
  }).toString();
  return url.toString();
}
