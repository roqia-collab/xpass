"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { z } from "zod";

import { SESSION_COOKIE } from "@/lib/session";

function apiUrl(): string {
  return process.env.XPASS_API_URL || "https://api.xpass.fr";
}
const id = z.string().uuid();

/** Envoi d'une photo (multipart) à l'API, qui la contrôle et la réencode. Le jeton reste côté serveur. */
export async function uploadPhoto(locationId: string, offerId: string | null, form: FormData) {
  if (!id.safeParse(locationId).success || (offerId && !id.safeParse(offerId).success)) {
    return { ok: false as const, error: "Requête invalide." };
  }
  const file = form.get("file");
  if (!(file instanceof File) || file.size === 0) return { ok: false as const, error: "Choisissez une photo." };
  if (file.size > 8 * 1024 * 1024) return { ok: false as const, error: "Photo trop lourde (8 Mo maximum)." };
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  const body = new FormData();
  body.set("file", file, file.name);
  const path = offerId
    ? `/partner/locations/${locationId}/offers/${offerId}/image`
    : `/partner/locations/${locationId}/cover`;
  try {
    const res = await fetch(`${apiUrl()}/api/v1${path}`, {
      method: "POST",
      body,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: "no-store",
      signal: AbortSignal.timeout(30_000),
    });
    if (!res.ok) {
      const err = (await res.json().catch(() => null)) as { detail?: { message?: string } } | null;
      return { ok: false as const, error: err?.detail?.message ?? `Erreur API (${res.status}).` };
    }
    revalidatePath("/partner", "layout");
    return { ok: true as const };
  } catch {
    return { ok: false as const, error: "L'API XPASS est injoignable." };
  }
}
