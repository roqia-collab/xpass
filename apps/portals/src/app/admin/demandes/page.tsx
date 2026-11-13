import { Badge, PageHead } from "@/components/ui";
import { apiFetch, mediaUrl } from "@/lib/session";

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
  const rows = await apiFetch<RequestRow[]>("/admin/access-requests");
  const pending = rows.filter((row) => row.status === "pending");
  const done = rows.filter((row) => row.status !== "pending");
  return (
    <>
      <PageHead
        eyebrow="Admin"
        title="Demandes d’accès"
        subtitle="Le formulaire arrive ici. Vous acceptez, vous choisissez le mot de passe, vous le donnez à la personne. L’identifiant est son Gmail. Elle se connecte avec « Continuer avec un e-mail »."
        image={mediaUrl("demo/heroes/culture.jpg") ?? undefined}
      />
      {pending.length === 0 && <p className="muted">Aucune demande en attente.</p>}
      {pending.map((row) => (
        <article key={row.id} className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <Badge tone="lavender">{KIND[row.kind]}</Badge>
            <strong>{row.full_name}</strong>
            <span className="muted">{row.gmail}</span>
          </div>
          <p style={{ margin: 0 }}>{row.place_name} · {row.city}</p>
          {row.message && <p className="muted" style={{ margin: 0 }}>{row.message}</p>}
          <DecideRequest id={row.id} gmail={row.gmail} />
        </article>
      ))}
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
