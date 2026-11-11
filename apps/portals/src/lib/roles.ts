import type { CommercialStatus, Me, PspStatus, Space } from "./types";

const SPACE_ROLES: Record<Space, string[]> = {
  admin: ["platform_admin", "platform_operator"],
  company: ["hr_admin", "hr_viewer"],
  partner: ["merchant_owner", "merchant_staff"],
};

/** Ordre d'affichage : administration, RH, commerçant. */
export const SPACE_ORDER: Space[] = ["admin", "company", "partner"];

/** Espaces accessibles à l'utilisateur, déduits de ses rattachements. Le backend reste l'autorité. */
export function spacesFor(me: Pick<Me, "memberships">): Space[] {
  return SPACE_ORDER.filter((space) => me.memberships.some((m) => SPACE_ROLES[space].includes(m.role)));
}

export function canAccess(me: Pick<Me, "memberships">, space: Space): boolean {
  return spacesFor(me).includes(space);
}

export const SPACE_HOME: Record<Space, string> = {
  partner: "/partner",
  company: "/company",
  admin: "/admin",
};

export const SPACE_LABEL: Record<Space, string> = {
  admin: "Admin",
  company: "RH",
  partner: "Commerçant",
};

/** Même phrase sur l’admin, le RH, le commerçant et l’accueil. */
export const NETWORK_LINE =
  "L’admin ouvre le service RH. Le RH ajoute ses commerçants. Leurs prestations publiées apparaissent dans l’application client.";

export const COMMERCIAL_LABEL: Record<CommercialStatus, { label: string; tone: "lavender" | "coral" | "mint" | "grey" }> = {
  draft: { label: "Brouillon", tone: "grey" },
  pending_review: { label: "À vérifier", tone: "lavender" },
  documents_missing: { label: "Documents manquants", tone: "coral" },
  approved: { label: "Validé", tone: "mint" },
  suspended: { label: "Suspendu", tone: "coral" },
};

export const PSP_LABEL: Record<PspStatus, string> = {
  not_started: "PSP non démarré",
  pending: "PSP en cours",
  verified: "PSP vérifié",
  rejected: "PSP refusé",
};

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join("");
}

export function formatDuration(min: number): string {
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m === 0 ? `${h} h` : `${h} h ${String(m).padStart(2, "0")}`;
}
