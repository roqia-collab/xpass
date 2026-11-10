"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { apiFetch } from "@/lib/session";

/** Accès de l'équipe au portail (responsable uniquement : contrôlé par l'API). */
const id = z.string().uuid();
const email = z.string().trim().toLowerCase().email("Adresse e-mail invalide.").max(254);

async function call(path: string, body: unknown) {
  try {
    await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
    revalidatePath("/partner/equipe");
    return { ok: true as const };
  } catch (e) {
    return { ok: false as const, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}

export async function inviteTeamMember(locationId: string, address: string, role: "merchant_owner" | "merchant_staff") {
  if (!id.safeParse(locationId).success) return { ok: false as const, error: "Requête invalide." };
  const e = email.safeParse(address);
  if (!e.success) return { ok: false as const, error: e.error.issues[0]!.message };
  if (role !== "merchant_owner" && role !== "merchant_staff") return { ok: false as const, error: "Rôle invalide." };
  return call(`/partner/locations/${locationId}/access`, { email: e.data, role });
}

export async function removeTeamMember(locationId: string, membershipId: string) {
  if (!id.safeParse(locationId).success || !id.safeParse(membershipId).success) {
    return { ok: false as const, error: "Requête invalide." };
  }
  return call(`/partner/locations/${locationId}/access/${membershipId}/revoke`, {});
}
