import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";

import { canAccess } from "./roles";
import type { Me, Space } from "./types";

export const SESSION_COOKIE = "xpass_session";
const API_URL = process.env.XPASS_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** Appel serveur → API FastAPI avec le jeton de la session (jamais exposé au navigateur). */
export async function apiFetch<T>(path: string, init?: RequestInit & { token?: string }): Promise<T> {
  const token = init?.token ?? (await cookies()).get(SESSION_COOKIE)?.value;
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    throw new ApiError(503, "L'API XPASS est injoignable. Vérifiez que le backend est démarré.");
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: { message?: string } } | null;
    throw new ApiError(res.status, body?.detail?.message ?? `Erreur API (${res.status}).`);
  }
  return (await res.json()) as T;
}

/** Variante brute (fichiers : CSV...). Même authentification que `apiFetch`. */
export async function apiFetchRaw(path: string): Promise<Response> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  try {
    return await fetch(`${API_URL}/api/v1${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    throw new ApiError(503, "L'API XPASS est injoignable.");
  }
}

/** Utilisateur courant, mémorisé pour la durée de la requête. */
export const getMe = cache(async (): Promise<Me | null> => {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return null;
  try {
    return await apiFetch<Me>("/me", { token });
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return null;
    throw e;
  }
});

/** Garde d'espace : redirige vers la connexion ou refuse l'accès. */
export async function requireSpace(space: Space): Promise<Me> {
  const me = await getMe();
  if (!me) redirect("/login");
  if (!canAccess(me, space)) redirect("/login?error=forbidden");
  return me;
}

export const mediaUrl = (key: string | null) =>
  key ? `${process.env.NEXT_PUBLIC_MEDIA_BASE_URL ?? "http://localhost:8333/xpass-public"}/${key}` : null;

/** Application client (Flutter). Même API que les portails. */
export const clientAppUrl = () => process.env.APP_PUBLIC_URL ?? "http://localhost:5174";

/** Adresse de chaque espace. En production, admin, RH et commerçant ont chacun leur site. */
export function spaceHrefs(): Record<"admin" | "company" | "partner", string> {
  const dedicated = Boolean(process.env.ADMIN_PUBLIC_URL);
  const base = {
    admin: process.env.ADMIN_PUBLIC_URL,
    company: process.env.RH_PUBLIC_URL,
    partner: process.env.PORTALS_PUBLIC_URL,
  };
  const path = { admin: "/admin", company: "/company", partner: "/partner" } as const;
  return {
    admin: dedicated && base.admin ? `${base.admin}${path.admin}` : path.admin,
    company: dedicated && base.company ? `${base.company}${path.company}` : path.company,
    partner: dedicated && base.partner ? `${base.partner}${path.partner}` : path.partner,
  };
}
