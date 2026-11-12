import { ArrowRight, BadgeCheck, QrCode, Sparkles, Wallet } from "lucide-react";

const WORLDS = [
  { image: "/visuels/login-sport.jpg", title: "Sport", text: "Cours, salles et bassins réservés en crédits." },
  { image: "/visuels/login-atelier.jpg", title: "Culture", text: "Ateliers, musées et scènes ouverts aux membres." },
  { image: "/visuels/login-beaute.jpg", title: "Beauté", text: "Soins et instituts, avec un passage simple." },
  { image: "/visuels/promo-partenaires.jpg", title: "Sorties", text: "Lieux de la ville, du hammam à la salle de spectacle." },
];

const PATH = [
  { icon: BadgeCheck, title: "La fiche", text: "SIRET vérifié, adresse placée sur la carte, photos de l’établissement." },
  { icon: Sparkles, title: "Les prestations", text: "Prix en crédits, durée, horaires. Ce qui est publié apparaît chez le client." },
  { icon: QrCode, title: "Le passage", text: "Le membre présente son QR code. Vous validez en un geste." },
  { icon: Wallet, title: "Le règlement", text: "Chaque prestation confirmée est suivie dans votre espace." },
];

/** Présentation du site commerçant, avant le tableau de bord. */
export function MerchantPresentation({ signedIn }: { signedIn: boolean }) {
  const enter = signedIn ? "/partner" : "/login?espace=1";
  return (
    <div className="show">
      <header className="show-header">
        <a href="/" aria-label="XPASS, accueil">
          <img src="/logo.png" alt="XPASS" />
        </a>
        <nav className="show-nav" aria-label="Présentation">
          <a href="#offre">Offre</a>
          <a href="#parcours">Parcours</a>
          <a href="#reseau">Réseau</a>
          <a href="/tableau">Tableau de bord</a>
        </nav>
        <a className="btn primary" href={enter}>
          {signedIn ? "Mon espace" : "Connexion"}
        </a>
      </header>

      <section className="show-hero">
        <img src="/visuels/promo-partenaires.jpg" alt="" />
        <div className="show-hero-copy">
          <p className="eyebrow">Commerçants · Paris</p>
          <h1>Le réseau qui amène les membres jusqu’à votre porte.</h1>
          <p>
            Sport, culture, beauté et sorties. Ils réservent avec leurs crédits. Vous accueillez, vous validez, vous êtes réglés.
          </p>
          <div className="show-actions">
            <a className="btn primary" href="/tableau">
              Voir le tableau de bord <ArrowRight size={18} aria-hidden />
            </a>
            <a className="btn outline" href={enter}>
              {signedIn ? "Mon espace" : "Connexion"}
            </a>
          </div>
        </div>
      </section>

      <section className="show-intro" id="offre">
        <div>
          <p className="eyebrow">Le site</p>
          <h2>Une vitrine, puis votre tableau de bord.</h2>
        </div>
        <p>
          Cette page présente le réseau. Le tableau de bord qui suit montre les sections de votre établissement : planning, prestations, équipe, règlements. La connexion ouvre ensuite votre espace de travail.
        </p>
      </section>

      <section className="show-worlds" aria-label="Univers">
        {WORLDS.map((world) => (
          <article key={world.title}>
            <img src={world.image} alt="" />
            <div>
              <h3>{world.title}</h3>
              <p>{world.text}</p>
            </div>
          </article>
        ))}
      </section>

      <section className="show-path" id="parcours">
        <p className="eyebrow">Parcours</p>
        <h2>De la candidature au premier client</h2>
        <ol>
          {PATH.map(({ icon: Icon, title, text }, index) => (
            <li key={title}>
              <span>{index + 1}</span>
              <Icon size={20} aria-hidden />
              <strong>{title}</strong>
              <p>{text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="show-band" id="reseau">
        <img src="/visuels/login-sport.jpg" alt="" />
        <div>
          <p className="eyebrow">Le réseau</p>
          <h2>Admin, RH, commerçant, application.</h2>
          <p>
            L’admin ouvre le service RH. Le RH ajoute ses commerçants. Leurs prestations publiées apparaissent dans l’application client.
          </p>
          <a className="btn primary" href="/devenir-partenaire">
            Rejoindre le réseau <ArrowRight size={18} aria-hidden />
          </a>
        </div>
      </section>

      <footer className="show-footer">
        <div>
          <img src="/logo.png" alt="XPASS" />
          <p>Le pass crédits du sport, de la culture, de la beauté et des sorties.</p>
        </div>
        <nav aria-label="Pied de page">
          <a href="#offre">Offre</a>
          <a href="#parcours">Parcours</a>
          <a href="/tableau">Tableau de bord</a>
          <a href={enter}>{signedIn ? "Mon espace" : "Connexion"}</a>
        </nav>
        <nav aria-label="Informations légales">
          <a href="/legal/confidentialite">Confidentialité</a>
          <a href="/legal/cgu">Conditions</a>
          <a href="/legal/mentions-legales">Mentions</a>
        </nav>
        <small>© XPASS</small>
      </footer>
    </div>
  );
}
