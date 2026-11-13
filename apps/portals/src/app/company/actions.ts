"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { z } from "zod";

import { SESSION_COOKIE, apiFetch } from "@/lib/session";
import type { CsvPreview } from "@/lib/types";

/** Mutations du portail RH (Server Actions). Droits et règles contrôlés par l'API. */
type Result<T = null> = { ok: true; data: T } | { ok: false; error: string; headers?: string[] };

async function call<T>(path: string, method: string, body?: unknown): Promise<Result<T>> {
  try {
    const data = await apiFetch<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
    revalidatePath("/company", "layout");
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}

const mapping = z.record(z.enum(["email", "first_name", "last_name"]), z.string().max(120)).nullable();

export async function inviteEmployee(raw: unknown) {
  const p = z.object({ email: z.string().trim().max(254), first_name: z.string().max(80), last_name: z.string().max(80) }).safeParse(raw);
  if (!p.success) return { ok: false, error: "Saisie invalide." } as const;
  return call("/company/employees", "POST", p.data);
}

export async function previewCsv(content: string, map: Record<string, string> | null): Promise<Result<CsvPreview>> {
  if (content.length > 200_000) return { ok: false, error: "Fichier trop volumineux (200 Ko maximum)." };
  const m = mapping.safeParse(map);
  if (!m.success) return { ok: false, error: "Correspondance de colonnes invalide." };
  try {
    return { ok: true, data: await apiFetch<CsvPreview>("/company/employees/import/preview", { method: "POST", body: JSON.stringify({ content, mapping: m.data }) }) };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}

export async function importCsv(content: string, map: Record<string, string> | null) {
  const m = mapping.safeParse(map);
  if (!m.success || content.length > 200_000) return { ok: false, error: "Import invalide." } as const;
  return call<{ created: number }>("/company/employees/import", "POST", { content, mapping: m.data });
}

export async function employeeAction(employeeId: string, action: "suspend" | "reactivate" | "remove") {
  if (!z.string().uuid().safeParse(employeeId).success || !["suspend", "reactivate", "remove"].includes(action)) {
    return { ok: false, error: "Requête invalide." } as const;
  }
  return call(`/company/employees/${employeeId}/${action}`, "POST");
}

export async function savePolicy(raw: unknown) {
  const p = z
    .object({
      credits_per_month: z.coerce.number().int().min(1, "Indiquez un nombre de crédits.").max(10000),
      eligible_categories: z.array(z.string().max(32)).nullable(),
      credit_validity_days: z.coerce.number().int().min(7).max(366),
      effective_from: z.string().regex(/^\d{4}-\d{2}-01$/, "Choisissez un mois."),
    })
    .safeParse(raw);
  if (!p.success) return { ok: false, error: p.error.issues[0]?.message ?? "Saisie invalide." } as const;
  return call("/company/policy", "PUT", p.data);
}

const merchantForm = z.object({
  display_name: z.string().trim().min(2, "Indiquez le nom du commerçant.").max(120),
  owner_email: z.string().trim().toLowerCase().email("Adresse e-mail invalide.").max(254),
  location_name: z.string().trim().min(2, "Indiquez le nom de l’établissement.").max(120),
  subcategory_slug: z.string().trim().min(2).max(32),
  address_line: z.string().trim().min(3, "Indiquez la rue.").max(200),
  postal_code: z.string().trim().min(4).max(12),
  city: z.string().trim().min(2).max(80),
  description: z.string().trim().max(2000),
  price_credits: z.coerce.number().int().min(1).max(500),
});

export async function createMerchant(raw: unknown) {
  const p = merchantForm.safeParse(raw);
  if (!p.success) return { ok: false, error: p.error.issues[0].message } as const;
  return call<{ id: string }>("/company/merchants", "POST", p.data);
}

export async function locateAddress(raw: unknown) {
  const p = merchantForm.pick({ address_line: true, postal_code: true, city: true }).safeParse(raw);
  if (!p.success) return { ok: false, error: p.error.issues[0].message } as const;
  return call<{ label: string; latitude: number; longitude: number; district: string }>("/company/merchants/locate", "POST", p.data);
}

export async function updateMerchant(id: string, raw: unknown) {
  if (!z.string().uuid().safeParse(id).success) return { ok: false, error: "Requête invalide." } as const;
  const p = merchantForm.safeParse(raw);
  if (!p.success) return { ok: false, error: p.error.issues[0].message } as const;
  return call(`/company/merchants/${id}`, "PATCH", p.data);
}

export async function setMerchantVisibility(id: string, published: boolean) {
  if (!z.string().uuid().safeParse(id).success) return { ok: false, error: "Requête invalide." } as const;
  return call(`/company/merchants/${id}/visibility`, "POST", { published });
}

export async function uploadMerchantPhoto(id: string, form: FormData) {
  if (!z.string().uuid().safeParse(id).success) return { ok: false, error: "Requête invalide." } as const;
  const file = form.get("file");
  if (!(file instanceof File) || file.size === 0) return { ok: false, error: "Choisissez une photo." } as const;
  if (file.size > 8 * 1024 * 1024) return { ok: false, error: "Photo trop lourde (8 Mo maximum)." } as const;
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  const body = new FormData();
  body.set("file", file, file.name);
  try {
    const res = await fetch(`${process.env["XPASS_API_URL"] ?? "http://localhost:8000"}/api/v1/company/merchants/${id}/cover`, {
      method: "POST",
      body,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    });
    if (!res.ok) {
      const err = (await res.json().catch(() => null)) as { detail?: { message?: string } } | null;
      return { ok: false, error: err?.detail?.message ?? `Erreur API (${res.status}).` } as const;
    }
    revalidatePath("/company", "layout");
    return { ok: true, data: null } as const;
  } catch {
    return { ok: false, error: "L'API XPASS est injoignable." } as const;
  }
}

export async function requestFunding(amountMinor: number) {
  if (!Number.isInteger(amountMinor) || amountMinor < 100) return { ok: false, error: "Montant invalide." } as const;
  return call("/company/invoices", "POST", { amount_minor: amountMinor });
}

const eventSchema = z.object({
  location_id: z.string().uuid(),
  title: z.string().trim().min(2).max(120),
  summary: z.string().trim().max(500),
  starts_at: z.string().min(16),
  ends_at: z.string().min(16),
  price_credits: z.number().int().min(1).max(500),
});

export async function saveCompanyEvent(id: string | null, raw: unknown): Promise<{ ok: true; id: string } | { ok: false; error: string }> {
  const parsed = eventSchema.safeParse(raw);
  if (!parsed.success) return { ok: false, error: "Vérifiez le titre, les horaires et le prix." };
  const res = await call<{ id: string }>(id ? `/company/events/${id}` : "/company/events", id ? "PATCH" : "POST", parsed.data);
  revalidatePath("/company/evenements");
  return res.ok ? { ok: true, id: res.data.id } : res;
}

export async function setCompanyEventVisible(id: string, published: boolean): Promise<{ ok: true } | { ok: false; error: string }> {
  if (!z.string().uuid().safeParse(id).success) return { ok: false, error: "Requête invalide." };
  const res = await call(`/company/events/${id}/visibility`, "POST", { published });
  revalidatePath("/company/evenements");
  return res.ok ? { ok: true } : res;
}

export async function uploadCompanyEventPhoto(id: string, file: File): Promise<{ ok: true } | { ok: false; error: string }> {
  if (!z.string().uuid().safeParse(id).success) return { ok: false, error: "Requête invalide." };
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return { ok: false, error: "Session expirée." };
  const body = new FormData();
  body.set("file", file, file.name);
  const res = await fetch(`${process.env["XPASS_API_URL"] ?? "http://localhost:8000"}/api/v1/company/events/${id}/cover`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body,
    cache: "no-store",
  });
  revalidatePath("/company/evenements");
  if (!res.ok) return { ok: false, error: "Photo refusée : JPEG, PNG ou WebP, 400 pixels minimum." };
  return { ok: true };
}
