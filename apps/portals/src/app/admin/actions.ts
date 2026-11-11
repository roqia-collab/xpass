"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { z } from "zod";

import { apiFetch, SESSION_COOKIE } from "@/lib/session";

/** Décisions d'administration (Server Actions). Motif obligatoire, droits et règles contrôlés par l'API. */
export type ActionResult = { ok: true } | { ok: false; error: string };

const uuid = z.string().uuid();
const reason = z.string().trim().min(5, "Indiquez le motif de la décision (5 caractères minimum).").max(2000);

async function call(path: string, body: unknown): Promise<ActionResult> {
  try {
    await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
    revalidatePath("/admin", "layout");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}

function check(id: string, why: string): string | null {
  if (!uuid.safeParse(id).success) return "Requête invalide.";
  const r = reason.safeParse(why);
  return r.success ? null : r.error.issues[0].message;
}

export async function merchantDecision(id: string, decision: "approve" | "request_documents" | "suspend" | "reopen", why: string) {
  const err = check(id, why);
  if (err) return { ok: false, error: err } as const;
  return call(`/admin/merchants/${id}/decision`, { decision, reason: why });
}

export async function pspSandboxVerify(id: string, why: string) {
  const err = check(id, why);
  if (err) return { ok: false, error: err } as const;
  return call(`/admin/merchants/${id}/psp-sandbox-verify`, { reason: why });
}

export async function moderateLocation(id: string, publish: boolean, why: string) {
  const err = check(id, why);
  if (err) return { ok: false, error: err } as const;
  return call(`/admin/locations/${id}/moderation`, { publish, reason: why });
}

export async function updateDispute(id: string, status: "open" | "in_review" | "waiting_customer", notes: string, why: string) {
  const err = check(id, why);
  if (err) return { ok: false, error: err } as const;
  return call(`/admin/disputes/${id}/update`, { status, notes, reason: why });
}

export async function refundDispute(id: string, partnerAdjustmentMinor: number, why: string) {
  const err = check(id, why);
  if (err) return { ok: false, error: err } as const;
  if (!Number.isInteger(partnerAdjustmentMinor) || partnerAdjustmentMinor < 0) return { ok: false, error: "Montant invalide." } as const;
  return call(`/admin/disputes/${id}/refund`, { partner_adjustment_minor: partnerAdjustmentMinor, reason: why });
}

export async function rejectDispute(id: string, why: string) {
  const err = check(id, why);
  if (err) return { ok: false, error: err } as const;
  return call(`/admin/disputes/${id}/reject`, { reason: why });
}

export async function payoutAction(id: string, action: "retry" | "close", why: string) {
  const err = check(id, why);
  if (err) return { ok: false, error: err } as const;
  return call(`/admin/payouts/${id}/${action}`, { reason: why });
}

export async function eventAction(id: string, action: "retry" | "dismiss", why: string) {
  const err = check(id, why);
  if (err) return { ok: false, error: err } as const;
  return call(`/admin/payment-events/${id}/${action}`, { reason: why });
}

export async function confirmEmployerInvoice(id: string) {
  if (!uuid.safeParse(id).success) return { ok: false, error: "Requête invalide." } as const;
  try {
    await apiFetch(`/admin/employer-invoices/${id}/confirm-payment`, { method: "POST" });
    revalidatePath("/admin", "layout");
    return { ok: true } as const;
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue." } as const;
  }
}

export async function replySupport(id: string, reply: string, close: boolean) {
  if (!uuid.safeParse(id).success) return { ok: false, error: "Requête invalide." } as const;
  if (reply.trim().length < 5) return { ok: false, error: "Rédigez une réponse." } as const;
  return call(`/admin/support/${id}/reply`, { reply: reply.slice(0, 4000), close });
}

const email = z.string().trim().toLowerCase().email("Adresse e-mail invalide.").max(254);
const ACCESS_ROLES = { merchant: ["merchant_owner", "merchant_staff"], organization: ["hr_admin", "hr_viewer"] } as const;

const rhService = z.object({
  name: z.string().trim().min(2, "Indiquez le nom du service RH.").max(160),
  city_label: z.string().trim().max(80),
  hr_email: email,
});

export async function createRhService(raw: unknown) {
  const p = rhService.safeParse(raw);
  if (!p.success) return { ok: false, error: p.error.issues[0].message } as const;
  return call("/admin/organizations", p.data);
}

export async function grantAccess(scopeType: "merchant" | "organization", scopeId: string, address: string, role: string) {
  if (!uuid.safeParse(scopeId).success) return { ok: false, error: "Requête invalide." } as const;
  const e = email.safeParse(address);
  if (!e.success) return { ok: false, error: e.error.issues[0].message } as const;
  if (!(ACCESS_ROLES[scopeType] as readonly string[]).includes(role)) return { ok: false, error: "Rôle invalide." } as const;
  return call("/admin/access", { email: e.data, scope_type: scopeType, scope_id: scopeId, role });
}

export async function revokeAccess(id: string) {
  if (!uuid.safeParse(id).success) return { ok: false, error: "Requête invalide." } as const;
  return call(`/admin/access/${id}/revoke`, {});
}

export async function openCity(slug: string, why: string) {
  const city = z.string().trim().min(2, "Indiquez la ville.").max(64).safeParse(slug);
  if (!city.success) return { ok: false, error: city.error.issues[0].message } as const;
  const r = reason.safeParse(why);
  if (!r.success) return { ok: false, error: r.error.issues[0].message } as const;
  return call("/admin/cities/open", { slug: city.data, reason: why });
}

export async function setDemoLocations(visible: boolean, why: string) {
  const r = reason.safeParse(why);
  if (!r.success) return { ok: false, error: r.error.issues[0].message } as const;
  return call("/admin/demo-locations", { visible, reason: why });
}

export async function decideChange(id: string, approve: boolean, why: string) {
  const err = check(id, why);
  if (err) return { ok: false, error: err } as const;
  return call(`/admin/change-requests/${id}/decision`, { approve, reason: why });
}

export async function hideReview(id: string, why: string) {
  const err = check(id, why);
  if (err) return { ok: false, error: err } as const;
  return call(`/admin/reviews/${id}/hide`, { reason: why });
}

const eventSchema = z.object({
  location_id: z.string().uuid(),
  title: z.string().trim().min(2).max(120),
  summary: z.string().trim().max(500),
  starts_at: z.string().min(16),
  ends_at: z.string().min(16),
  price_credits: z.number().int().min(1).max(500),
});

export async function saveAdminEvent(id: string | null, raw: unknown): Promise<{ ok: true; id: string } | { ok: false; error: string }> {
  const parsed = eventSchema.safeParse(raw);
  if (!parsed.success) return { ok: false, error: "Vérifiez le titre, les horaires et le prix." };
  try {
    const data = await apiFetch<{ id: string }>(id ? `/admin/events/${id}` : "/admin/events", {
      method: id ? "PATCH" : "POST",
      body: JSON.stringify(parsed.data),
    });
    revalidatePath("/admin/evenements");
    return { ok: true, id: data.id };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}

export async function setAdminEventVisible(id: string, published: boolean): Promise<ActionResult> {
  if (!uuid.safeParse(id).success) return { ok: false, error: "Requête invalide." };
  try {
    await apiFetch(`/admin/events/${id}/visibility`, { method: "POST", body: JSON.stringify({ published }) });
    revalidatePath("/admin/evenements");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}

export async function uploadAdminEventPhoto(id: string, file: File): Promise<ActionResult> {
  if (!uuid.safeParse(id).success) return { ok: false, error: "Requête invalide." };
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return { ok: false, error: "Session expirée." };
  const body = new FormData();
  body.set("file", file, file.name);
  const res = await fetch(`${process.env.XPASS_API_URL ?? "http://localhost:8000"}/api/v1/admin/events/${id}/cover`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body,
    cache: "no-store",
  });
  revalidatePath("/admin/evenements");
  if (!res.ok) return { ok: false, error: "Photo refusée : JPEG, PNG ou WebP, 400 pixels minimum." };
  return { ok: true };
}
