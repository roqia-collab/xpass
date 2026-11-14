import { Badge, ErrorCard, PageHead } from "@/components/ui";
import { tryApi } from "@/lib/session";

import { OpenMerchant } from "./form";

export const metadata = { title: "Demandes commerçants" };

type RequestRow = {
  id: string;
  gmail: string;
  full_name: string;
  place_name: string;
  city: string;
  message: string;
  status: "pending" | "accepted" | "refused";
  created_at: string;
};

export default async function CompanyRequestsPage() {
  const loaded = await tryApi<RequestRow[]>("/company/access-requests");
  if (!loaded.data) {
    return (
      <>
        <PageHead eyebrow="RH" title="Demandes commerçants" subtitle="Les demandes pour ouvrir un compte commerçant arrivent ici, à côté de vos commerçants." />
        <ErrorCard message={loaded.error ?? "Les demandes n’ont pas pu être chargées."} />
      </>
    );
  }
  const pending = loaded.data.filter((row) => row.status === "pending");
  const done = loaded.data.filter((row) => row.status !== "pending");
  return (
    <>
      <PageHead
        eyebrow="RH"
        title="Demandes commerçants"
        subtitle="Vous créez le compte à partir de la demande. L’identifiant et le mot de passe partent vers le Gmail du commerçant. Il se connecte sur xpass.fr."
      />
      {pending.length === 0 && <p className="muted">Aucune demande commerçant en attente.</p>}
      {pending.map((row) => {
        const activity = row.message.startsWith("Activité :") ? row.message.split("\n")[0].replace("Activité :", "").trim() : "";
        return (
          <article key={row.id} className="card request-card">
            <div className="request-line">
              {activity && <Badge tone="coral">{activity}</Badge>}
              <strong>{row.place_name}</strong>
              <span className="muted">{row.city}</span>
            </div>
            <p>{row.full_name} · {row.gmail}</p>
            <OpenMerchant id={row.id} gmail={row.gmail} />
          </article>
        );
      })}
      {done.length > 0 && (
        <section className="request-list">
          <h2>Déjà traitées</h2>
          {done.map((row) => (
            <p key={row.id} className="muted">{row.status === "accepted" ? "Compte créé" : "Refusée"} · {row.place_name} · {row.gmail}</p>
          ))}
        </section>
      )}
    </>
  );
}
