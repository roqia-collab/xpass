import { ArrowRight, Building2, ShieldCheck, Smartphone, Store } from "lucide-react";
import Link from "next/link";
import { redirect } from "next/navigation";

import { NETWORK_LINE, SPACE_LABEL, spacesFor } from "@/lib/roles";
import { clientAppUrl, getMe, spaceHrefs } from "@/lib/session";
import type { Space } from "@/lib/types";

const ICONS: Record<Space, typeof ShieldCheck> = {
  admin: ShieldCheck,
  company: Building2,
  partner: Store,
};

const HINT: Record<Space, string> = {
  admin: "Services RH, commerçants, paiements.",
  company: "Salariés, commerçants, factures.",
  partner: "Prestations, planning, versements.",
};

/** Après connexion : Admin, puis RH, puis site commerçant, plus l'application client. */
export default async function Home() {
  const me = await getMe();
  if (!me) redirect("/login");
  const spaces = spacesFor(me);
  if (spaces.length === 0) redirect("/login?erreur=acces");
  const app = clientAppUrl();
  const homes = spaceHrefs();
  return (
    <div className="hub">
      <header className="hub-head">
        <img src="/logo.png" alt="XPASS" />
      </header>
      <p className="eyebrow hub-kicker">Vos espaces</p>
      <h1 className="hub-title">Où allez-vous maintenant ?</h1>
      <p className="hub-sub muted">
        {NETWORK_LINE}
      </p>
      <ul className="hub-list">
        {spaces.map((space) => {
          const Icon = ICONS[space];
          return (
            <li key={space}>
              <Link href={homes[space]} className="hub-card">
                <Icon size={22} aria-hidden />
                <span>
                  <strong>{SPACE_LABEL[space]}</strong>
                  <span className="muted">{HINT[space]}</span>
                </span>
                <ArrowRight size={18} aria-hidden />
              </Link>
            </li>
          );
        })}
        <li>
          <a href={app} className="hub-card" target="_blank" rel="noreferrer">
            <Smartphone size={22} aria-hidden />
            <span>
              <strong>Application client</strong>
              <span className="muted">Réserver sport, culture, beauté et sorties.</span>
            </span>
            <ArrowRight size={18} aria-hidden />
          </a>
        </li>
      </ul>
    </div>
  );
}
