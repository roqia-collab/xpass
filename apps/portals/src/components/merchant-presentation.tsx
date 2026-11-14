import { ArrowRight, Handshake, List, Megaphone } from "lucide-react";

import { PartnerFaq, PartnerStart, RevenueCalculator } from "@/components/partner-public";

const WORDS = ["Sport", "Culture", "Beauté", "Sorties", "Crédits", "QR code", "Paris"];

const FRAMES = [
  { src: "/visuels/login-sport.jpg", title: "Sport", href: "/demande?activite=sport" },
  { src: "/visuels/login-beaute.jpg", title: "Beauté", href: "/demande?activite=beaute" },
  { src: "/visuels/login-atelier.jpg", title: "Culture", href: "/demande?activite=culture" },
  { src: "/visuels/promo-partenaires.jpg", title: "Sorties", href: "/demande?activite=sorties" },
];

const CONCEPT = [
  {
    icon: List,
    title: "Envoyez vos informations",
    text: "Le formulaire dit qui vous êtes, le nom de l’établissement et l’activité. C’est ce qui ouvre le compte.",
  },
  {
    icon: Handshake,
    title: "Commencez à utiliser XPASS",
    text: "Après validation, la fiche est prête : planning, prestations, photos et scanner. Vous n’ouvrez que les places à remplir.",
  },
  {
    icon: Megaphone,
    title: "Générez des revenus",
    text: "Les membres réservent ces places et paient en crédits. Vous scannez au comptoir. Chaque semaine, 0,90 € par crédit vous sont versés.",
  },
];

const FLOW = [
  { n: "01", title: "La demande", text: "Le formulaire, avec l’adresse de l’entreprise.", href: "#demarrer", image: "/visuels/promo-partenaires.jpg", label: "Écrire" },
  { n: "02", title: "La validation", text: "L’e-mail apporte l’identifiant et le mot de passe.", href: "mailto:support@xpass.fr", image: "/visuels/factures.jpg", label: "Une question" },
  { n: "03", title: "La porte", text: "Commerçant sur xpass.fr. Service RH sur rh.xpass.fr.", href: "/login?espace=1", image: "/visuels/salaries.jpg", label: "Se connecter" },
  { n: "04", title: "Le tableau", text: "Places, crédits, photo, scan. Vous publiez.", href: "/tableau", image: "/visuels/login-sport.jpg", label: "Ouvrir" },
  { n: "05", title: "L’application", text: "Le membre réserve. La visite se scanne au comptoir.", href: "https://app.xpass.fr", image: "/visuels/login-beaute.jpg", label: "Voir l’app" },
];

/** Présentation du site commerçant, avant le tableau de bord. */
export function MerchantPresentation({ signedIn, partner = false }: { signedIn: boolean; partner?: boolean }) {
  const enter = partner ? "/partner" : signedIn ? "/inscription-partenaire" : "/login?espace=1";
  const label = partner ? "Mon espace" : "Se connecter";
  const words = [...WORDS, ...WORDS];
  const frames = [...FRAMES, ...FRAMES];
  return (
    <div className="partners">
      <header className="partners-header">
        <a href="/" aria-label="XPASS, accueil">
          <img src="/logo.png" alt="XPASS" />
        </a>
        <nav className="partners-nav" aria-label="Présentation">
          <a href="#concept">Notre concept</a>
          <a href="#parcours">Le flux</a>
          <a href="#calculateur">Calculateur</a>
          <a href="#questions">Questions</a>
          <a href="/tableau">Tableau de bord</a>
        </nav>
        <div className="partners-header-actions">
          <a className="btn ghost" href={enter}>{label}</a>
          <a className="btn primary" href="#demarrer">Démarrer</a>
        </div>
      </header>

      <section className="partners-hero">
        <div className="partners-lead">
          <p className="lead-mark" aria-hidden>XPASS</p>
          <p className="eyebrow">Commerçants · Paris</p>
          <h1>
            <span>Les places</span>
            <span>vides ont</span>
            <span>un prix.</span>
          </h1>
          <p>Vous ouvrez le créneau. Le membre paie en crédits. Vous scannez, le règlement part en fin de semaine.</p>
          <ul className="lead-facts">
            <li><strong>1 €</strong><span>le crédit</span></li>
            <li><strong>10 %</strong><span>retenus</span></li>
            <li><strong>QR</strong><span>au comptoir</span></li>
          </ul>
          <div className="show-actions">
            <a className="btn primary" href="#demarrer">Démarrer <ArrowRight size={18} aria-hidden /></a>
            <a className="btn outline" href="/tableau">Tableau de bord</a>
          </div>
        </div>
        <div className="partners-stage">
          <div className="partners-mosaic" aria-hidden>
            <img src="/visuels/login-sport.jpg" alt="" />
            <img src="/visuels/login-beaute.jpg" alt="" />
            <img src="/visuels/login-atelier.jpg" alt="" />
            <img src="/visuels/promo-partenaires.jpg" alt="" />
          </div>
          <PartnerStart />
        </div>
      </section>

      <div className="partners-ticker" aria-hidden>
        <div>
          {words.map((word, index) => <span key={`${word}-${index}`}>{word}</span>)}
        </div>
      </div>

      <section className="billboard" aria-labelledby="rejoindre">
        <p className="billboard-kicker">Rejoindre XPASS</p>
        <h2 id="rejoindre">Et si on avançait ensemble ?</h2>
        <div className="billboard-grid">
          <a className="billboard-card rh" href="/demande?profil=rh" style={{ backgroundImage: "url(/visuels/salaries.jpg)" }}>
            <span>Entreprises &amp; services RH</span>
            <strong>Le bien-être de vos équipes commence ici.</strong>
            <small>Sport, culture, beauté et sorties avec XPASS.</small>
            <em>Devenir partenaire RH</em>
          </a>
          <a className="billboard-card" href="/demande?profil=commercant" style={{ backgroundImage: "url(/visuels/promo-partenaires.jpg)" }}>
            <span>Commerçants &amp; établissements</span>
            <strong>Votre savoir-faire. De nouveaux clients.</strong>
            <small>Faites découvrir vos activités aux membres XPASS.</small>
            <em>Rejoindre le réseau</em>
          </a>
        </div>
        <p className="billboard-mail">Une question ? <a href="mailto:support@xpass.fr">support@xpass.fr</a></p>
      </section>

      <div className="partners-film" aria-label="Les quatre univers">
        <div>
          {frames.map((frame, index) => (
            <a key={`${frame.title}-${index}`} href={frame.href}>
              <img src={frame.src} alt="" />
              <strong>{frame.title}</strong>
            </a>
          ))}
        </div>
      </div>

      <section className="concept" id="concept">
        <h2>Notre concept</h2>
        <ol>
          {CONCEPT.map((step) => (
            <li key={step.title}>
              <step.icon size={36} strokeWidth={1.6} aria-hidden />
              <strong>{step.title}</strong>
              <p>{step.text}</p>
              {step.title.startsWith("Envoyez") && <a href="#demarrer">Remplir le formulaire</a>}
            </li>
          ))}
        </ol>
      </section>

      <section className="flux" id="parcours">
        <p className="eyebrow">Le flux</p>
        <h2>De la demande à l’application.</h2>
        <ol>
          {FLOW.map((step) => (
            <li key={step.n}>
              <a href={step.href}>
                <img src={step.image} alt="" />
                <span>
                  <em>{step.n}</em>
                  <strong>{step.title}</strong>
                  <small>{step.text}</small>
                  <b>{step.label}</b>
                </span>
              </a>
            </li>
          ))}
        </ol>
      </section>

      <section className="partners-calc" id="calculateur">
        <div className="partners-calc-photo" aria-hidden>
          <img src="/visuels/login-atelier.jpg" alt="" />
        </div>
        <div className="partners-calc-copy">
          <p className="eyebrow">Calculateur</p>
          <h2>Une semaine, en euros.</h2>
          <p>1 crédit vaut 1,00 €. Vous gardez 90 %. Le montant suit les passages scannés, rien d’autre.</p>
          <RevenueCalculator />
        </div>
      </section>

      <section className="partners-faq" id="questions">
        <p className="eyebrow">Questions</p>
        <h2>Avant d’ouvrir le compte.</h2>
        <PartnerFaq />
      </section>

      <footer className="partners-footer">
        <p className="partners-mark">XPASS</p>
        <nav aria-label="Partenaires">
          <strong>Partenaires</strong>
          <a href="#demarrer">Devenir commerçant</a>
          <a href="#calculateur">Calculateur</a>
          <a href="/tableau">Tableau de bord</a>
          <a href={enter}>{label}</a>
        </nav>
        <nav aria-label="Entreprises">
          <strong>Entreprises</strong>
          <a href="/demande?profil=rh">Devenir un service RH</a>
          <a href="https://rh.xpass.fr">Connexion RH</a>
          <a href="#questions">Questions</a>
        </nav>
        <nav aria-label="Assistance">
          <strong>Assistance</strong>
          <a href="mailto:support@xpass.fr">support@xpass.fr</a>
          <a href="/legal/cgu">Conditions</a>
          <a href="/legal/confidentialite">Confidentialité</a>
          <a href="/legal/mentions-legales">Mentions</a>
        </nav>
        <small>© XPASS · Paris</small>
      </footer>
    </div>
  );
}
