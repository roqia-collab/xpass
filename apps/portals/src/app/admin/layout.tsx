import type { ReactNode } from "react";

import type { NavItem } from "@/components/nav-links";
import { PortalShell } from "@/components/shell";
import { SpaceSwitcher } from "@/components/space-switcher";
import { spacesFor } from "@/lib/roles";
import { clientAppUrl, mediaUrl, requireSpace, spaceHrefs } from "@/lib/session";

const NAV: NavItem[] = [
  { href: "/admin", label: "Vue d’ensemble", short: "Accueil", icon: "home" },
  { href: "/admin/partenaires", label: "Partenaires", icon: "users" },
  { href: "/admin/entreprises", label: "Services RH", icon: "store" },
  { href: "/admin/moderation", label: "Modération", icon: "message" },
  { href: "/admin/litiges", label: "Litiges", icon: "shield" },
  { href: "/admin/avis", label: "Avis", icon: "star" },
  { href: "/admin/assistance", label: "Assistance", icon: "message" },
  { href: "/admin/formules", label: "Formules", icon: "coins" },
  { href: "/admin/paiements", label: "Paiements", icon: "card" },
  { href: "/admin/audit", label: "Audit", icon: "audit" },
];

export default async function AdminLayout({ children }: { children: ReactNode }) {
  const me = await requireSpace("admin");
  return (
    <PortalShell
      brandSub="Administration"
      nav={NAV}
      promo={<>Le pass crédits. Sport, culture, beauté, sorties.</>}
      promoImage={mediaUrl("demo/heroes/culture.jpg") ?? undefined}
      searchPlaceholder="Rechercher un partenaire, une demande, un numéro…"
      accountName={me.display_name}
      accountDetail="Opérations XPASS"
      contextSwitcher={<SpaceSwitcher spaces={spacesFor(me)} appUrl={clientAppUrl()} homes={spaceHrefs()} />}
    >
      {children}
    </PortalShell>
  );
}
