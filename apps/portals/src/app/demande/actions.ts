"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";

import { apiFetch } from "@/lib/session";

const requestForm = z.object({
  kind: z.enum(["rh", "merchant"]),
  gmail: z.string().trim().toLowerCase().email("Indiquez une adresse Gmail.").max(254),
  full_name: z.string().trim().min(2, "Indiquez votre nom.").max(120),
  place_name: z.string().trim().min(2, "Indiquez le nom du service ou de l’établissement.").max(160),
  city: z.string().trim().min(2, "Indiquez la ville.").max(80),
  message: z.string().trim().max(1000).optional().default(""),
  website: z.string().max(200).optional().default(""),
});

export async function submitAccessRequest(raw: unknown) {
  const p = requestForm.safeParse(raw);
  if (!p.success) return { ok: false as const, error: p.error.issues[0].message };
  if (!p.data.gmail.endsWith("@gmail.com") && !p.data.gmail.endsWith("@googlemail.com")) {
    return { ok: false as const, error: "Indiquez une adresse Gmail (@gmail.com)." };
  }
  try {
    await apiFetch("/access-requests", { method: "POST", body: JSON.stringify(p.data) });
    return { ok: true as const };
  } catch (e) {
    return { ok: false as const, error: e instanceof Error ? e.message : "Envoi impossible." };
  }
}
