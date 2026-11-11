import { ArrowRight, CalendarDays, Flower2, Users } from "lucide-react";
import Link from "next/link";

import { LiveRefresh } from "@/components/live-refresh";
import { Badge, ErrorCard, Kpi, Notice, PageHead } from "@/components/ui";
import { money } from "@/lib/money";
import { apiFetch, mediaUrl } from "@/lib/session";
import { NETWORK_LINE } from "@/lib/roles";
import type { Settlements } from "@/lib/types";

import { getCurrentLocation, getManagedLocation } from "./data";

export const metadata = { title: "Vue d’ensemble" };

export default async function PartnerOverview() {
  const location = await getCurrentLocation();
  if (!location) return <ErrorCard message="Aucun établissement n’est rattaché à ce compte." />;
  const cover = mediaUrl(location.cover_image_key);
  const staff = location.team.filter((t) => t.kind === "staff");
  const [visits, managed, settlements, affiliation] = await Promise.all([
    apiFetch<{ booking_id: string }[]>(`/partner/redemptions?location_id=${location.id}`),
    getManagedLocation(),
    apiFetch<Settlements>("/partner/settlements").catch(() => null),
    apiFetch<{ organization_name: string | null; published_locations: number }>(
      `/partner/affiliation?location_id=${location.id}`,
    ).catch(() => null),
  ]);
  const offerPhotos = (managed?.offers ?? []).filter((o) => o.image_key);

  return (
    <>
      <LiveRefresh />
      <PageHead
        eyebrow={`${location.category_name} · ${location.subcategory_name}`}
        title={location.name}
        subtitle={`${location.address_line}, ${location.postal_code} ${location.city_name}`}
        image={cover ?? undefined}
      />
      <Notice>
        {NETWORK_LINE}
        {affiliation?.organization_name ? ` Service RH : ${affiliation.organization_name}.` : ""}
        {affiliation && affiliation.published_locations > 0 ? " Vos prestations publiées sont dans l’application." : ""}
      </Notice>

      {offerPhotos.length > 0 && (
        <section className="photo-band">
          <h2>Vos prestations</h2>
          <div className="photo-band-row">
            {offerPhotos.map((o) => (
              <figure key={o.id}>
                <img src={mediaUrl(o.image_key)!} alt="" />
                <figcaption>
                  <strong>{o.current.title}</strong>
                  <span>{o.current.price_credits} crédits</span>
                </figcaption>
              </figure>
            ))}
          </div>
        </section>
      )}

      <div className="grid grid-3">
        <Kpi href="/partner/prestations" icon={<Flower2 />} label="Prestations publiées" value={location.offers.length} detail="Catalogue XPASS" />
        <Kpi href="/partner/equipe" icon={<Users />} label="Équipe" value={staff.length} detail={staff.map((s) => s.name).join(", ") || "—"} />
        <Kpi href="/partner/planning" icon={<CalendarDays />} label="Visites du jour" value={visits.length} detail="Consommations validées aujourd’hui" tone="coral" />
      </div>

      <section className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <h3>Paiements</h3>
          <Link href="/partner/reglements">Tout voir <ArrowRight size={14} /></Link>
        </div>
        {settlements && (
          <p>
            À recevoir : <strong>{money(settlements.to_receive_minor, settlements.currency)}</strong>
            {" · "}période en cours, net {money(settlements.open_period.net_minor, settlements.currency)}
            {" · "}compte de versement {settlements.has_payout_account ? "enregistré" : "à configurer"}
          </p>
        )}
        {settlements && !settlements.has_payout_account && (
          <p className="muted">La commission XPASS est déduite du versement. Rien n’est viré tant que le compte de versement n’est pas relié.</p>
        )}
        {settlements && settlements.payouts.slice(0, 5).map((p) => (
          <Link key={p.id} href={`/partner/reglements?versement=${p.id}`} className="list-row" style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <div style={{ flex: 1 }}>
              <strong>{p.period_start} – {p.period_end}</strong>
              <div className="muted" style={{ fontSize: 13 }}>{p.visits} visite(s)</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div>{money(p.net_minor, p.currency)}</div>
              <Badge tone={p.status === "paid" ? "mint" : p.status === "failed" || p.status === "to_reconcile" ? "coral" : "lavender"}>
                {p.status === "paid" ? "Versé" : p.status === "in_transit" ? "En cours" : p.status === "failed" ? "Échec" : p.status === "to_reconcile" ? "Écart" : "En attente"}
              </Badge>
            </div>
          </Link>
        ))}
        {settlements && settlements.payouts.length === 0 && <p className="muted">Aucun versement clôturé. Les visites de la semaine sont dans la période en cours.</p>}
        {!settlements && <p className="muted">Les règlements ne sont pas disponibles pour le moment.</p>}
      </section>

      <Notice>
        Chaque visite validée est versée après la clôture de la semaine. Le prix de base bouge selon le créneau
        (+20 % aux heures de pointe ou si le créneau est presque plein, −20 % en dernière minute). Annulation tardive :
        la moitié vous est versée. Absence : la totalité, 2 h après la fin du créneau.
      </Notice>
    </>
  );
}
