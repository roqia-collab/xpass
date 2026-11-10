"use client";

import {
  BarChart3,
  Building2,
  CalendarDays,
  ClipboardCheck,
  Coins,
  CreditCard,
  FileText,
  Flower2,
  Home,
  MessageCircle,
  MoreHorizontal,
  RefreshCcw,
  ScanLine,
  Settings,
  ShieldCheck,
  Star,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const ICONS = {
  home: Home,
  calendar: CalendarDays,
  scan: ScanLine,
  flower: Flower2,
  users: Users,
  wallet: Wallet,
  store: Building2,
  chart: BarChart3,
  file: FileText,
  settings: Settings,
  shield: ShieldCheck,
  message: MessageCircle,
  refresh: RefreshCcw,
  card: CreditCard,
  audit: ClipboardCheck,
  star: Star,
  coins: Coins,
} satisfies Record<string, LucideIcon>;

export interface NavItem {
  href: string;
  label: string;
  icon: keyof typeof ICONS;
  /** Libellé court pour la barre du bas sur téléphone. */
  short?: string;
  /** Lot de livraison si la page n'est pas encore fonctionnelle. */
  lot?: string;
}

function isActive(items: NavItem[], item: NavItem, pathname: string) {
  const root = items[0]!.href;
  return item.href === root ? pathname === root : pathname.startsWith(item.href);
}

export function NavLinks({ items }: { items: NavItem[] }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Navigation principale" style={{ display: "contents" }}>
      {items.map((item) => {
        const Icon = ICONS[item.icon];
        const active = isActive(items, item, pathname);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-link ${active ? "active" : ""}`}
            aria-current={active ? "page" : undefined}
          >
            <Icon size={20} aria-hidden />
            <span>{item.label}</span>
            {item.lot && <span className="lot">{item.lot}</span>}
          </Link>
        );
      })}
    </nav>
  );
}

/** Barre du bas sur téléphone, au style de l'application (pastille corail, trait sous l'onglet actif). */
export function BottomNav({ items }: { items: NavItem[] }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  // Au-delà de quatre entrées, les suivantes passent dans « Plus ».
  const visible = items.length > 4 ? items.slice(0, 3) : items;
  const more = items.length > 4 ? items.slice(3) : [];
  const moreActive = more.some((i) => isActive(items, i, pathname));

  useEffect(() => setOpen(false), [pathname]);

  return (
    <nav className="bottom-nav" aria-label="Navigation principale">
      {open && (
        <ul className="bottom-more" id="bottom-more">
          {more.map((item) => {
            const Icon = ICONS[item.icon];
            const active = isActive(items, item, pathname);
            return (
              <li key={item.href}>
                <Link href={item.href} className={active ? "active" : ""} aria-current={active ? "page" : undefined}>
                  <Icon size={20} aria-hidden />
                  <span>{item.label}</span>
                  {item.lot && <span className="lot">{item.lot}</span>}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
      {visible.map((item, i) => {
        const Icon = ICONS[item.icon];
        const active = isActive(items, item, pathname);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`bottom-item ${active ? "active" : ""} ${i === 0 ? "first" : ""}`}
            aria-current={active ? "page" : undefined}
          >
            <span className="glyph"><Icon size={i === 0 && active ? 18 : 22} aria-hidden /></span>
            <span className="label">{item.short ?? item.label}</span>
          </Link>
        );
      })}
      {more.length > 0 && (
        <button
          type="button"
          className={`bottom-item ${moreActive ? "active" : ""}`}
          aria-expanded={open}
          aria-controls="bottom-more"
          onClick={() => setOpen((v) => !v)}
        >
          <span className="glyph"><MoreHorizontal size={22} aria-hidden /></span>
          <span className="label">Plus</span>
        </button>
      )}
    </nav>
  );
}
