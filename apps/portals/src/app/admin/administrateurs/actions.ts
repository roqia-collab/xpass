"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { apiFetch } from "@/lib/session";

export async function createAdministrator(raw: unknown) {
  const p = z.object({
    email: z.string().trim().toLowerCase().email("Indiquez un Gmail."),
    full_name: z.string().trim().min(2, "Indiquez le nom.").max(120),
    password: z.string().min(8, "8 caractères minimum, avec une lettre et un chiffre.").max(72),
  }).safeParse(raw);
  if (!p.success) return { ok: false as const, error: p.error.issues[0].message };
  if (!p.data.email.endsWith("@gmail.com") && !p.data.email.endsWith("@googlemail.com")) {
    return { ok: false as const, error: "Les autres admins utilisent une adresse Gmail." };
  }
  try {
    await apiFetch("/admin/administrators", { method: "POST", body: JSON.stringify(p.data) });
    revalidatePath("/admin/administrateurs");
    return { ok: true as const };
  } catch (e) {
    return { ok: false as const, error: e instanceof Error ? e.message : "Création impossible." };
  }
}
