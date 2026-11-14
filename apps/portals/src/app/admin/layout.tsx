import type { ReactNode } from "react";

import type { NavItem } from "@/components/nav-links";
import { PortalShell } from "@/components/shell";
import { SpaceSwitcher } from "@/components/space-switcher";
import type { AdminOverview } from "@/lib/admin-types";
import { clientAppUrl, mediaUrl, requireSpace, tryApi } from "@/lib/session";

import { AdminAlerts, type AdminAlert } from "./alerts";

const NAV: NavItem[] = [
  { href: "/admin", label: "Vue d’ensemble", short: "Accueil", icon: "home" },
  { href: "/admin/demandes", label: "Demandes", icon: "message" },
  { href: "/admin/administrateurs", label: "Admins", icon: "shield" },
  { href: "/admin/partenaires", label: "Commerçants", icon: "users" },
  { href: "/admin/entreprises", label: "Services RH", icon: "store" },
  { href: "/admin/evenements", label: "Événements", icon: "calendar" },
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
  const [requests, support, overview] = await Promise.all([
    tryApi<{ status: string; kind: string; full_name: string; place_name: string }[]>("/admin/access-requests"),
    tryApi<{ status: string; subject: string; customer_name: string }[]>("/admin/support?status=open"),
    tryApi<AdminOverview>("/admin/overview"),
  ]);
  const alerts: AdminAlert[] = [];
  for (const row of (requests.data ?? []).filter((row) => row.status === "pending").slice(0, 6)) {
    alerts.push({
      href: "/admin/demandes",
      title: row.kind === "rh" ? "Demande de service RH" : "Demande commerçant",
      detail: `${row.full_name} · ${row.place_name}`,
    });
  }
  if ((overview.data?.merchants_to_review ?? 0) > 0) {
    alerts.push({ href: "/admin/partenaires", title: "Commerçants à vérifier", detail: `${overview.data?.merchants_to_review} dossier(s) en attente` });
  }
  if ((overview.data?.open_disputes ?? 0) > 0) {
    alerts.push({ href: "/admin/litiges", title: "Litiges ouverts", detail: `${overview.data?.open_disputes} dossier(s)` });
  }
  for (const row of (support.data ?? []).filter((row) => row.status === "open").slice(0, 4)) {
    alerts.push({ href: "/admin/assistance", title: "Message assistance", detail: `${row.customer_name} · ${row.subject}` });
  }
  return (
    <PortalShell
      brandSub="Admin"
      nav={NAV}
      promo={<>L’admin ouvre le service RH. Le RH ajoute ses commerçants.</>}
      promoImage={mediaUrl("demo/heroes/culture.jpg") ?? undefined}
      searchPlaceholder="Rechercher un commerçant, une demande, un numéro…"
      accountName={me.display_name}
      accountDetail="Opérations XPASS"
      alerts={<AdminAlerts items={alerts} />}
      contextSwitcher={<SpaceSwitcher spaces={["admin"]} appUrl={clientAppUrl()} showApp />}
    >
      {children}
    </PortalShell>
  );
}
