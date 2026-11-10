"use server";

import { z } from "zod";

import { ApiError, apiFetch } from "@/lib/session";

import { getCurrentLocation } from "../data";

// Le contenu du QR ne transite jamais par l'URL : il reste dans le corps des Server Actions
// (protégées contre le CSRF par la vérification d'origine de Next.js).
const input = z
  .object({
    qr: z.string().max(200).optional(),
    code: z
      .string()
      .max(20)
      .regex(/^[A-Za-z0-9-\s]+$/, "Code invalide.")
      .optional(),
  })
  .refine((v) => Boolean(v.qr) !== Boolean(v.code), "Fournir un QR ou un code.");

export type ScanPreview = {
  booking_id: string;
  customer_name: string;
  location_name: string;
  kind_label: string;
  district_label: string;
  cover_image_key: string | null;
  offer_title: string;
  resource_name: string | null;
  local_start: string;
  duration_min: number;
  party_size: number;
  total_credits: number;
  confirm_before: string;
};

export type Redemption = {
  booking_id: string;
  receipt_reference: string;
  credits: number;
  redeemed_at: string;
  customer_name: string;
  offer_title: string;
};

type Result<T> = { ok: true; data: T } | { ok: false; error: string; code?: string };

async function call<T>(path: string, body: unknown, headers?: Record<string, string>): Promise<Result<T>> {
  const location = await getCurrentLocation();
  if (!location) return { ok: false, error: "Aucun établissement rattaché à ce compte." };
  try {
    const data = await apiFetch<T>(path, {
      method: "POST",
      body: JSON.stringify({ location_id: location.id, ...(body as object) }),
      headers,
    });
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue.", code: e instanceof ApiError ? String(e.status) : undefined };
  }
}

/** Aperçu sans effet financier. */
export async function previewScan(raw: { qr?: string; code?: string }): Promise<Result<ScanPreview>> {
  const parsed = input.safeParse(raw);
  if (!parsed.success) return { ok: false, error: parsed.error.issues[0]?.message ?? "Saisie invalide." };
  return call<ScanPreview>("/partner/scan/preview", parsed.data);
}

/** Consommation : une seule par réservation ; la clé rend un réessai réseau sans risque. */
export async function confirmRedemption(raw: { qr?: string; code?: string }, idempotencyKey: string): Promise<Result<Redemption>> {
  const parsed = input.safeParse(raw);
  if (!parsed.success) return { ok: false, error: parsed.error.issues[0]?.message ?? "Saisie invalide." };
  if (!/^[a-f0-9-]{16,64}$/.test(idempotencyKey)) return { ok: false, error: "Requête invalide." };
  return call<Redemption>("/partner/redemptions", parsed.data, { "Idempotency-Key": idempotencyKey });
}
