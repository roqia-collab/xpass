"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { apiFetch } from "@/lib/session";

/**
 * Mutations du portail commerçant (Server Actions : origine vérifiée par Next.js, jeton jamais exposé).
 * Les droits et toutes les règles métier sont contrôlés par l'API ; ici, seulement la forme des données.
 */
export type ActionResult = { ok: true; bookingsOutsideHours: number } | { ok: false; error: string };

const id = z.string().uuid();
const hhmm = z.string().regex(/^\d{2}:\d{2}$/);

async function call(path: string, method: string, body?: unknown): Promise<ActionResult> {
  try {
    const res = await apiFetch<{ bookings_outside_hours?: number }>(path, {
      method,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    revalidatePath("/partner", "layout");
    return { ok: true, bookingsOutsideHours: res.bookings_outside_hours ?? 0 };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}

function invalid(error: z.ZodError): ActionResult {
  return { ok: false, error: error.issues[0]?.message ?? "Saisie invalide." };
}

const offerSchema = z.object({
  title: z.string().trim().min(2, "Nom trop court.").max(120),
  summary: z.string().max(240),
  duration_min: z.coerce.number().int().min(15).max(480),
  price_credits: z.coerce.number().int().min(1, "Prix en crédits requis.").max(10000),
  participants_min: z.coerce.number().int().min(1).max(50),
  participants_max: z.coerce.number().int().min(1).max(50),
  capacity: z.coerce.number().int().min(1).max(500).nullable(),
  free_cancellation_hours: z.coerce.number().int().min(0).max(168),
  resource_ids: z.array(id),
});

export async function saveOffer(
  locationId: string,
  offerId: string | null,
  raw: unknown,
  create?: { booking_mode: string; publish: boolean },
): Promise<ActionResult> {
  const parsed = offerSchema.safeParse(raw);
  if (!parsed.success) return invalid(parsed.error);
  if (!id.safeParse(locationId).success) return { ok: false, error: "Établissement invalide." };
  const base = `/partner/locations/${locationId}`;
  if (offerId === null) {
    const mode = z.enum(["resource_slot", "capacity_session", "open_access"]).safeParse(create?.booking_mode);
    if (!mode.success) return { ok: false, error: "Mode de réservation invalide." };
    return call(`${base}/offers`, "POST", { ...parsed.data, booking_mode: mode.data, publish: Boolean(create?.publish) });
  }
  if (!id.safeParse(offerId).success) return { ok: false, error: "Prestation invalide." };
  return call(`${base}/offers/${offerId}`, "PUT", parsed.data);
}

export async function setOfferActive(locationId: string, offerId: string, active: boolean) {
  if (!id.safeParse(locationId).success || !id.safeParse(offerId).success) return { ok: false, error: "Requête invalide." } as const;
  return call(`/partner/locations/${locationId}/offers/${offerId}/active`, "POST", { active });
}

const resourceSchema = z.object({
  kind: z.enum(["staff", "equipment", "room"]),
  name: z.string().trim().min(1, "Nom requis.").max(80),
  role_label: z.string().trim().min(1, "Rôle requis.").max(80),
});

export async function createResource(locationId: string, raw: unknown) {
  const parsed = resourceSchema.safeParse(raw);
  if (!parsed.success) return invalid(parsed.error);
  return call(`/partner/locations/${locationId}/resources`, "POST", parsed.data);
}

export async function updateResource(locationId: string, resourceId: string, raw: unknown) {
  const parsed = resourceSchema.omit({ kind: true }).extend({ active: z.boolean() }).safeParse(raw);
  if (!parsed.success) return invalid(parsed.error);
  if (!id.safeParse(resourceId).success) return { ok: false, error: "Ressource invalide." } as const;
  return call(`/partner/locations/${locationId}/resources/${resourceId}`, "PUT", parsed.data);
}

export async function saveHours(locationId: string, raw: unknown) {
  const parsed = z.array(z.object({ weekday: z.number().int().min(0).max(6), opens_at: hhmm, closes_at: hhmm })).safeParse(raw);
  if (!parsed.success) return invalid(parsed.error);
  return call(`/partner/locations/${locationId}/hours`, "PUT", parsed.data);
}

export async function addException(locationId: string, raw: unknown) {
  const parsed = z
    .object({
      day: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Date requise."),
      is_closed: z.boolean(),
      opens_at: hhmm.nullable(),
      closes_at: hhmm.nullable(),
      reason: z.string().max(160).nullable(),
    })
    .safeParse(raw);
  if (!parsed.success) return invalid(parsed.error);
  return call(`/partner/locations/${locationId}/exceptions`, "POST", parsed.data);
}

export async function deleteException(locationId: string, exceptionId: string) {
  if (!id.safeParse(exceptionId).success) return { ok: false, error: "Requête invalide." } as const;
  return call(`/partner/locations/${locationId}/exceptions/${exceptionId}`, "DELETE");
}

export async function updateLocation(locationId: string, raw: unknown) {
  const parsed = z
    .object({
      description: z.string().max(2000),
      access_info: z.string().max(240).nullable(),
      meeting_point: z.string().max(240).nullable(),
      wheelchair_accessible: z.boolean(),
      review_url: z.string().max(500).nullable(),
    })
    .safeParse(raw);
  if (!parsed.success) return invalid(parsed.error);
  return call(`/partner/locations/${locationId}`, "PATCH", parsed.data);
}

export async function createBlock(locationId: string, raw: unknown) {
  const parsed = z
    .object({
      resource_id: id,
      local_start: z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/, "Début requis."),
      local_end: z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/, "Fin requise."),
      reason: z.string().trim().min(2, "Motif requis.").max(160),
    })
    .safeParse(raw);
  if (!parsed.success) return invalid(parsed.error);
  return call(`/partner/locations/${locationId}/blocks`, "POST", parsed.data);
}

export async function deleteBlock(locationId: string, blockId: string) {
  if (!id.safeParse(blockId).success) return { ok: false, error: "Requête invalide." } as const;
  return call(`/partner/locations/${locationId}/blocks/${blockId}`, "DELETE");
}
