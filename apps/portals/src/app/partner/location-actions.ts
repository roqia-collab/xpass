"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { z } from "zod";

import { apiFetch } from "@/lib/session";

import { LOCATION_COOKIE } from "./data";

const id = z.string().uuid();

async function remember(locationId: string) {
  (await cookies()).set(LOCATION_COOKIE, locationId, {
    httpOnly: true, sameSite: "lax", path: "/", secure: process.env.NODE_ENV === "production", maxAge: 60 * 60 * 24 * 365,
  });
}

export async function selectLocation(locationId: string) {
  if (!id.safeParse(locationId).success) return;
  await remember(locationId);
  revalidatePath("/partner", "layout");
}

const locationSchema = z.object({
  location_name: z.string().trim().min(2, "Nom de l’établissement trop court.").max(120),
  subcategory_slug: z.string().min(2, "Choisissez l’activité."),
  kind_label: z.string().trim().max(80),
  address_line: z.string().trim().min(3, "Indiquez le numéro et la rue.").max(200),
  postal_code: z.string().trim().regex(/^\d{5}$/, "Code postal à 5 chiffres."),
  city: z.string().trim().min(2, "Indiquez la commune.").max(80),
  description: z.string().trim().max(2000),
});

export async function addLocation(currentLocationId: string, raw: unknown) {
  if (!id.safeParse(currentLocationId).success) return { ok: false as const, error: "Requête invalide." };
  const parsed = locationSchema.safeParse(raw);
  if (!parsed.success) return { ok: false as const, error: parsed.error.issues[0]?.message ?? "Saisie invalide." };
  try {
    const r = await apiFetch<{ id: string; address_label: string }>(`/partner/locations/${currentLocationId}/siblings`, {
      method: "POST", body: JSON.stringify(parsed.data),
    });
    await remember(r.id);
    revalidatePath("/partner", "layout");
    return { ok: true as const, address: r.address_label };
  } catch (e) {
    return { ok: false as const, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}

const changeSchema = z.object({
  name: z.string().trim().max(120),
  subcategory_slug: z.string().max(32),
  kind_label: z.string().trim().max(80),
  address_line: z.string().trim().max(200),
  postal_code: z.string().trim().regex(/^(\d{5})?$/, "Code postal à 5 chiffres."),
  city: z.string().trim().max(80),
});

export async function requestChange(locationId: string, raw: unknown) {
  if (!id.safeParse(locationId).success) return { ok: false as const, error: "Requête invalide." };
  const parsed = changeSchema.safeParse(raw);
  if (!parsed.success) return { ok: false as const, error: parsed.error.issues[0]?.message ?? "Saisie invalide." };
  try {
    await apiFetch(`/partner/locations/${locationId}/change-requests`, { method: "POST", body: JSON.stringify(parsed.data) });
    revalidatePath("/partner/etablissement");
    return { ok: true as const };
  } catch (e) {
    return { ok: false as const, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}
