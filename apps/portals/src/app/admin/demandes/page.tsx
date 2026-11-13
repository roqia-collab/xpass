import { Badge, ErrorCard, PageHead } from "@/components/ui";
import { mediaUrl, tryApi } from "@/lib/session";

import { DecideRequest } from "./decide";

export const metadata = { title: "Demandes" };

type RequestRow = {
  id: string;
  kind: "rh" | "merchant";
  gmail: string;
  full_name: string;
  place_name: string;
  city: string;
  message: string;
  status: "pending" | "accepted" | "refused";
  created_at: string;
};

const KIND = { rh: "Service RH", merchant: "Commerçant" };
const STATUS = { pending: "En attente", accepted: "Acceptée", refused: "Refusée" };

export default async function RequestsPage() {
  const loaded = await tryApi<RequestRow[]>("/admin/access-requests");
  if (!loaded.data) {
    return (
      <>
        <PageHead eyebrow="Admin" title="Demandes d’accès" subtitle="Les demandes du formulaire public arrivent ici." />
        <ErrorCard message={loaded.error ?? "Les demandes n’ont pas pu être chargées."} />
      </>
    );
  }
  const rows = loaded.data;
  const pending = rows.filter((row) => row.status === "pending");
  const done = rows.filter((row) => row.status !== "pending");
  return (
    <>
      <PageHead
        eyebrow="Admin"
        title="Demandes d’accès"
        subtitle="Le formulaire arrive ici, avec l’activité choisie. Vous acceptez, vous choisissez le mot de passe, vous le donnez à la personne. Elle ouvre rh.xpass.fr et entre son Gmail et ce mot de passe."
        image={mediaUrl("demo/heroes/culture.jpg") ?? undefined}
      />
      {pending.length === 0 && <p className="muted">Aucune demande en attente.</p>}
      {pending.map((row) => {
        const activity = row.message.startsWith("Activité :") ? row.message.split("\n")[0].replace("Activité :", "").trim() : "";
        return (
        <article key={row.id} className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <Badge tone="lavender">{KIND[row.kind]}</Badge>
            {activity && <Badge tone="coral">{activity}</Badge>}
            <strong>{row.full_name}</strong>
            <span className="muted">{row.gmail}</span>
          </div>
          <p style={{ margin: 0 }}>{row.place_name} · {row.city}</p>
          {row.message && <p className="muted" style={{ margin: 0 }}>{row.message}</p>}
          <DecideRequest id={row.id} gmail={row.gmail} />
        </article>
        );
      })}
      {done.length > 0 && (
        <section style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <h2>Déjà traitées</h2>
          {done.map((row) => (
            <p key={row.id} className="muted" style={{ margin: 0 }}>
              {STATUS[row.status]} · {KIND[row.kind]} · {row.full_name} · {row.gmail}
            </p>
          ))}
        </section>
      )}
    </>
  );
}
