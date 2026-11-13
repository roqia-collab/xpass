import { ErrorCard, PageHead } from "@/components/ui";
import { mediaUrl, tryApi } from "@/lib/session";

import { AdminRows } from "./rows";
import { CreateAdminForm } from "./create-admin";

export const metadata = { title: "Administrateurs" };

type AdminRow = { email: string; display_name: string; original: boolean };

export default async function AdministratorsPage() {
  const loaded = await tryApi<AdminRow[]>("/admin/administrators");
  const rows = loaded.data ?? [];
  return (
    <>
      <PageHead
        eyebrow="Admin"
        title="Administrateurs"
        subtitle="L’admin d’origine n’utilise pas Gmail. Il crée les autres admins : leur identifiant est leur Gmail, et il leur remet le mot de passe."
        image={mediaUrl("demo/heroes/culture.jpg") ?? undefined}
        action={<CreateAdminForm />}
      />
      {!loaded.data && <ErrorCard message={loaded.error ?? "La liste n’a pas pu être chargée. Le formulaire de création reste disponible."} />}
      <AdminRows rows={rows} />
    </>
  );
}
