import type { ReactNode } from "react";

import type { NavItem } from "@/components/nav-links";
import { PortalShell } from "@/components/shell";
import { mediaUrl, requireSpace } from "@/lib/session";

const NAV: NavItem[] = [
  { href: "/company", label: "Budgets", icon: "wallet" },
  { href: "/company/salaries", label: "Salariés", icon: "users" },
  { href: "/company/demandes", label: "Demandes", icon: "message" },
  { href: "/company/commercants", label: "Commerçants", icon: "store" },
  { href: "/company/evenements", label: "Événements", icon: "calendar" },
  { href: "/company/factures", label: "Factures et rapports", short: "Factures", icon: "file" },
  { href: "/company/parametres", label: "Paramètres", icon: "settings" },
];

export default async function CompanyLayout({ children }: { children: ReactNode }) {
  const me = await requireSpace("company");
  return (
    <PortalShell
      brandSub="RH"
      nav={NAV}
      promo={<>Vos salariés réservent chez vos commerçants avec leurs crédits.</>}
      promoImage={mediaUrl("demo/heroes/sport.jpg") ?? undefined}
      searchPlaceholder="Rechercher un salarié, une information…"
      accountName={me.display_name}
      accountDetail={me.memberships.find((m) => m.scope_type === "organization")?.scope_name ?? ""}
      contextSwitcher={null}
    >
      {children}
    </PortalShell>
  );
}
