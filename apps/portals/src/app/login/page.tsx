import { ArrowRight, Building2, CircleHelp, Lock, ShieldCheck, Store } from "lucide-react";
import type { Metadata } from "next";
import { headers } from "next/headers";

import { LoginForm } from "./login-form";
import { AdminLoginForm } from "./admin-form";

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<{ porte?: string }>;
}): Promise<Metadata> {
  const { porte } = await searchParams;
  return { title: (await face(porte)).meta };
}

const ERRORS: Record<string, string> = {
  forbidden: "Votre compte n’a pas accès à cet espace.",
  acces: "Ce compte n’a accès à aucun portail professionnel. Commerçant ? Déposez votre candidature ci-dessous.",
  annule: "Connexion annulée.",
  etat: "La connexion a expiré ou n’est pas valide. Réessayez.",
  refus: "Connexion refusée par le fournisseur d’identité ou l’API.",
};

type Door = "xpass" | "admin" | "rh";

const FACES: Record<
  Door,
  {
    meta: string;
    klass: string;
    image: string;
    word: string;
    kicker: string;
    title: string;
    text: string;
    pills: string[];
    panel: string;
    panelText: string;
    role: string;
    icon: typeof Store;
    suite: "inscription" | "espace" | "admin" | "rh" | null;
    join: boolean;
    ask: boolean;
  }
> = {
  xpass: {
    meta: "Connexion commerçant",
    klass: "login-xpass",
    image: "/visuels/login-sport.jpg",
    word: "XPASS",
    kicker: "Commerçants · Paris",
    title: "Jusqu’à votre porte.",
    text: "Ils réservent en crédits. Vous accueillez, vous validez, vous êtes réglés.",
    pills: ["Sport", "Culture", "Beauté", "Sorties"],
    panel: "Espace commerçant",
    panelText: "Votre vitrine, puis votre espace de travail.",
    role: "Commerçant",
    icon: Store,
    suite: "inscription",
    join: true,
    ask: true,
  },
  admin: {
    meta: "Connexion administration",
    klass: "login-admin",
    image: "/visuels/promo-administration.jpg",
    word: "ADMIN",
    kicker: "Administration",
    title: "Le réseau, sous vos yeux.",
    text: "Entrez l’identifiant d’origine, ou le Gmail d’un admin que vous avez créé.",
    pills: ["Réseau", "Comptes", "Contrôle"],
    panel: "Administration",
    panelText: "Réservé à l’équipe XPASS.",
    role: "Équipe XPASS",
    icon: ShieldCheck,
    suite: "admin",
    join: false,
    ask: false,
  },
  rh: {
    meta: "Connexion RH",
    klass: "login-rh",
    image: "/visuels/factures.jpg",
    word: "RH",
    kicker: "Ressources humaines",
    title: "Vos équipes. Leurs envies.",
    text: "Ajoutez vos commerçants. Leurs prestations publiées arrivent dans l’application.",
    pills: ["Équipes", "Crédits", "Établissements"],
    panel: "Espace RH",
    panelText: "Le service qui ouvre les commerçants de l’entreprise.",
    role: "Service RH",
    icon: Building2,
    suite: "rh",
    join: false,
    ask: true,
  },
};

async function face(porte: string | undefined) {
  const host = ((await headers()).get("x-forwarded-host") ?? (await headers()).get("host") ?? "")
    .split(",")[0]
    .trim()
    .toLowerCase()
    .replace(/:\d+$/, "");
  const door: Door = host === "admin.xpass.fr" || porte === "admin" ? "admin" : host === "rh.xpass.fr" || porte === "rh" ? "rh" : "xpass";
  return FACES[door];
}

function authHref(kind: "google" | "email" | "create", suite: "inscription" | "espace" | "admin" | "rh" | null) {
  const params = new URLSearchParams();
  if (suite) params.set("suite", suite);
  if (kind !== "google") params.set("methode", "email");
  if (kind === "create") params.set("creer", "1");
  const q = params.toString();
  return q ? `/auth/login?${q}` : "/auth/login";
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; erreur?: string; espace?: string; porte?: string }>;
}) {
  const { error, erreur, espace, porte } = await searchParams;
  const view = await face(porte);
  const suite = view.suite === "inscription" && espace === "1" ? "espace" : view.suite;
  const code = erreur ?? error ?? "";
  const message = ERRORS[code];
  const demo = process.env.NODE_ENV !== "production" && process.env.PORTAL_DEV_LOGIN === "true";
  const support = process.env.SUPPORT_EMAIL;
  const helpHref = support ? `mailto:${support}` : "/legal/mentions-legales";
  const Icon = view.icon;
  return (
    <div className={`login ${view.klass}`}>
      <div className="login-stage">
        <img className="login-stage-bg" src={view.image} alt="" />
        <header className="login-header">
          <img src="/logo.png" alt="XPASS" className="login-logo" />
          <a className="login-help" href={helpHref}>
            <CircleHelp size={18} aria-hidden /> Aide
          </a>
        </header>

        <main className="login-hero">
          <section>
            <p className="login-kicker">{view.kicker}</p>
            <p className="login-brand" aria-hidden>
              {view.word}
            </p>
            <h1 className="login-title">{view.title}</h1>
            <p className="login-sub">{view.text}</p>
            <ul className="login-universes" aria-label="Repères">
              {view.pills.map((u) => (
                <li key={u}>{u}</li>
              ))}
            </ul>
          </section>

          <section className="login-panel">
            <h2>{view.panel}</h2>
            <p className="muted">{view.panelText}</p>
            <ul className="login-spaces" aria-label="Espace">
              <li>
                <Icon size={18} aria-hidden /> {view.role}
              </li>
            </ul>
            {message && (
              <p className={code === "annule" ? "login-alert info" : "login-alert"} role="alert">
                {message}
              </p>
            )}
            {view.suite === "admin" ? (
              <AdminLoginForm />
            ) : (
              <>
                <a className="btn primary login-cta" href={authHref("google", suite)}>
                  Continuer avec Google <ArrowRight size={18} aria-hidden />
                </a>
                <a className="btn outline login-cta" href={authHref("email", suite)}>
                  Continuer avec un e-mail
                </a>
                {view.join && (
                  <a className="btn ghost login-cta" href={authHref("create", suite)}>
                    Créer un compte avec un e-mail
                  </a>
                )}
              </>
            )}
            <p className="login-secure">
              <Lock size={14} aria-hidden />{" "}
              {view.suite === "admin"
                ? "L’admin d’origine entre avec son identifiant. Les autres admins entrent avec leur Gmail."
                : "L’identifiant est le Gmail. Le mot de passe, remis par l’administrateur ou le RH, se saisit avec « Continuer avec un e-mail »."}
            </p>
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
            {view.ask && (
              <p className="login-partner">
                Pas encore de compte ? <a href="/demande">Remplir le formulaire d’accès</a>
              </p>
            )}
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
