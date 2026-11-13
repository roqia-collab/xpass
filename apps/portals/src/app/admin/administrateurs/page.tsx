import { Badge, PageHead } from "@/components/ui";
import { apiFetch, mediaUrl } from "@/lib/session";

import { CreateAdminForm } from "./create-admin";

export const metadata = { title: "Administrateurs" };

type AdminRow = { email: string; display_name: string; original: boolean };

export default async function AdministratorsPage() {
  const rows = await apiFetch<AdminRow[]>("/admin/administrators");
  return (
    <>
      <PageHead
        eyebrow="Admin"
        title="Administrateurs"
        subtitle="L’admin d’origine n’utilise pas Gmail. Il crée les autres admins : leur identifiant est leur Gmail, et il leur remet le mot de passe."
        image={mediaUrl("demo/heroes/culture.jpg") ?? undefined}
        action={<CreateAdminForm />}
      />
      {rows.map((row) => (
        <p key={row.email} style={{ margin: 0, display: "flex", gap: 10, alignItems: "center" }}>
          <strong>{row.display_name}</strong>
          <span className="muted">{row.original ? "Identifiant admin" : row.email}</span>
          {row.original && <Badge tone="coral">Origine</Badge>}
        </p>
      ))}
    </>
  );
}
