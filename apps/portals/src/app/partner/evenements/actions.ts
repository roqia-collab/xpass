"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { z } from "zod";

import { SESSION_COOKIE, apiFetch } from "@/lib/session";

type Result<T = null> = { ok: true; data: T } | { ok: false; error: string };

async function call<T>(path: string, method: string, body?: unknown): Promise<Result<T>> {
  try {
    const data = await apiFetch<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
    revalidatePath("/partner/evenements");
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}

const eventSchema = z.object({
  location_id: z.string().uuid(),
  title: z.string().trim().min(2).max(120),
  summary: z.string().trim().max(500),
  starts_at: z.string().min(16),
  ends_at: z.string().min(16),
  price_credits: z.number().int().min(1).max(500),
});

export async function savePartnerEvent(id: string | null, raw: unknown): Promise<{ ok: true; id: string } | { ok: false; error: string }> {
  const parsed = eventSchema.safeParse(raw);
  if (!parsed.success) return { ok: false, error: "Vérifiez le titre, les horaires et le prix en crédits." };
  const res = await call<{ id: string }>(id ? `/partner/events/${id}` : "/partner/events", id ? "PATCH" : "POST", parsed.data);
  return res.ok ? { ok: true, id: res.data.id } : res;
}

export async function setPartnerEventVisible(id: string, published: boolean): Promise<{ ok: true } | { ok: false; error: string }> {
  if (!z.string().uuid().safeParse(id).success) return { ok: false, error: "Requête invalide." };
  const res = await call(`/partner/events/${id}/visibility`, "POST", { published });
  return res.ok ? { ok: true } : res;
}

export async function uploadPartnerEventPhoto(id: string, file: File): Promise<{ ok: true } | { ok: false; error: string }> {
  if (!z.string().uuid().safeParse(id).success) return { ok: false, error: "Requête invalide." };
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return { ok: false, error: "Session expirée." };
  const body = new FormData();
  body.set("file", file, file.name);
  const res = await fetch(`https://api.xpass.fr/api/v1/partner/events/${id}/cover`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body,
    cache: "no-store",
  });
  revalidatePath("/partner/evenements");
  if (!res.ok) return { ok: false, error: "La photo n’a pas été enregistrée. L’événement est quand même publié." };
  return { ok: true };
}
