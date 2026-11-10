"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { apiFetch } from "@/lib/session";

const id = z.string().uuid();

/** Lien vers la page de paiement du prestataire (carte ou prélèvement SEPA). */
export async function payInvoice(invoiceId: string) {
  if (!id.safeParse(invoiceId).success) return { ok: false as const, error: "Requête invalide." };
  try {
    const { url } = await apiFetch<{ url: string }>(`/company/invoices/${invoiceId}/pay`, { method: "POST", body: "{}" });
    const host = new URL(url).hostname;
    if (!(host.endsWith("stripe.com") || host === "localhost" || host === "127.0.0.1")) {
      return { ok: false as const, error: "Adresse de paiement inattendue." };
    }
    return { ok: true as const, url };
  } catch (e) {
    return { ok: false as const, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}

export async function createApiKey(label: string) {
  try {
    const r = await apiFetch<{ key: string }>("/company/api-keys", { method: "POST", body: JSON.stringify({ label: label.slice(0, 80) }) });
    revalidatePath("/company/salaries");
    return { ok: true as const, key: r.key };
  } catch (e) {
    return { ok: false as const, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}

export async function revokeApiKey(keyId: string) {
  if (!id.safeParse(keyId).success) return { ok: false as const, error: "Requête invalide." };
  try {
    await apiFetch(`/company/api-keys/${keyId}/revoke`, { method: "POST", body: "{}" });
    revalidatePath("/company/salaries");
    return { ok: true as const };
  } catch (e) {
    return { ok: false as const, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}
