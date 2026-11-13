import { ArrowRight, BadgeCheck, QrCode, Sparkles, Wallet } from "lucide-react";

const WORLDS = [
  { slug: "sport", image: "/visuels/login-sport.jpg", kicker: "01", title: "Sport", text: "Cours, salles et bassins." },
  { slug: "culture", image: "/visuels/login-atelier.jpg", kicker: "02", title: "Culture", text: "Ateliers, musées, scènes." },
  { slug: "beaute", image: "/visuels/login-beaute.jpg", kicker: "03", title: "Beauté", text: "Soins et instituts." },
  { slug: "sorties", image: "/visuels/promo-partenaires.jpg", kicker: "04", title: "Sorties", text: "Hammams, salles, la ville." },
];

const PATH = [
  { icon: BadgeCheck, title: "La fiche", text: "SIRET vérifié, adresse sur la carte, photos du lieu." },
  { icon: Sparkles, title: "Les prestations", text: "Prix en crédits, durée, horaires. Publié chez le client." },
  { icon: QrCode, title: "Le passage", text: "Le membre montre son QR code. Vous validez." },
  { icon: Wallet, title: "Le règlement", text: "Chaque prestation confirmée est suivie dans votre espace." },
];

const TICKER = ["Sport", "Culture", "Beauté", "Sorties", "Crédits", "QR code", "Paris"];

/** Présentation du site commerçant, avant le tableau de bord. */
export function MerchantPresentation({ signedIn, partner = false }: { signedIn: boolean; partner?: boolean }) {
  const enter = partner ? "/partner" : signedIn ? "/inscription-partenaire" : "/login?espace=1";
  const label = partner ? "Mon espace" : signedIn ? "Mon dossier" : "Connexion";
  const loop = [...TICKER, ...TICKER];
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
          {label}
        </a>
      </header>

      <section className="show-hero">
        <img src="/visuels/promo-partenaires.jpg" alt="" />
        <p className="show-mark" aria-hidden>XPASS</p>
        <div className="show-hero-copy">
          <p className="eyebrow">Commerçants · Paris</p>
          <h1>Jusqu’à votre porte.</h1>
          <p>Ils réservent en crédits. Vous accueillez, vous validez, vous êtes réglés.</p>
          <div className="show-actions">
            <a className="btn primary" href="/tableau">
              Tableau de bord <ArrowRight size={18} aria-hidden />
            </a>
            <a className="btn outline" href={enter}>
              {label}
            </a>
          </div>
        </div>
        <div className="show-ticker" aria-hidden>
          <div>
            {loop.map((word, index) => (
              <span key={`${word}-${index}`}>{word}</span>
            ))}
          </div>
        </div>
      </section>

      <section className="show-stage" id="offre">
        <div className="show-stage-copy">
          <p className="eyebrow">L’offre</p>
          <h2>Quatre univers. Un seul pass.</h2>
          <p>La vitrine présente le réseau. Le tableau de bord ouvre les sections de votre établissement. La connexion mène à votre espace de travail.</p>
        </div>
        <div className="show-mosaic">
          {WORLDS.map((world) => (
            <a key={world.slug} href={`/demande?activite=${world.slug}`} aria-label={`Choisir ${world.title}`}>
              <img src={world.image} alt="" />
              <div>
                <small>{world.kicker}</small>
                <h3>{world.title}</h3>
                <p>{world.text}</p>
                <span>Choisir {world.title}</span>
              </div>
            </a>
          ))}
        </div>
      </section>

      <section className="show-path" id="parcours">
        <p className="eyebrow">Parcours</p>
        <h2>Quatre gestes, du dossier au règlement.</h2>
        <ol>
          {PATH.map(({ icon: Icon, title, text }, index) => (
            <li key={title}>
              <span>0{index + 1}</span>
              <Icon size={18} aria-hidden />
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
          <h2>Admin. RH. Commerçant. Application.</h2>
          <p>L’admin ouvre le service RH. Le RH ajoute ses commerçants. Leurs prestations publiées apparaissent dans l’application client.</p>
          <a className="btn primary" href="/devenir-partenaire">
            Rejoindre le réseau <ArrowRight size={18} aria-hidden />
          </a>
          <a className="btn outline" href="/demande" style={{ marginLeft: 12 }}>
            Demander un accès
          </a>
        </div>
      </section>

      <footer className="show-footer">
        <p className="show-footer-mark">XPASS</p>
        <p>Le pass crédits du sport, de la culture, de la beauté et des sorties.</p>
        <nav aria-label="Pied de page">
          <a href="#offre">Offre</a>
          <a href="#parcours">Parcours</a>
          <a href="/tableau">Tableau de bord</a>
          <a href="/demande">Demander un accès</a>
          <a href={enter}>{label}</a>
        </nav>
        <nav aria-label="Informations légales">
          <a href="/legal/confidentialite">Confidentialité</a>
          <a href="/legal/cgu">Conditions</a>
          <a href="/legal/mentions-legales">Mentions</a>
        </nav>
        <small>© XPASS · Paris</small>
      </footer>
    </div>
  );
}
