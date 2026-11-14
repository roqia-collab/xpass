"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { apiFetch } from "@/lib/session";

export async function decideRequest(id: string, decision: "accept" | "refuse", password = "") {
  if (!z.string().uuid().safeParse(id).success) return { ok: false as const, error: "Requête invalide." };
  if (decision === "accept") {
    const p = z.string().min(8, "8 caractères minimum, avec une lettre et un chiffre.").max(72).safeParse(password);
    if (!p.success) return { ok: false as const, error: p.error.issues[0].message };
  }
  try {
    const sent = await apiFetch<{ mailed?: boolean }>(`/admin/access-requests/${id}/${decision}`, {
      method: "POST",
      body: JSON.stringify(decision === "accept" ? { password } : {}),
    });
    revalidatePath("/admin/demandes");
    return { ok: true as const, mailed: Boolean(sent.mailed) };
  } catch (e) {
    return { ok: false as const, error: e instanceof Error ? e.message : "Décision impossible." };
  }
}
