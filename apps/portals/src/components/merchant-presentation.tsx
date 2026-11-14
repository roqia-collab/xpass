import { ArrowRight, CalendarDays, QrCode, Sparkles, Wallet } from "lucide-react";

import { PartnerFaq, PartnerStart, RevenueCalculator } from "@/components/partner-public";

const WHY = [
  { title: "Remplissez les places libres", text: "Les membres réservent les créneaux que vous publiez. Une place vide devient une visite." },
  { title: "Gardez votre clientèle", text: "Vous décidez du nombre de places ouvertes à XPASS. Vos rendez-vous habituels restent les vôtres." },
  { title: "Accueillez de nouveaux visages", text: "Des particuliers et des salariés d’entreprises arrivent par l’application, déjà décidés à réserver." },
];

const STEPS = [
  { n: "01", title: "Envoyez vos informations", text: "Établissement, activité, adresse de l’entreprise. L’admin valide la demande." },
  { n: "02", title: "Ouvrez le tableau de bord", text: "Prestations, photos, planning, événements. Ce que vous publiez apparaît dans l’application." },
  { n: "03", title: "Encaissez les visites", text: "Le membre montre son QR code. Vous scannez. Le règlement part après la semaine." },
];

const FACTS = [
  { value: "4", label: "univers : sport, culture, beauté, sorties" },
  { value: "1 €", label: "brut par crédit, payé par le membre" },
  { value: "10 %", label: "de commission, prélevée sur la visite validée" },
  { value: "Paris", label: "est la ville ouverte aujourd’hui" },
];

const TOOLS = [
  { href: "/tableau?section=planning", icon: CalendarDays, title: "Planning", text: "Les places que vous ouvrez, jour par jour." },
  { href: "/tableau?section=scanner", icon: QrCode, title: "Scanner", text: "La validation du passage, au comptoir." },
  { href: "/tableau?section=prestations", icon: Sparkles, title: "Prestations", text: "Le prix en crédits, la durée, la photo." },
  { href: "/tableau?section=reglements", icon: Wallet, title: "Règlements", text: "Le net à recevoir, commission déduite." },
];

/** Présentation du site commerçant, avant le tableau de bord. */
export function MerchantPresentation({ signedIn, partner = false }: { signedIn: boolean; partner?: boolean }) {
  const enter = partner ? "/partner" : signedIn ? "/inscription-partenaire" : "/login?espace=1";
  const label = partner ? "Mon espace" : "Se connecter";
  return (
    <div className="partners">
      <header className="partners-header">
        <a href="/" aria-label="XPASS, accueil">
          <img src="/logo.png" alt="XPASS" />
        </a>
        <nav className="partners-nav" aria-label="Présentation">
          <a href="#concept">Notre concept</a>
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
          <p className="eyebrow">Commerçants · Paris</p>
          <h1>Vous accueillez déjà. XPASS remplit les places libres.</h1>
          <p>Les membres réservent en crédits. Vous gardez vos clients habituels, vous validez le QR code, vous êtes réglé chaque semaine.</p>
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

      <section className="partners-why" id="pourquoi">
        <div className="partners-why-copy">
          <p className="eyebrow">Pourquoi XPASS</p>
          <h2>Une place vide ne rapporte rien.</h2>
          <p>XPASS envoie des membres vers les créneaux que vous choisissez d’ouvrir. Le reste de votre journée ne change pas.</p>
        </div>
        <div className="partners-why-grid">
          {WHY.map((item) => (
            <article key={item.title}>
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="partners-steps" id="concept">
        <p className="eyebrow">Notre concept</p>
        <h2>Trois étapes, de la demande au règlement.</h2>
        <ol>
          {STEPS.map((step) => (
            <li key={step.n}>
              <span>{step.n}</span>
              <strong>{step.title}</strong>
              <p>{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="partners-facts" aria-label="Repères">
        {FACTS.map((fact) => (
          <article key={fact.value}>
            <strong>{fact.value}</strong>
            <p>{fact.label}</p>
          </article>
        ))}
      </section>

      <section className="partners-calc" id="calculateur">
        <div>
          <p className="eyebrow">Calculateur</p>
          <h2>Estimez ce que les visites peuvent rapporter.</h2>
          <p>1 crédit = 1,00 € brut. Vous gardez 90 %. Le chiffre bouge avec le nombre de passages réellement scannés.</p>
        </div>
        <RevenueCalculator />
      </section>

      <section className="partners-tools" id="outils">
        <div>
          <p className="eyebrow">Tableau de bord</p>
          <h2>Tout le quotidien de l’établissement.</h2>
        </div>
        <div>
          {TOOLS.map(({ href, icon: Icon, title, text }) => (
            <a key={href} href={href}>
              <Icon size={20} aria-hidden />
              <strong>{title}</strong>
              <span>{text}</span>
            </a>
          ))}
        </div>
      </section>

      <section className="partners-faq" id="questions">
        <p className="eyebrow">Questions</p>
        <h2>Avant d’ouvrir le compte.</h2>
        <PartnerFaq />
      </section>

      <section className="partners-rh">
        <img src="/visuels/salaries.jpg" alt="" />
        <div>
          <p className="eyebrow">Entreprises</p>
          <h2>Les salariés arrivent par leur service RH.</h2>
          <p>Une entreprise ouvre XPASS pour ses équipes. Ses salariés réservent chez vous avec leurs crédits. Vous voyez la visite, pas la paie de l’entreprise.</p>
          <a className="btn primary" href="/demande?profil=rh">Devenir un service RH</a>
        </div>
      </section>

      <section className="partners-cta">
        <h2>Vous voulez remplir vos prochains créneaux ?</h2>
        <p>Le compte s’ouvre sans frais. La commission arrive seulement quand une visite est validée.</p>
        <a className="btn primary" href="#demarrer">Démarrer</a>
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
