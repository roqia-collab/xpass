"use server";

import { revalidatePath } from "next/cache";

import { apiFetch } from "@/lib/session";

/** Compte de versement (Stripe Connect). L'identité et l'IBAN sont saisis chez le prestataire, jamais ici. */
type LinkResult = { ok: true; url: string } | { ok: false; error: string };

async function link(path: string): Promise<LinkResult> {
  try {
    const { url } = await apiFetch<{ url: string }>(path, { method: "POST", body: "{}" });
    // Seules les pages du prestataire ou du bac à sable local sont acceptées comme destination.
    const host = new URL(url).hostname;
    const allowed = host.endsWith("stripe.com") || host === "localhost" || host === "127.0.0.1";
    return allowed ? { ok: true, url } : { ok: false, error: "Adresse de redirection inattendue." };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}

export async function startPayoutOnboarding(): Promise<LinkResult> {
  return link("/partner/payout-account/onboarding");
}

export async function openPayoutDashboard(): Promise<LinkResult> {
  return link("/partner/payout-account/dashboard");
}

export async function refreshPayoutStatus(): Promise<{ ok: true; status: string } | { ok: false; error: string }> {
  try {
    const r = await apiFetch<{ psp_status: string }>("/partner/payout-account/refresh", { method: "POST", body: "{}" });
    revalidatePath("/partner/reglements");
    return { ok: true, status: r.psp_status };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}
