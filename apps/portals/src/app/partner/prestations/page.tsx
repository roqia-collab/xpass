import { Clock, Coins, Plus, Users } from "lucide-react";
import Link from "next/link";

import { Badge, ErrorCard, Notice, PageHead } from "@/components/ui";
import { formatDuration } from "@/lib/roles";
import { mediaUrl } from "@/lib/session";

import { BOOKING_MODE_LABEL, getManagedLocation } from "../data";
import { OfferActiveToggle, OfferEditor } from "../manage-forms";
import { PhotoUpload } from "../photo-upload";

export const metadata = { title: "Prestations" };

/** Maquette 21 — prestations : liste, création, nouvelle version, publication. */
export default async function PrestationsPage({ searchParams }: { searchParams: Promise<{ edit?: string; nouvelle?: string }> }) {
  const location = await getManagedLocation();
  if (!location) return <ErrorCard message="Aucun établissement n’est rattaché à ce compte." />;
  const { edit, nouvelle } = await searchParams;
  const editing = edit ? location.offers.find((o) => o.id === edit) : undefined;
  const panel = editing || (nouvelle && location.can_edit);
  const names = Object.fromEntries(location.resources.map((r) => [r.id, r.name]));

  return (
    <div style={{ display: "grid", gridTemplateColumns: panel ? "minmax(0,1fr) 440px" : "1fr", gap: 24 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 0 }}>
        <PageHead
          eyebrow={`${location.name} · ${location.district_label}`}
          title="Prestations et disponibilités"
          subtitle="Créez vos prestations, assignez-les à votre équipe et publiez-les."
          action={
            location.can_edit ? (
              <Link className="btn primary" href="?nouvelle=1"><Plus size={18} /> Créer une prestation</Link>
            ) : undefined
          }
        />
        {!location.can_edit && <Notice>Lecture seule : seul le responsable de l’établissement modifie le catalogue.</Notice>}
        {location.offers.map((o) => {
          const img = mediaUrl(o.image_key ?? location.cover_image_key);
          return (
            <div key={o.id} className={`offer-card ${editing?.id === o.id ? "selected" : ""}`}>
              {img ? <img className="thumb" src={img} alt="" style={{ width: 168, height: 120, borderRadius: 16 }} /> : <span className="thumb" style={{ width: 168, height: 120 }} />}
              <div style={{ flex: 1, minWidth: 0 }}>
                <Link href={`?edit=${o.id}`}><h3>{o.current.title}</h3></Link>
                <p className="muted" style={{ margin: "4px 0 8px" }}>{o.current.summary}</p>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <span className="pill"><Clock size={14} aria-hidden /> {formatDuration(o.current.duration_min)}</span>
                  <span className="pill"><Coins size={14} aria-hidden /> {o.current.price_credits} crédits (prix de base)</span>
                  <span className="pill">{BOOKING_MODE_LABEL[o.booking_mode]}</span>
                  {o.current.capacity && <span className="pill">capacité {o.current.capacity}</span>}
                  <span className="pill">v{o.current.version}</span>
                </div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "flex-end", minWidth: 150 }}>
                {o.resource_ids.length > 0 && (
                  <span className="muted" style={{ fontSize: 14 }}><Users size={14} aria-hidden /> {o.resource_ids.map((id) => names[id]).join(", ")}</span>
                )}
                <Badge tone={o.is_active ? "mint" : "grey"}>{o.is_active ? "Publiée" : "Brouillon / retirée"}</Badge>
                <OfferActiveToggle locationId={location.id} offerId={o.id} active={o.is_active} canEdit={location.can_edit && o.booking_mode !== "external_ticket"} />
              </div>
            </div>
          );
        })}
        <Notice>
          Modifier une prestation crée une nouvelle version : les réservations existantes gardent leur prix, leur durée et leurs
          conditions d’annulation. Dépublier n’annule aucune réservation.
        </Notice>
      </div>
      {panel && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {editing && location.can_edit && (
            <PhotoUpload locationId={location.id} offerId={editing.id} current={mediaUrl(editing.image_key)} label="Photo de la prestation" />
          )}
          <OfferEditor key={editing?.id ?? "new"} location={location} offer={editing} />
        </div>
      )}
    </div>
  );
}
