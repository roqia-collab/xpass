import { EventBoard, type VenueEventRow, type VenueOption } from "@/components/event-board";
import { PageHead } from "@/components/ui";
import type { OrganizationRow } from "@/lib/admin-types";
import { apiFetch, mediaUrl } from "@/lib/session";

import { saveAdminEvent, setAdminEventVisible, uploadAdminEventPhoto } from "../actions";

export const metadata = { title: "Événements" };

export default async function AdminEventsPage() {
  const [events, orgs] = await Promise.all([
    apiFetch<VenueEventRow[]>("/admin/events"),
    apiFetch<OrganizationRow[]>("/admin/organizations"),
  ]);
  const venues: VenueOption[] = orgs.flatMap((org) =>
    org.merchants.flatMap((merchant) =>
      merchant.venues
        .filter((venue) => venue.status === "published")
        .map((venue) => ({ id: venue.id, label: `${org.name} · ${merchant.display_name} · ${venue.name}` })),
    ),
  );
  return (
    <>
      <PageHead
        eyebrow="Admin"
        title="Événements"
        subtitle="Un événement publié sur un commerçant d’un service RH apparaît dans l’application client."
        image={mediaUrl("demo/heroes/culture.jpg") ?? undefined}
      />
      <EventBoard
        events={events.map((event) => ({ ...event, photoUrl: mediaUrl(event.cover_image_key) }))}
        venues={venues}
        save={saveAdminEvent}
        hide={setAdminEventVisible}
        upload={uploadAdminEventPhoto}
      />
    </>
  );
}
