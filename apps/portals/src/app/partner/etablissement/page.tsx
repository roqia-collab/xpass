import { Badge, ErrorCard, PageHead } from "@/components/ui";

import { getCurrentLocation, getManagedLocation } from "../data";
import { ExceptionsManager, HoursEditor, LocationForm } from "../manage-forms";
import { PhotoUpload } from "../photo-upload";
import { ChangeRequest, type ChangeRow } from "../change-request";
import { apiFetch, mediaUrl } from "@/lib/session";

export const metadata = { title: "Établissement" };

export default async function EtablissementPage() {
  const [summary, location] = await Promise.all([getCurrentLocation(), getManagedLocation()]);
  if (!summary || !location) return <ErrorCard message="Aucun établissement n’est rattaché à ce compte." />;
  const [history, categories] = location.can_edit
    ? await Promise.all([
        apiFetch<ChangeRow[]>(`/partner/locations/${location.id}/change-requests`),
        apiFetch<{ name: string; subcategories: { slug: string; name: string }[] }[]>("/catalog/categories"),
      ])
    : [[], []];
  return (
    <>
      <PageHead
        title="Établissement"
        image={mediaUrl(summary.cover_image_key) ?? undefined}
        subtitle={`${summary.kind_label} · ${summary.address_line}, ${summary.postal_code} ${summary.city_name}`}
        action={<Badge tone={summary.status === "published" ? "mint" : "grey"}>{summary.status === "published" ? "Publié" : summary.status}</Badge>}
      />
      <PhotoUpload locationId={location.id} current={mediaUrl(location.cover_image_key)} label="Photo principale de l’établissement" />
      {location.can_edit && (
        <ChangeRequest
          locationId={location.id}
          current={{ name: summary.name, subcategory_slug: summary.subcategory_slug, kind_label: summary.kind_label }}
          categories={categories.map((c) => ({ name: c.name, subs: c.subcategories }))}
          history={history}
        />
      )}
      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <LocationForm location={location} />
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <HoursEditor location={location} />
          <ExceptionsManager location={location} />
        </div>
      </div>
      <p className="muted" style={{ fontSize: 13 }}>
        Le nom, l’activité et l’adresse changent après validation par l’équipe XPASS (bloc « Demander une modification »). Un changement d’horaires
        n’annule jamais de réservation : celles qui tombent hors des nouveaux horaires sont signalées.
      </p>
    </>
  );
}
