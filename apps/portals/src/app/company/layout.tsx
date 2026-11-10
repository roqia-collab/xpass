import type { ReactNode } from "react";

import type { NavItem } from "@/components/nav-links";
import { PortalShell } from "@/components/shell";
import { SpaceSwitcher } from "@/components/space-switcher";
import { spacesFor } from "@/lib/roles";
import { clientAppUrl, mediaUrl, requireSpace, spaceHrefs } from "@/lib/session";

const NAV: NavItem[] = [
  { href: "/company", label: "Budgets", icon: "wallet" },
  { href: "/company/salaries", label: "Salariés", icon: "users" },
  { href: "/company/commercants", label: "Commerçants", icon: "store" },
  { href: "/company/factures", label: "Factures et rapports", short: "Factures", icon: "file" },
  { href: "/company/parametres", label: "Paramètres", icon: "settings" },
];

export default async function CompanyLayout({ children }: { children: ReactNode }) {
  const me = await requireSpace("company");
  return (
    <PortalShell
      brandSub="Entreprises"
      nav={NAV}
      promo={<>Le même pass, pour vos salariés.</>}
      promoImage={mediaUrl("demo/heroes/sport.jpg") ?? undefined}
      searchPlaceholder="Rechercher un salarié, une information…"
      accountName={me.display_name}
      accountDetail={me.memberships.find((m) => m.scope_type === "organization")?.scope_name ?? ""}
      contextSwitcher={<SpaceSwitcher spaces={spacesFor(me)} appUrl={clientAppUrl()} homes={spaceHrefs()} />}
    >
      {children}
    </PortalShell>
  );
}
