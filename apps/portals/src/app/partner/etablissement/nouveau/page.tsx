import { ErrorCard, PageHead } from "@/components/ui";
import { apiFetch } from "@/lib/session";

import { getCurrentLocation, getManagedLocation } from "../../data";
import { NewLocationForm } from "./new-location-form";

export const metadata = { title: "Nouvel établissement" };

export default async function NewLocationPage() {
  const [current, managed] = await Promise.all([getCurrentLocation(), getManagedLocation()]);
  if (!current || !managed) return <ErrorCard message="Aucun établissement n’est rattaché à ce compte." />;
  if (!managed.can_edit) return <ErrorCard message="Seul le responsable peut ajouter un établissement." />;
  const categories = await apiFetch<{ name: string; subcategories: { slug: string; name: string }[] }[]>("/catalog/categories");
  return (
    <>
      <PageHead
        eyebrow={current.merchant_name}
        title="Ajouter un établissement"
        subtitle="Un autre lieu de votre entreprise. Son adresse est placée sur la carte par la Base Adresse Nationale ; il reste en brouillon jusqu’à sa publication par XPASS."
      />
      <NewLocationForm currentId={current.id} categories={categories.map((c) => ({ name: c.name, subs: c.subcategories }))} />
    </>
  );
}
