import { LogOut, Search } from "lucide-react";
import type { ReactNode } from "react";

import { logout } from "@/app/login/actions";
import { initials } from "@/lib/roles";

import { BottomNav, NavLinks, type NavItem } from "./nav-links";

interface ShellProps {
  variant?: "cream" | "navy";
  brandSub?: string;
  section?: string;
  nav: NavItem[];
  promo?: ReactNode;
  /** Visuel décoratif de l'encart bas de menu (maquettes 18, 21, 26). */
  promoImage?: string;
  searchPlaceholder: string;
  contextSwitcher?: ReactNode;
  accountName: string;
  accountDetail: string;
  children: ReactNode;
}

export function PortalShell(props: ShellProps) {
  return (
    <div className="shell">
      {/* Accessibilité clavier : accès direct au contenu, sans parcourir la navigation. */}
      <a className="skip-link" href="#contenu">Aller au contenu</a>
      <aside className={`sidebar ${props.variant === "navy" ? "navy" : ""}`} aria-label="Navigation principale">
        <div className="brand">
          <img
            src="/logo.png"
            alt="XPASS"
            style={props.variant === "navy" ? { filter: "brightness(0) invert(1)" } : undefined}
          />
          {props.brandSub && <small>{props.brandSub}</small>}
        </div>
        {props.section && <div className="section">{props.section}</div>}
        <NavLinks items={props.nav} />
        {props.promo && (
          <div className="promo">
            {props.promoImage && <img src={props.promoImage} alt="" />}
            <span>{props.promo}</span>
          </div>
        )}
      </aside>
      <div className="main">
        <header className="topbar">
          {props.contextSwitcher}
          {/* La recherche transverse sera branchée avec les modules concernés. */}
          <label className="search">
            <Search size={18} aria-hidden />
            <input placeholder={props.searchPlaceholder} aria-label={props.searchPlaceholder} disabled />
          </label>
          <div className="account">
            <div className="avatar" aria-hidden>
              {initials(props.accountName)}
            </div>
            <div style={{ lineHeight: 1.2 }}>
              <strong style={{ display: "block" }}>{props.accountName}</strong>
              <span className="muted" style={{ fontSize: 13 }}>
                {props.accountDetail}
              </span>
            </div>
            <form action={logout}>
              <button className="btn ghost" type="submit" title="Se déconnecter" aria-label="Se déconnecter">
                <LogOut size={18} />
              </button>
            </form>
          </div>
        </header>
        <main className="content" id="contenu" tabIndex={-1}>{props.children}</main>
      </div>
      <BottomNav items={props.nav} />
    </div>
  );
}
