import { EventBoard, type VenueEventRow, type VenueOption } from "@/components/event-board";
import { PageHead } from "@/components/ui";
import { apiFetch, mediaUrl } from "@/lib/session";

import { saveCompanyEvent, setCompanyEventVisible, uploadCompanyEventPhoto } from "../actions";

export const metadata = { title: "Événements" };

interface MerchantItem {
  display_name: string;
  venues: { id: string; name: string; status: string }[];
}

export default async function CompanyEventsPage() {
  const [events, merchants] = await Promise.all([
    apiFetch<VenueEventRow[]>("/company/events"),
    apiFetch<MerchantItem[]>("/company/merchants"),
  ]);
  const venues: VenueOption[] = merchants.flatMap((merchant) =>
    merchant.venues
      .filter((venue) => venue.status === "published")
      .map((venue) => ({ id: venue.id, label: `${merchant.display_name} · ${venue.name}` })),
  );
  return (
    <>
      <PageHead
        eyebrow="RH"
        title="Événements de vos commerçants"
        subtitle="Publiez un événement sur un commerçant que vous avez créé. Il s’affiche dans l’application client."
        image={mediaUrl("demo/heroes/culture.jpg") ?? undefined}
      />
      <EventBoard
        events={events.map((event) => ({ ...event, photoUrl: mediaUrl(event.cover_image_key) }))}
        venues={venues}
        save={saveCompanyEvent}
        hide={setCompanyEventVisible}
        upload={uploadCompanyEventPhoto}
      />
    </>
  );
}
