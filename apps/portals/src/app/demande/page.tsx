import type { Metadata } from "next";

import { activityName } from "@/lib/activities";
import { SeoJsonLd, seoMetadata } from "@/lib/seo-server";

import { AccessForm } from "./form";

export async function generateMetadata(): Promise<Metadata> {
  return seoMetadata("/demande", { title: "Demander un accès" });
}

export default async function AccessRequestPage({ searchParams }: { searchParams: Promise<{ activite?: string; profil?: string }> }) {
  const { activite, profil } = await searchParams;
  const chosen = activityName(activite);
  const kind = profil === "commercant" || profil === "merchant" ? "merchant" : "rh";
  return (
    <main className="demande-page">
      <SeoJsonLd path="/demande" />
      <div className="demande-top">
        <a href="/" aria-label="XPASS">
          <img src="/logo.png" alt="XPASS" width={120} height={36} />
        </a>
        <a className="btn outline" href="/">Retour</a>
      </div>
      <p className="eyebrow" style={{ marginTop: 28 }}>Formulaire</p>
      <h1>Demander un accès</h1>
      <p className="muted">
        L’administrateur reçoit votre demande. S’il l’accepte, l’identifiant et le mot de passe sont envoyés à l’adresse indiquée, celle de l’entreprise ou un Gmail.
        Un service RH remet ensuite l’identifiant de ses commerçants. Un commerçant publié apparaît dans l’application.
      </p>
      {chosen && <p className="notice mint">Activité choisie : <strong>{chosen}</strong></p>}
      <AccessForm activity={activite} kind={kind} />
    </main>
  );
}
