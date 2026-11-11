import { PageHead } from "@/components/ui";
import { apiFetch, mediaUrl } from "@/lib/session";

import { CreateMerchantForm } from "../create-merchant";
import { MerchantRow } from "../merchant-row";

export const metadata = { title: "Commerçants" };

interface MerchantItem {
  id: string;
  display_name: string;
  city_label: string;
  owner_email: string | null;
  venues: {
    id: string;
    name: string;
    status: string;
    address_line: string;
    postal_code: string;
    district_label: string;
    description: string;
    cover_image_key: string | null;
    price_credits: number | null;
    subcategory_slug: string;
  }[];
}

/** Le service RH crée ses commerçants. Un établissement publié est visible dans l'application client. */
export default async function CompanyMerchantsPage() {
  const [merchants, categories] = await Promise.all([
    apiFetch<MerchantItem[]>("/company/merchants"),
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
        <MerchantRow
          key={m.id}
          merchant={m}
          categories={categories.map((c) => ({ name: c.name, subs: c.subcategories }))}
          photoUrl={mediaUrl(m.venues[0]?.cover_image_key ?? null)}
        />
      ))}
    </>
  );
}
