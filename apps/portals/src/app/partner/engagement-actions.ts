"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { apiFetch } from "@/lib/session";

const id = z.string().uuid();

async function post(path: string, body: unknown, revalidate: string) {
  try {
    await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
    revalidatePath(revalidate);
    return { ok: true as const };
  } catch (e) {
    return { ok: false as const, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}

export async function sendPartnerMessage(locationId: string, conversationId: string, body: string) {
  if (!id.safeParse(locationId).success || !id.safeParse(conversationId).success) return { ok: false as const, error: "Requête invalide." };
  const text = body.trim();
  if (!text || text.length > 2000) return { ok: false as const, error: "Message vide ou trop long (2 000 caractères maximum)." };
  return post(`/partner/locations/${locationId}/conversations/${conversationId}/messages`, { body: text }, "/partner/messages");
}

export async function replyToReview(locationId: string, reviewId: string, reply: string) {
  if (!id.safeParse(locationId).success || !id.safeParse(reviewId).success) return { ok: false as const, error: "Requête invalide." };
  const text = reply.trim();
  if (text.length < 2 || text.length > 1000) return { ok: false as const, error: "Réponse de 2 à 1 000 caractères." };
  return post(`/partner/locations/${locationId}/reviews/${reviewId}/reply`, { reply: text }, "/partner/avis");
}
