"use server";

import { z } from "zod";

import { apiFetch } from "@/lib/session";

/** Candidature commerçant (Server Actions). L'API vérifie le SIRET, géocode l'adresse et applique les règles. */
export interface CompanyPreview {
  status: "verified" | "unavailable";
  siret: string;
  legal_name: string | null;
  trade_name: string | null;
  address: string | null;
  postal_code: string | null;
  city: string | null;
}

const siret = z.string().transform((v) => v.replace(/\s+/g, "")).pipe(z.string().regex(/^\d{14}$/, "Le SIRET comporte 14 chiffres."));

export async function checkSiret(raw: string): Promise<{ ok: true; company: CompanyPreview } | { ok: false; error: string }> {
  const s = siret.safeParse(raw);
  if (!s.success) return { ok: false, error: s.error.issues[0]!.message };
  try {
    return { ok: true, company: await apiFetch<CompanyPreview>(`/partners/siret/${s.data}`) };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}

const application = z.object({
  siret,
  display_name: z.string().trim().max(120),
  contact_phone: z.string().trim().min(6, "Indiquez un téléphone de contact.").max(30),
  location_name: z.string().trim().min(2, "Nom de l’établissement trop court.").max(120),
  subcategory_slug: z.string().min(2, "Choisissez votre activité."),
  kind_label: z.string().trim().max(80),
  address_line: z.string().trim().min(3, "Indiquez le numéro et la rue.").max(200),
  postal_code: z.string().trim().regex(/^\d{5}$/, "Code postal à 5 chiffres."),
  city: z.string().trim().min(2, "Indiquez la commune.").max(80),
  description: z.string().trim().max(2000),
  accept: z.literal(true, { error: "Confirmez l’exactitude des informations." }),
});

export async function submitApplication(raw: unknown): Promise<{ ok: true; address: string; check: string } | { ok: false; error: string }> {
  const parsed = application.safeParse(raw);
  if (!parsed.success) return { ok: false, error: parsed.error.issues[0]?.message ?? "Saisie invalide." };
  const { accept: _accept, ...body } = parsed.data;
  try {
    const res = await apiFetch<{ address_label: string; company_check: string }>("/partners/applications", {
      method: "POST",
      body: JSON.stringify(body),
    });
    return { ok: true, address: res.address_label, check: res.company_check };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Erreur inattendue." };
  }
}
