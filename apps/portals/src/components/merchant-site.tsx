import { ArrowRight, BadgeCheck, CalendarDays, QrCode, Wallet } from "lucide-react";

const OFFERS = [
  { image: "/visuels/login-sport.jpg", title: "Sport", text: "Salles, cours et bassins réservés en crédits." },
  { image: "/visuels/login-atelier.jpg", title: "Culture", text: "Ateliers, musées et scènes ouverts aux membres." },
  { image: "/visuels/login-beaute.jpg", title: "Beauté", text: "Soins et instituts, avec un passage simple." },
];

const STEPS = [
  { icon: BadgeCheck, title: "Votre établissement", text: "SIRET vérifié, adresse placée sur la carte." },
  { icon: CalendarDays, title: "Vos prestations", text: "Photos, prix en crédits et horaires depuis le portail." },
  { icon: QrCode, title: "Le passage", text: "Le membre présente son QR code, vous validez." },
  { icon: Wallet, title: "Le règlement", text: "Chaque prestation confirmée est suivie dans votre espace." },
];

/** Site commerçant public : visible sans compte, connexion dans l'en-tête. */
export function MerchantSite({ signedIn }: { signedIn: boolean }) {
  return (
    <main className="partner-landing marketing merchant-site">
      <header className="site-header">
        <a href="/" aria-label="XPASS, accueil commerçant">
          <img src="/logo.png" alt="XPASS" />
        </a>
        <nav className="site-nav" aria-label="Site commerçant">
          <a href="#offre">Offre</a>
          <a href="#parcours">Parcours</a>
          <a href="/devenir-partenaire">Rejoindre</a>
        </nav>
        <a className="btn primary" href={signedIn ? "/partner" : "/login"}>
          {signedIn ? "Mon espace" : "Connexion"}
        </a>
      </header>

      <section className="landing-hero">
        <img className="landing-hero-bg" src="/visuels/promo-partenaires.jpg" alt="" />
        <div className="landing-hero-copy">
          <p className="brand-mark">XPASS</p>
          <h1>Le site des commerçants du réseau</h1>
          <p className="lead">
            Sport, culture, beauté et sorties. Les membres réservent avec leurs crédits. Vous accueillez, vous validez, vous êtes réglés.
          </p>
          <div className="landing-actions">
            <a className="btn primary" href="/devenir-partenaire">
              Rejoindre le réseau <ArrowRight size={18} aria-hidden />
            </a>
            <a className="btn outline" href="/login">
              Connexion
            </a>
          </div>
        </div>
      </section>

      <div className="landing-body">
        <section id="offre">
          <p className="eyebrow">Visible sans compte</p>
          <h2 style={{ marginTop: 10 }}>Ce que les membres viennent réserver</h2>
          <div className="offer-grid">
            {OFFERS.map((offer) => (
              <article key={offer.title} className="offer-card">
                <img src={offer.image} alt="" />
                <div>
                  <h3>{offer.title}</h3>
                  <p className="muted">{offer.text}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section id="parcours">
          <p className="eyebrow">Parcours</p>
          <h2 style={{ marginTop: 10 }}>De la candidature au premier client</h2>
          <ol className="landing-steps">
            {STEPS.map(({ icon: Icon, title, text }, i) => (
              <li key={title}>
                <span className="step-n" aria-hidden>
                  {i + 1}
                </span>
                <div>
                  <strong>
                    <Icon size={18} aria-hidden /> {title}
                  </strong>
                  <p className="muted" style={{ marginTop: 4 }}>
                    {text}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </section>
      </div>

      <footer className="site-footer">
        <span>© XPASS</span>
        <nav aria-label="Informations légales">
          <a href="/legal/confidentialite">Confidentialité</a>
          <a href="/legal/cgu">Conditions</a>
        </nav>
      </footer>
    </main>
  );
}
