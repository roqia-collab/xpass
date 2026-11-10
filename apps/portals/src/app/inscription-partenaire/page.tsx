import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { apiFetch, getMe } from "@/lib/session";
import { canAccess } from "@/lib/roles";

import { SignupForm, type CategoryOption } from "./signup-form";

export const metadata: Metadata = { title: "Inscription partenaire" };

/** Candidature d'un commerçant réel : compte XPASS requis, aucun espace professionnel nécessaire. */
export default async function PartnerSignupPage() {
  const me = await getMe();
  if (!me) redirect("/devenir-partenaire");
  if (canAccess(me, "partner")) redirect("/partner");
  const categories = await apiFetch<{ slug: string; name: string; subcategories: { slug: string; name: string }[] }[]>(
    "/catalog/categories",
  );
  const options: CategoryOption[] = categories.map((c) => ({ name: c.name, subs: c.subcategories.map((s) => ({ slug: s.slug, name: s.name })) }));
  return (
    <main className="partner-landing" style={{ maxWidth: 860 }}>
      <header className="landing-top">
        <a href="/devenir-partenaire" aria-label="Retour"><img src="/logo.png" alt="XPASS" style={{ height: 34 }} /></a>
        <span className="muted" style={{ fontSize: 14 }}>Connecté : {me.email}</span>
      </header>
      <div>
        <p className="eyebrow">Inscription partenaire</p>
        <h1>Votre établissement sur XPASS</h1>
        <p className="muted" style={{ fontSize: 17, marginTop: 10 }}>
          Deux étapes : votre entreprise, puis votre établissement. Votre dossier est ensuite vérifié par l’équipe XPASS ;
          vous pouvez compléter photos, prestations et horaires dès maintenant.
        </p>
      </div>
      <SignupForm categories={options} />
    </main>
  );
}
