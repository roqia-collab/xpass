"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { apiFetch } from "@/lib/session";

/** Formules d'abonnement (Server Actions). Règles (prix figé dès qu'il y a des abonnés) contrôlées par l'API. */
const plan = z.object({
  code: z.string().trim().regex(/^[a-z0-9-]{2,40}$/, "Code : lettres minuscules, chiffres et tirets (2 à 40)."),
  name: z.string().trim().min(2, "Nom trop court.").max(80),
  price_euros: z.coerce.number().min(1, "Prix minimum : 1 €.").max(10000),
  credits_per_period: z.coerce.number().int("Nombre de crédits entier.").min(1).max(10000),
  credit_validity_days: z.union([z.literal(""), z.coerce.number().int().min(7).max(366)]),
  psp_price_id: z.string().trim().max(120),
  is_active: z.boolean(),
});

export type PlanForm = z.input<typeof plan>;

export async function savePlan(id: string | null, raw: PlanForm): Promise<{ ok: true } | { ok: false; error: string }> {
  const parsed = plan.safeParse(raw);
  if (!parsed.success) return { ok: false, error: parsed.error.issues[0]?.message ?? "Saisie invalide." };
  if (id !== null && !z.string().uuid().safeParse(id).success) return { ok: false, error: "Requête invalide." };
  const p = parsed.data;
  const body = {
    code: p.code,
    name: p.name,
    // Argent en centimes entiers.
    price_minor: Math.round(p.price_euros * 100),
    credits_per_period: p.credits_per_period,
    credit_validity_days: p.credit_validity_days === "" ? null : p.credit_validity_days,
    psp_price_id: p.psp_price_id || null,
    is_active: p.is_active,
  };
  try {
    await apiFetch(id ? `/admin/plans/${id}` : "/admin/plans", { method: id ? "PUT" : "POST", body: JSON.stringify(body) });
    revalidatePath("/admin/formules");
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}
