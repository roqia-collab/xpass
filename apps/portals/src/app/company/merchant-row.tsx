"use client";

import { useState } from "react";

import { Badge } from "@/components/ui";

import { EditMerchantForm, type MerchantDraft } from "./create-merchant";

export function MerchantRow({
  merchant,
  categories,
  photoUrl,
}: {
  merchant: {
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
  };
  categories: { name: string; subs: { slug: string; name: string }[] }[];
  photoUrl: string | null;
}) {
  const [editing, setEditing] = useState(false);
  const venue = merchant.venues[0];
  const published = venue?.status === "published";
  const photo = photoUrl;
  const initial: MerchantDraft = {
    display_name: merchant.display_name,
    owner_email: merchant.owner_email ?? "",
    location_name: venue?.name ?? "",
    subcategory_slug: venue?.subcategory_slug || categories[0]?.subs[0]?.slug || "",
    address_line: venue?.address_line ?? "",
    postal_code: venue?.postal_code ?? "",
    city: merchant.city_label || "Paris",
    description: venue?.description ?? "",
    price_credits: String(venue?.price_credits ?? 8),
  };
  return (
    <section className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        {photo ? (
          <img src={photo} alt="" style={{ width: 160, height: 110, objectFit: "cover", borderRadius: 14 }} />
        ) : (
          <span className="thumb" style={{ width: 160, height: 110 }} />
        )}
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "baseline", flexWrap: "wrap" }}>
            <h2>{merchant.display_name}</h2>
            <Badge tone={published ? "mint" : "grey"}>{published ? "Visible dans l’application" : "Retiré"}</Badge>
          </div>
          {venue && (
            <p className="muted">
              {venue.name} · {venue.address_line}, {venue.postal_code} {venue.district_label}
              {venue.price_credits ? ` · ${venue.price_credits} crédits` : ""}
            </p>
          )}
          {merchant.owner_email && <p className="muted">{merchant.owner_email}</p>}
        </div>
        <button className="btn outline" onClick={() => setEditing((v) => !v)}>{editing ? "Fermer" : "Modifier"}</button>
      </div>
      {editing && (
        <EditMerchantForm
          categories={categories}
          merchantId={merchant.id}
          initial={initial}
          published={published}
          onDone={() => setEditing(false)}
        />
      )}
    </section>
  );
}
