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
        subtitle="Les demandes du formulaire arrivent ici. Vous validez les comptes service RH. Les demandes commerçants sont aussi visibles : le service RH peut créer ces comptes depuis son espace."
        image={mediaUrl("demo/heroes/culture.jpg") ?? undefined}
      />
      {pending.length === 0 && <p className="muted">Aucune demande en attente.</p>}
      <RequestGroup title="Services RH à valider" rows={pending.filter((row) => row.kind === "rh")} empty="Aucun compte service RH à valider." />
      <RequestGroup title="Demandes commerçants" rows={pending.filter((row) => row.kind === "merchant")} empty="Aucune demande commerçant." />
      {done.length > 0 && (
        <section className="request-list">
          <h2>Comptes déjà validés</h2>
          {done.map((row) => (
            <article key={row.id} className="card request-card">
              <p className="muted" style={{ margin: 0 }}>
                {row.kind === "rh" ? "Compte service RH" : "Commerçant"} · {STATUS[row.status]} · {row.full_name} · {row.gmail}
              </p>
              {row.status === "accepted" && <ResetAccessPassword gmail={row.gmail} kind={row.kind} />}
            </article>
          ))}
        </section>
      )}
    </>
  );
}

function RequestGroup({ title, rows, empty }: { title: string; rows: RequestRow[]; empty: string }) {
  return (
    <section className="request-list">
      <h2>{title}</h2>
      {rows.length === 0 && <p className="muted">{empty}</p>}
      {rows.map((row) => {
        const activity = row.message.startsWith("Activité :") ? row.message.split("\n")[0].replace("Activité :", "").trim() : "";
        return (
          <article key={row.id} className="card request-card">
            <div className="request-line">
              <Badge tone="lavender">{KIND[row.kind]}</Badge>
              {activity && <Badge tone="coral">{activity}</Badge>}
              <strong>{row.full_name}</strong>
              <span className="muted">{row.gmail}</span>
            </div>
            <p>{row.place_name} · {row.city}</p>
            <DecideRequest id={row.id} gmail={row.gmail} kind={row.kind} />
          </article>
        );
      })}
    </section>
  );
}
