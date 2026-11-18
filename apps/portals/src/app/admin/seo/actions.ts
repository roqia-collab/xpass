"use server";

import { revalidatePath, revalidateTag } from "next/cache";
import { z } from "zod";

import { apiFetch } from "@/lib/session";

/**
 * Décisions SEO (Server Actions : Next.js vérifie l’origine de la requête, ce qui protège du CSRF).
 * Le jeton reste côté serveur ; l’API vérifie le rôle administrateur et toutes les règles.
 */
export type SeoActionResult = { ok: true } | { ok: false; error: string };

const id = z.string().uuid();
const note = z.string().trim().max(2000);

async function post(path: string, body: unknown, publish = false): Promise<SeoActionResult> {
  try {
    await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
  revalidatePath("/admin/seo", "layout");
  if (publish) revalidateTag("seo"); // les pages publiques relisent leurs balises
  return { ok: true };
}

export async function validateRecommendation(recoId: string, rawNote: string, editedValue: string | null): Promise<SeoActionResult> {
  if (!id.safeParse(recoId).success) return { ok: false, error: "Requête invalide." };
  const n = note.safeParse(rawNote);
  if (!n.success) return { ok: false, error: "Note trop longue (2 000 caractères maximum)." };
  const value = editedValue === null ? null : z.string().trim().min(1, "La nouvelle valeur est vide.").max(20_000).safeParse(editedValue);
  if (value && !value.success) return { ok: false, error: value.error.issues[0].message };
  return post(`/admin/seo/recommendations/${recoId}/validate`, { note: n.data || null, ...(value ? { value: value.data } : {}) });
}

export async function rejectRecommendation(recoId: string, rawNote: string): Promise<SeoActionResult> {
  if (!id.safeParse(recoId).success) return { ok: false, error: "Requête invalide." };
  const n = note.min(5, "Indiquez le motif du rejet (5 caractères minimum).").safeParse(rawNote);
  if (!n.success) return { ok: false, error: n.error.issues[0].message };
  return post(`/admin/seo/recommendations/${recoId}/reject`, { note: n.data });
}

export async function applyRecommendation(recoId: string, confirmed: boolean): Promise<SeoActionResult> {
  if (!id.safeParse(recoId).success) return { ok: false, error: "Requête invalide." };
  if (confirmed !== true) return { ok: false, error: "Confirmez l’application." };
  return post(`/admin/seo/recommendations/${recoId}/apply`, { confirm: true }, true);
}

export async function revertChange(changeId: string, confirmed: boolean): Promise<SeoActionResult> {
  if (!id.safeParse(changeId).success) return { ok: false, error: "Requête invalide." };
  if (confirmed !== true) return { ok: false, error: "Confirmez l’annulation." };
  return post(`/admin/seo/changes/${changeId}/revert`, { confirm: true }, true);
}
