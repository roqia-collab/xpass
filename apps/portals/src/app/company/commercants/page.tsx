import { Badge, PageHead } from "@/components/ui";
import { apiFetch, mediaUrl } from "@/lib/session";

import { CreateMerchantForm } from "../create-merchant";

export const metadata = { title: "Commerçants" };

interface MerchantRow {
  id: string;
  display_name: string;
  city_label: string;
  owner_email: string | null;
  venues: { id: string; name: string; status: string }[];
}

/** Le service RH crée ses commerçants. Un établissement publié est visible dans l'application client. */
export default async function CompanyMerchantsPage() {
  const [merchants, categories] = await Promise.all([
    apiFetch<MerchantRow[]>("/company/merchants"),
    apiFetch<{ name: string; subcategories: { slug: string; name: string }[] }[]>("/catalog/categories"),
  ]);
  return (
    <>
      <PageHead
        eyebrow="Commerçants"
        title="Vos commerçants"
        subtitle="Vous les créez ici. Leur établissement et leur prestation sont publiés dans l’application client."
        image={mediaUrl("demo/heroes/beaute.jpg") ?? undefined}
        action={<CreateMerchantForm categories={categories.map((c) => ({ name: c.name, subs: c.subcategories }))} />}
      />
      {merchants.length === 0 && <p className="muted">Aucun commerçant pour le moment.</p>}
      {merchants.map((m) => (
        <section key={m.id} className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "baseline", flexWrap: "wrap" }}>
            <h2>{m.display_name}</h2>
            <span className="muted">{m.city_label}</span>
            {m.owner_email && <span className="muted">{m.owner_email}</span>}
          </div>
          {m.venues.map((v) => (
            <div key={v.id} className="list-row" style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <strong style={{ flex: 1 }}>{v.name}</strong>
              <Badge tone={v.status === "published" ? "mint" : "grey"}>
                {v.status === "published" ? "Visible dans l’application" : "Masqué"}
              </Badge>
            </div>
          ))}
        </section>
      ))}
    </>
  );
}
