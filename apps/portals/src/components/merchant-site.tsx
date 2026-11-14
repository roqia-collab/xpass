"use client";

import {
  BarChart3,
  Building2,
  CalendarDays,
  Flower2,
  Home,
  MessageCircle,
  ScanLine,
  Sparkles,
  Star,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

import { AccessSection } from "@/components/access-section";
import { PartnerFaq, RevenueCalculator } from "@/components/partner-public";

const SECTIONS: { id: string; label: string; short: string; icon: LucideIcon }[] = [
  { id: "accueil", label: "Vue d’ensemble", short: "Accueil", icon: Home },
  { id: "planning", label: "Planning", short: "Planning", icon: CalendarDays },
  { id: "scanner", label: "Scanner", short: "Scanner", icon: ScanLine },
  { id: "prestations", label: "Prestations", short: "Offres", icon: Flower2 },
  { id: "evenements", label: "Événements", short: "Événements", icon: Sparkles },
  { id: "reglements", label: "Règlements", short: "Règlements", icon: Wallet },
  { id: "statistiques", label: "Statistiques", short: "Stats", icon: BarChart3 },
  { id: "equipe", label: "Équipe", short: "Équipe", icon: Users },
  { id: "messages", label: "Messages", short: "Messages", icon: MessageCircle },
  { id: "avis", label: "Avis", short: "Avis", icon: Star },
  { id: "etablissement", label: "Établissement", short: "Lieu", icon: Building2 },
];

const SLOTS = [
  { time: "09:00", title: "Cours du matin", meta: "4 places ouvertes à XPASS" },
  { time: "12:30", title: "Créneau encore vide", meta: "À publier si vous le souhaitez" },
  { time: "18:30", title: "Séance du soir", meta: "2 places restantes" },
];

/** Premier tableau de bord commerçant, visible sans compte. La connexion ouvre l'autre. */
export function MerchantSite({ signedIn, partner = false }: { signedIn: boolean; partner?: boolean }) {
  const [section, setSection] = useState(SECTIONS[0]!.id);
  useEffect(() => {
    const wanted = new URLSearchParams(window.location.search).get("section");
    if (wanted && SECTIONS.some((item) => item.id === wanted)) setSection(wanted);
  }, []);
  const current = SECTIONS.find((item) => item.id === section) ?? SECTIONS[0]!;
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
          <a href="/" style={{ marginRight: "auto", fontWeight: 700 }}>xpass.fr</a>
          <a className="btn outline" href="/#demarrer">Démarrer</a>
          <a className="btn primary" href={enter}>{label}</a>
        </header>
        <main className="content" id="contenu" tabIndex={-1}>
          <p className="eyebrow">Tableau de bord</p>
          <h1>{current.label}</h1>
          {current.id === "accueil" && (
            <>
              <p className="muted dash-lead">Vos chiffres arrivent après la connexion. En attendant, une semaine se calcule ici.</p>
              <div className="dash-film" aria-hidden>
                <div>
                  {["/visuels/login-sport.jpg", "/visuels/login-beaute.jpg", "/visuels/login-atelier.jpg", "/visuels/promo-partenaires.jpg", "/visuels/login-sport.jpg", "/visuels/login-beaute.jpg", "/visuels/login-atelier.jpg", "/visuels/promo-partenaires.jpg"].map((src, index) => (
                    <img key={`${src}-${index}`} src={src} alt="" />
                  ))}
                </div>
              </div>
              <section className="card dash-block">
                <h2>Une semaine, en euros</h2>
                <RevenueCalculator />
              </section>
              <section className="card dash-block">
                <h2>Questions avant d’ouvrir le compte</h2>
                <PartnerFaq />
              </section>
            </>
          )}
          {current.id === "planning" && (
            <section className="card dash-block">
              <h2>Places à remplir</h2>
              <p className="muted">Exemple de journée. Après la connexion, ce sont vos horaires et vos places.</p>
              <ul className="slot-list">
                {SLOTS.map((slot) => (
                  <li key={slot.time}>
                    <strong>{slot.time}</strong>
                    <span>{slot.title}</span>
                    <small>{slot.meta}</small>
                  </li>
                ))}
              </ul>
            </section>
          )}
          {current.id === "scanner" && (
            <section className="card dash-block">
              <h2>Le passage</h2>
              <ol className="plain-steps">
                <li>Le membre réserve dans l’application.</li>
                <li>Il présente son QR code à l’arrivée.</li>
                <li>Vous scannez. La visite entre dans le règlement de la semaine.</li>
              </ol>
            </section>
          )}
          {current.id === "prestations" && (
            <section className="card dash-block">
              <h2>Le catalogue dans l’application</h2>
              <ul className="slot-list">
                <li><strong>1</strong><span>Accès libre</span><small>1 crédit · la durée que vous indiquez</small></li>
                <li><strong>2</strong><span>Séance ou soin</span><small>Le prix en crédits s’affiche sous le nom</small></li>
                <li><strong>Photo</strong><span>Une image par prestation</span><small>Elle apparaît sur la fiche du membre</small></li>
              </ul>
            </section>
          )}
          {current.id === "evenements" && (
            <section className="card dash-block">
              <h2>Un horaire, un prix, une affiche</h2>
              <p>Vous créez l’événement, le nombre de crédits et le créneau. Il s’affiche dans l’application pour les membres, le temps qu’il est publié.</p>
            </section>
          )}
          {current.id === "reglements" && (
            <section className="card dash-block">
              <h2>Ce que vous recevez</h2>
              <p>Chaque visite validée est versée après la clôture de la semaine. La commission de 10 % est déduite. Rien n’est viré tant que le compte de versement n’est pas enregistré.</p>
              <RevenueCalculator />
            </section>
          )}
          {current.id === "statistiques" && (
            <section className="card dash-block">
              <h2>La fréquentation réelle</h2>
              <p>Visites scannées, crédits utilisés, clients différents, annulations et net pour vous. Les graphiques portent sur 7, 30, 90 jours ou un an.</p>
            </section>
          )}
          {current.id === "equipe" && (
            <section className="card dash-block">
              <h2>Qui accueille</h2>
              <p>Les personnes de l’établissement peuvent valider un passage. Le responsable voit les règlements et les statistiques.</p>
            </section>
          )}
          {current.id === "messages" && (
            <section className="card dash-block">
              <h2>Les échanges après une demande</h2>
              <p>Un membre qui a réservé peut écrire. Vous répondez depuis cette section, une fois le compte ouvert.</p>
            </section>
          )}
          {current.id === "avis" && (
            <section className="card dash-block">
              <h2>Les retours après la visite</h2>
              <p>L’avis arrive une fois le passage validé. Il reste attaché à l’établissement.</p>
            </section>
          )}
          {current.id === "etablissement" && (
            <section className="card dash-block">
              <h2>La fiche vue par les membres</h2>
              <p>Adresse, photos, horaires et activité. Tant que le dossier n’est pas publié, l’établissement reste invisible dans l’application.</p>
            </section>
          )}
          <div className="dash-enter">
            <a className="btn primary" href={enter}>{label}</a>
            <a className="btn outline" href="/#demarrer">Demander un accès</a>
          </div>
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
