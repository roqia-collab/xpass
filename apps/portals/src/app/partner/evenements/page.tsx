import { EventBoard, type VenueEventRow } from "@/components/event-board";
import { ErrorCard, PageHead } from "@/components/ui";
import { apiFetch, mediaUrl } from "@/lib/session";

import { getCurrentLocation } from "../data";
import { savePartnerEvent, setPartnerEventVisible, uploadPartnerEventPhoto } from "./actions";

export const metadata = { title: "Événements" };

export default async function PartnerEventsPage() {
  const location = await getCurrentLocation();
  if (!location) return <ErrorCard message="Aucun établissement n’est rattaché à ce compte." />;
  const events = await apiFetch<VenueEventRow[]>("/partner/events");
  return (
    <>
      <PageHead
        eyebrow={location.name}
        title="Événements"
        subtitle="Indiquez le titre, les horaires et le nombre de crédits. L’événement publié apparaît dans l’application."
        image={mediaUrl(location.cover_image_key) ?? undefined}
      />
      <EventBoard
        events={events
          .filter((event) => event.location_id === location.id)
          .map((event) => ({ ...event, photoUrl: mediaUrl(event.cover_image_key) }))}
        venues={[{ id: location.id, label: location.name }]}
        save={savePartnerEvent}
        hide={setPartnerEventVisible}
        upload={uploadPartnerEventPhoto}
      />
    </>
  );
}
