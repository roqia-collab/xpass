"use client";

import {
  BarChart3,
  Building2,
  CalendarDays,
  Flower2,
  Home,
  MessageCircle,
  ScanLine,
  Star,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";

import { AccessSection } from "@/components/access-section";

const SECTIONS: { id: string; label: string; short: string; icon: LucideIcon; text: string }[] = [
  { id: "accueil", label: "Vue d’ensemble", short: "Accueil", icon: Home, text: "L’activité du jour, les prestations et les paiements à venir." },
  { id: "planning", label: "Planning", short: "Planning", icon: CalendarDays, text: "Les créneaux réservés par les membres, jour par jour." },
  { id: "scanner", label: "Scanner", short: "Scanner", icon: ScanLine, text: "La validation du QR code au moment du passage." },
  { id: "prestations", label: "Prestations", short: "Offres", icon: Flower2, text: "Le catalogue publié dans l’application : prix, durée, photos." },
  { id: "equipe", label: "Équipe", short: "Équipe", icon: Users, text: "Les personnes qui accueillent et valident les passages." },
  { id: "reglements", label: "Règlements", short: "Règlements", icon: Wallet, text: "Les montants à recevoir après chaque prestation confirmée." },
  { id: "statistiques", label: "Statistiques", short: "Stats", icon: BarChart3, text: "La fréquentation et les crédits utilisés chez vous." },
  { id: "messages", label: "Messages", short: "Messages", icon: MessageCircle, text: "Les échanges avec les membres après leur première demande." },
  { id: "avis", label: "Avis", short: "Avis", icon: Star, text: "Les retours laissés après une visite." },
  { id: "etablissement", label: "Établissement", short: "Lieu", icon: Building2, text: "La fiche visible des clients : adresse, photos, horaires." },
];

/** Premier tableau de bord commerçant, visible sans compte. La connexion ouvre l'autre. */
export function MerchantSite({ signedIn, partner = false }: { signedIn: boolean; partner?: boolean }) {
  const [section, setSection] = useState(SECTIONS[0]!.id);
  const current = SECTIONS.find((item) => item.id === section) ?? SECTIONS[0]!;
  const Icon = current.icon;
  const enter = partner ? "/partner" : signedIn ? "/inscription-partenaire" : "/login?espace=1";
  const label = partner ? "Entrer dans mon espace" : signedIn ? "Ouvrir mon dossier" : "Connexion";

  return (
    <div className="shell">
      <a className="skip-link" href="#contenu">Aller au contenu</a>
      <aside className="sidebar" aria-label="Sections du commerçant">
        <a className="brand" href="/" aria-label="Retour à la présentation">
          <img src="/logo.png" alt="XPASS" />
          <small>Commerçant</small>
        </a>
        <nav aria-label="Sections" style={{ display: "contents" }}>
          {SECTIONS.map((item) => {
            const ItemIcon = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                className={`nav-link ${item.id === current.id ? "active" : ""}`}
                aria-current={item.id === current.id ? "page" : undefined}
                onClick={() => setSection(item.id)}
              >
                <ItemIcon size={20} aria-hidden />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>
      <div className="main">
        <header className="topbar">
          <strong style={{ marginRight: "auto" }}>Tableau de bord</strong>
          <a className="btn primary" href={enter}>
            {label}
          </a>
        </header>
        <main className="content" id="contenu" tabIndex={-1}>
          <p className="eyebrow">Commerçant</p>
          <h1>{current.label}</h1>
          <p className="muted" style={{ maxWidth: "46ch", marginTop: 8 }}>{current.text}</p>
          <section className="card intro-split" style={{ marginTop: 22 }}>
            <img src="/visuels/promo-partenaires.jpg" alt="" style={{ width: "100%", height: 120, objectFit: "cover", borderRadius: 16 }} />
            <div>
              <Icon size={22} aria-hidden />
              <h2 style={{ marginTop: 8 }}>Section ouverte</h2>
              <p className="muted" style={{ marginTop: 6 }}>
                Les chiffres, les réservations et les réglages de votre établissement sont dans le second tableau de bord, après la connexion.
              </p>
              <a className="btn primary" href={enter} style={{ marginTop: 14 }}>
                {label}
              </a>
            </div>
          </section>
          <div style={{ marginTop: 22 }}>
            <AccessSection kind="merchant" />
          </div>
        </main>
      </div>
      <nav className="bottom-nav" aria-label="Sections principales">
        {SECTIONS.slice(0, 5).map((item) => {
          const ItemIcon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              className={`bottom-item ${item.id === current.id ? "active" : ""} ${item.id === "accueil" ? "first" : ""}`}
              onClick={() => setSection(item.id)}
            >
              <span className="glyph"><ItemIcon size={22} aria-hidden /></span>
              <span className="label">{item.short}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
