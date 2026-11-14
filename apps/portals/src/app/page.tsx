import { ArrowRight, Building2, ShieldCheck, Smartphone, Store } from "lucide-react";
import { headers } from "next/headers";
import Link from "next/link";

import { MerchantPresentation } from "@/components/merchant-presentation";
import { canAccess, NETWORK_LINE, SPACE_LABEL, spacesFor } from "@/lib/roles";
import { clientAppUrl, getMe, spaceHrefs } from "@/lib/session";
import type { Space } from "@/lib/types";

const ICONS: Record<Space, typeof ShieldCheck> = {
  admin: ShieldCheck,
  company: Building2,
  partner: Store,
};

const PHOTOS: Record<Space, string> = {
  admin: "/visuels/promo-administration.jpg",
  company: "/visuels/salaries.jpg",
  partner: "/visuels/promo-partenaires.jpg",
};

const HINT: Record<Space, string> = {
  admin: "Services RH, commerçants, paiements.",
  company: "Salariés, commerçants, factures.",
  partner: "Prestations, planning, versements.",
};

function merchantHost(host: string) {
  const name = host.split(",")[0].trim().toLowerCase().replace(/:\d+$/, "");
  return name === "xpass.fr" || name === "www.xpass.fr";
}

/** Site commerçant public, ou choix d'espace après connexion en local. */
export default async function Home() {
  const host = (await headers()).get("x-forwarded-host") ?? (await headers()).get("host") ?? "";
  let me = null;
  try {
    me = await getMe();
  } catch {
    me = null;
  }
  if (merchantHost(host) || !me) return <MerchantPresentation signedIn={Boolean(me)} partner={Boolean(me && canAccess(me, "partner"))} />;

  const spaces = spacesFor(me);
  const app = clientAppUrl();
  const homes = await spaceHrefs();
  return (
    <div className="hub">
      <header className="hub-head">
        <img src="/logo.png" alt="XPASS" />
      </header>
      <p className="eyebrow hub-kicker">Vos espaces</p>
      <h1 className="hub-title">Choisissez votre espace</h1>
      <p className="hub-sub muted">{NETWORK_LINE}</p>
      <ul className="hub-board">
        {spaces.map((space) => {
          const Icon = ICONS[space];
          return (
            <li key={space}>
              <Link href={homes[space]} className="hub-tile">
                <img src={PHOTOS[space]} alt="" />
                <span>
                  <Icon size={18} aria-hidden />
                  <strong>{SPACE_LABEL[space]}</strong>
                  <em>{HINT[space]}</em>
                  <ArrowRight size={18} aria-hidden />
                </span>
              </Link>
            </li>
          );
        })}
        {canAccess(me, "admin") && (
          <li>
            <a href={app} className="hub-tile" target="_blank" rel="noreferrer">
              <img src="/visuels/login-sport.jpg" alt="" />
              <span>
                <Smartphone size={18} aria-hidden />
                <strong>Application client</strong>
                <em>Réservée à l’administrateur.</em>
                <ArrowRight size={18} aria-hidden />
              </span>
            </a>
          </li>
        )}
      </ul>
    </div>
  );
}
