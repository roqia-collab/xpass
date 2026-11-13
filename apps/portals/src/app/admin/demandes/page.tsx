import { Badge, ErrorCard, PageHead } from "@/components/ui";
import { mediaUrl, tryApi } from "@/lib/session";

import { DecideRequest, ResetAccessPassword } from "./decide";

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
        subtitle="Vous acceptez et vous choisissez le mot de passe. Un service RH se connecte sur rh.xpass.fr. Un commerçant se connecte sur xpass.fr, espace commerçant. L’identifiant est le Gmail."
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
          <DecideRequest id={row.id} gmail={row.gmail} kind={row.kind} />
        </article>
        );
      })}
      {done.length > 0 && (
        <section style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <h2>Déjà traitées</h2>
          {done.map((row) => (
            <article key={row.id} className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <p className="muted" style={{ margin: 0 }}>
                {STATUS[row.status]} · {KIND[row.kind]} · {row.full_name} · {row.gmail}
              </p>
              {row.status === "accepted" && <ResetAccessPassword gmail={row.gmail} kind={row.kind} />}
            </article>
          ))}
        </section>
      )}
    </>
  );
}
