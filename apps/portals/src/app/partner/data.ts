import "server-only";

import { cookies } from "next/headers";
import { cache } from "react";

import { apiFetch } from "@/lib/session";
import type { PartnerLocation } from "@/lib/types";

/** Établissements du commerçant connecté (filtrés côté API par ses rattachements). */
export const getPartnerLocations = cache(() => apiFetch<PartnerLocation[]>("/partner/locations"));

export const LOCATION_COOKIE = "xpass_location";

/** Établissement actif : choisi dans le sélecteur (cookie), sinon le premier. L'API reste juge des droits. */
export async function getCurrentLocation(): Promise<PartnerLocation | undefined> {
  const all = await getPartnerLocations();
  const chosen = (await cookies()).get(LOCATION_COOKIE)?.value;
  return all.find((l) => l.id === chosen) ?? all[0];
}

export const BOOKING_MODE_LABEL: Record<PartnerLocation["offers"][number]["booking_mode"], string> = {
  resource_slot: "Sur rendez-vous",
  capacity_session: "Séance à capacité",
  open_access: "Accès libre",
  external_ticket: "Billet externe",
};

/** Vue de gestion (prestations en brouillon, ressources inactives, exceptions) et droit d'écriture. */
export const getManagedLocation = cache(async () => {
  const location = await getCurrentLocation();
  if (!location) return undefined;
  return apiFetch<import("@/lib/types").ManagedLocation>(`/partner/locations/${location.id}/manage`);
});
