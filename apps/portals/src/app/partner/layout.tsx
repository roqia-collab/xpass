import type { ReactNode } from "react";

import { PortalShell } from "@/components/shell";
import type { NavItem } from "@/components/nav-links";
import { SpaceSwitcher } from "@/components/space-switcher";
import { spacesFor } from "@/lib/roles";
import { clientAppUrl, mediaUrl, requireSpace, spaceHrefs } from "@/lib/session";

import { getCurrentLocation, getPartnerLocations } from "./data";
import { LocationSwitcher } from "./location-switcher";

const NAV: NavItem[] = [
  { href: "/partner", label: "Vue d’ensemble", short: "Accueil", icon: "home" },
  { href: "/partner/planning", label: "Planning", icon: "calendar" },
  { href: "/partner/scanner", label: "Scanner", icon: "scan" },
  { href: "/partner/prestations", label: "Prestations", icon: "flower" },
  { href: "/partner/equipe", label: "Équipe", icon: "users" },
  { href: "/partner/reglements", label: "Règlements", icon: "wallet" },
  { href: "/partner/statistiques", label: "Statistiques", icon: "chart" },
  { href: "/partner/messages", label: "Messages", icon: "message" },
  { href: "/partner/avis", label: "Avis", icon: "star" },
  { href: "/partner/etablissement", label: "Établissement", icon: "store" },
];

export default async function PartnerLayout({ children }: { children: ReactNode }) {
  const me = await requireSpace("partner");
  const [location, locations] = await Promise.all([getCurrentLocation(), getPartnerLocations()]);

  return (
    <PortalShell
      brandSub="Commerçant"
      nav={NAV}
      promo={<>Les salariés réservent chez vous avec leurs crédits.</>}
      promoImage={mediaUrl(location?.cover_image_key ?? "demo/heroes/beaute.jpg") ?? undefined}
      searchPlaceholder="Rechercher un client, une prestation…"
      accountName={me.display_name}
      accountDetail={me.memberships.find((m) => m.scope_type === "merchant")?.scope_name ?? ""}
      contextSwitcher={
        <>
          <SpaceSwitcher spaces={spacesFor(me)} appUrl={clientAppUrl()} homes={await spaceHrefs()} />
          {location && (
            <LocationSwitcher
              currentId={location.id}
              locations={locations.map((l) => ({
                id: l.id, name: l.name, district_label: l.district_label, status: l.status, cover: mediaUrl(l.cover_image_key ?? null),
              }))}
            />
          )}
        </>
      }
    >
      {location && location.merchant_status && location.merchant_status !== "approved" && (
        <div className="notice" role="status">
          <span aria-hidden>ⓘ</span>
          <span>
            <strong>{location.merchant_status === "documents_missing" ? "Compléments demandés par XPASS." : location.merchant_status === "suspended" ? "Compte commerçant suspendu." : "Dossier en cours de validation par XPASS."}</strong>{" "}
            Votre établissement n’est pas encore visible des clients. Complétez photo, prestations et horaires en attendant.
          </span>
        </div>
      )}
      {location && location.merchant_status === "approved" && location.status !== "published" && (
        <div className="notice" role="status">
          <span aria-hidden>ⓘ</span>
          <span><strong>Dossier validé.</strong> L’établissement sera publié par l’équipe XPASS après relecture de la fiche.</span>
        </div>
      )}
      {children}
    </PortalShell>
  );
}
