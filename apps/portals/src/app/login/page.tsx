import { ArrowRight, Building2, CircleHelp, Lock, ShieldCheck, Store } from "lucide-react";
import type { Metadata } from "next";

import { oidcConfigured } from "@/lib/oidc";
import { NETWORK_LINE } from "@/lib/roles";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Connexion" };

const ERRORS: Record<string, string> = {
  forbidden: "Votre compte n’a pas accès à cet espace.",
  acces: "Ce compte n’a accès à aucun portail professionnel. Commerçant ? Déposez votre candidature ci-dessous.",
  annule: "Connexion annulée.",
  etat: "La connexion a expiré ou n’est pas valide. Réessayez.",
  refus: "Connexion refusée par le fournisseur d’identité ou l’API.",
  oidc: "La connexion sécurisée n’est pas configurée.",
};

const SPACES = [
  { icon: ShieldCheck, label: "Admin" },
  { icon: Building2, label: "RH" },
  { icon: Store, label: "Commerçant" },
];

const UNIVERSES = ["Sport", "Culture", "Beauté", "Sorties"];

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ error?: string; erreur?: string }> }) {
  const { error, erreur } = await searchParams;
  const code = erreur ?? error ?? "";
  const message = ERRORS[code];
  const oidc = oidcConfigured();
  const demo = process.env.NODE_ENV !== "production" && process.env.PORTAL_DEV_LOGIN === "true";
  const support = process.env.SUPPORT_EMAIL;
  const helpHref = support ? `mailto:${support}` : "/legal/mentions-legales";
  return (
    <div className="login">
      <div className="login-stage">
        <img className="login-stage-bg" src="/visuels/login-sport.jpg" alt="" />
        <header className="login-header">
          <img src="/logo.png" alt="XPASS" className="login-logo" />
          <a className="login-help" href={helpHref}>
            <CircleHelp size={18} aria-hidden /> Aide
          </a>
        </header>

        <main className="login-hero">
          <section>
            <p className="login-brand" aria-hidden>
              XPASS
            </p>
            <h1 className="login-title">Un pass. Toutes vos envies.</h1>
            <p className="login-sub">{NETWORK_LINE}</p>
            <ul className="login-universes" aria-label="Univers">
              {UNIVERSES.map((u) => (
                <li key={u}>{u}</li>
              ))}
            </ul>
          </section>

          <section className="login-panel">
            <h2>Espace pro</h2>
            <p className="muted">Un compte pour Admin, RH et commerçants.</p>
            <ul className="login-spaces" aria-label="Espaces disponibles">
              {SPACES.map(({ icon: Icon, label }) => (
                <li key={label}>
                  <Icon size={18} aria-hidden /> {label}
                </li>
              ))}
            </ul>
            {message && (
              <p className={code === "annule" ? "login-alert info" : "login-alert"} role="alert">
                {message}
              </p>
            )}
            {!oidc && !demo && (
              <p className="login-alert" role="alert">
                La connexion sécurisée n’est pas encore publiée sur cette adresse. Sur cet ordinateur, ouvrez la plateforme locale.
              </p>
            )}
            {!oidc && !demo && (
              <a className="btn primary login-cta" href="http://localhost:3080/login">
                Ouvrir la plateforme <ArrowRight size={18} aria-hidden />
              </a>
            )}
            {oidc && (
              <>
                <a className="btn primary login-cta" href="/auth/login?suite=inscription">
                  Continuer avec Google <ArrowRight size={18} aria-hidden />
                </a>
                <a className="btn outline login-cta" href="/auth/login?methode=email&suite=inscription">
                  Continuer avec un e-mail
                </a>
                <a className="btn ghost login-cta" href="/auth/login?methode=email&creer=1&suite=inscription">
                  Créer un compte avec un e-mail
                </a>
                <p className="login-secure">
                  <Lock size={14} aria-hidden /> Le mot de passe est saisi sur la page sécurisée. Un e-mail de confirmation est envoyé pour un nouveau compte.
                </p>
              </>
            )}
            {demo && (
              <>
                <LoginForm />
                <div className="notice">
                  <span aria-hidden>ⓘ</span>
                  <span>
                    <strong>Mode démonstration.</strong> Connexion sans mot de passe réservée aux comptes de démo.
                  </span>
                </div>
              </>
            )}
            <p className="login-partner">
              Commerçant ?{" "}
              <a href="/devenir-partenaire">
                Rejoindre le réseau <ArrowRight size={16} aria-hidden />
              </a>
            </p>
          </section>
        </main>

        <footer className="login-footer">
          <span>© XPASS</span>
          <nav aria-label="Informations légales">
            <a href="/legal/confidentialite">Confidentialité</a>
            <span aria-hidden>·</span>
            <a href="/legal/cgu">Conditions</a>
          </nav>
        </footer>
      </div>
    </div>
  );
}
