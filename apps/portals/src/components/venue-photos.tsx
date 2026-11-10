import { apiFetch, mediaUrl } from "@/lib/session";

interface Card {
  slug: string;
  name: string;
  district_label: string;
  subcategory_name: string;
  cover_image_key: string | null;
}

/** Bande de vraies photos du catalogue (mêmes fichiers que l'application). */
export async function VenuePhotos({
  title,
  text,
  category,
}: {
  title: string;
  text?: string;
  category?: string;
}) {
  const qs = new URLSearchParams({ city: "paris", limit: "8" });
  if (category) qs.set("category", category);
  let items: Card[] = [];
  try {
    const page = await apiFetch<{ items: Card[] }>(`/catalog/locations?${qs}`);
    items = page.items.filter((l) => l.cover_image_key);
  } catch {
    return null;
  }
  if (items.length === 0) return null;
  return (
    <section className="photo-band">
      <div>
        <h2>{title}</h2>
        {text && <p className="muted">{text}</p>}
      </div>
      <div className="photo-band-row">
        {items.map((l) => (
          <figure key={l.slug}>
            <img src={mediaUrl(l.cover_image_key)!} alt="" />
            <figcaption>
              <strong>{l.name}</strong>
              <span>{l.subcategory_name} · {l.district_label}</span>
            </figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}
