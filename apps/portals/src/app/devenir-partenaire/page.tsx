import { ArrowRight, BadgeCheck, CalendarDays, QrCode, Store, Users, Wallet } from "lucide-react";
import type { Metadata } from "next";

import { getMe } from "@/lib/session";

export const metadata: Metadata = { title: "Devenir partenaire" };

const STEPS = [
  { icon: Store, title: "Votre entreprise", text: "Votre SIRET est vérifié dans l’annuaire public des entreprises." },
  { icon: BadgeCheck, title: "Votre établissement", text: "Adresse placée sur la carte grâce à la Base Adresse Nationale." },
  { icon: CalendarDays, title: "Vos prestations", text: "Photos, prix en crédits, horaires et équipe, depuis le portail." },
  { icon: QrCode, title: "Validation XPASS", text: "Après vérification, vos clients réservent et présentent leur QR code." },
];

const BENEFITS = [
  { icon: Users, title: "De nouveaux clients", text: "Abonnés et salariés qui utilisent leurs crédits chez vous." },
  { icon: QrCode, title: "Un passage simple", text: "Le client présente son QR code, vous validez en un geste." },
  { icon: Wallet, title: "Des règlements suivis", text: "Chaque prestation confirmée vous est réglée dans le portail." },
];

/** Page publique : présentation du réseau et entrée du parcours d'inscription commerçant. */
export default async function BecomePartnerPage() {
  const me = await getMe();
  const start = me ? "/inscription-partenaire" : "/auth/login?suite=inscription";
  return (
    <main className="partner-landing marketing">
      <header className="landing-top">
        <a href="/login" aria-label="XPASS, portails professionnels">
          <img src="/logo.png" alt="XPASS" />
        </a>
        <a className="btn ghost" href="/login">
          Se connecter
        </a>
      </header>

      <section className="landing-hero">
        <img className="landing-hero-bg" src="/visuels/promo-partenaires.jpg" alt="" />
        <div className="landing-hero-copy">
          <p className="brand-mark">XPASS</p>
          <h1>Plus de clients pour vos talents</h1>
          <p className="lead">
            Sport, culture, beauté, sorties : les membres réservent avec des crédits. Vous accueillez, vous validez, vous
            êtes réglés.
          </p>
          <div className="landing-actions">
            <a className="btn primary" href={start}>
              {me ? "Continuer ma candidature" : "Créer mon compte"} <ArrowRight size={18} aria-hidden />
            </a>
            {!me && (
              <a className="btn outline" href="/auth/login?suite=inscription">
                J’ai déjà un compte
              </a>
            )}
          </div>
        </div>
      </section>

      <div className="landing-body">
        <section>
          <p className="eyebrow">Pourquoi rejoindre</p>
          <h2 style={{ marginTop: 10 }}>Un pass, des clients prêts à réserver</h2>
          <div className="grid grid-3" style={{ marginTop: 24 }}>
            {BENEFITS.map(({ icon: Icon, title, text }) => (
              <div key={title} className="card kpi" style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                <div className="icon" aria-hidden>
                  <Icon />
                </div>
                <div>
                  <h3>{title}</h3>
                  <p className="muted" style={{ marginTop: 6 }}>
                    {text}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section>
          <p className="eyebrow">Parcours</p>
          <h2 style={{ marginTop: 10 }}>Comment ça marche</h2>
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

        <p className="muted" style={{ fontSize: 13, textAlign: "center" }}>
          Munissez-vous de votre SIRET et de l’adresse de l’établissement. Les conditions commerciales sont présentées
          avant validation.
        </p>
      </div>
    </main>
  );
}
