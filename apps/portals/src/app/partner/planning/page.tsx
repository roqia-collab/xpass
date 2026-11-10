import { CalendarDays, ChevronLeft, ChevronRight, ScanLine } from "lucide-react";
import Link from "next/link";

import { LiveRefresh } from "@/components/live-refresh";
import { Badge, ErrorCard, Notice } from "@/components/ui";
import { initials } from "@/lib/roles";
import { apiFetch } from "@/lib/session";
import type { PartnerBlock, PartnerBooking } from "@/lib/types";

import { getManagedLocation } from "../data";
import { BlockForm } from "../manage-forms";

export const metadata = { title: "Planning" };

const DAY = 24 * 3600 * 1000;
const toMinutes = (t: string) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5));
const isoDate = (d: Date) => d.toISOString().slice(0, 10);
const HOUR_PX = 96;
const parisToday = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Paris" }).format(new Date());
const fmt = (d: Date, opts: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat("fr-FR", { ...opts, timeZone: "UTC" }).format(d);

/** Maquette 18 — planning jour (par ressource) ou semaine, réservations réelles et plages bloquées. */
export default async function PlanningPage({ searchParams }: { searchParams: Promise<{ date?: string; vue?: string }> }) {
  const location = await getManagedLocation();
  if (!location) return <ErrorCard message="Aucun établissement n’est rattaché à ce compte." />;

  const { date, vue } = await searchParams;
  const week = vue === "semaine";
  const today = parisToday();
  const dayStr = date && /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : today;
  const day = new Date(`${dayStr}T12:00:00Z`);
  const weekday = (day.getUTCDay() + 6) % 7; // 0 = lundi
  const from = week ? new Date(day.getTime() - weekday * DAY) : day;
  const span = week ? 7 : 1;
  const [allBookings, blocks] = await Promise.all([
    apiFetch<PartnerBooking[]>(`/partner/bookings?date=${isoDate(from)}&days=${span}`),
    apiFetch<PartnerBlock[]>(`/partner/locations/${location.id}/blocks?start=${isoDate(from)}&days=${span}`),
  ]);
  const bookings = allBookings.filter((b) => b.location_id === location.id);
  const step = week ? 7 * DAY : DAY;
  const nav = (d: Date) => `?date=${isoDate(d)}${week ? "&vue=semaine" : ""}`;
  const label = week
    ? `Semaine du ${fmt(from, { day: "numeric", month: "long" })} au ${fmt(new Date(from.getTime() + 6 * DAY), { day: "numeric", month: "long", year: "numeric" })}`
    : fmt(day, { weekday: "long", day: "numeric", month: "long", year: "numeric" });

  return (
    <>
    <LiveRefresh />
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 300px", gap: 24 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 20, minWidth: 0 }}>
        <div className="page-head" style={{ alignItems: "center" }}>
          <div>
            <h1>Planning</h1>
            <p className="serif" style={{ fontSize: 24, marginTop: 4 }}>{label}</p>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <div className="chip-tabs" role="tablist">
              <Link role="tab" className={week ? "" : "on"} aria-selected={!week} href={`?date=${dayStr}`}>Jour</Link>
              <Link role="tab" className={week ? "on" : ""} aria-selected={week} href={`?date=${dayStr}&vue=semaine`}>Semaine</Link>
            </div>
            <Link className="btn ghost" href={nav(new Date(day.getTime() - step))} aria-label="Période précédente"><ChevronLeft /></Link>
            <Link className="btn ghost" href={nav(new Date(day.getTime() + step))} aria-label="Période suivante"><ChevronRight /></Link>
            <Link className="btn outline" href={week ? "?vue=semaine" : "/partner/planning"}><CalendarDays size={18} /> Aujourd’hui</Link>
          </div>
        </div>

        <Notice>
          {bookings.length ? `${bookings.length} réservation(s) sur la période.` : "Aucune réservation sur la période."} Les réserves
          « en attente » durent 5 minutes maximum. Zones hachurées : fermeture ou plage bloquée.
        </Notice>

        {week ? <WeekView from={from} today={today} bookings={bookings} blocks={blocks} /> : <DayView location={location} day={day} bookings={bookings} blocks={blocks} />}
      </div>

      <aside style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <Link className="btn primary" href="/partner/scanner"><ScanLine size={20} /> Scanner un client</Link>
        {!week && <BlockForm location={location} day={dayStr} blocks={blocks} />}
        <div className="card">
          <strong>Visites</strong>
          <p className="serif" style={{ fontSize: 40, margin: "6px 0 0" }}>{bookings.filter((b) => b.status !== "held").length}</p>
          <p className="muted" style={{ fontSize: 13 }}>réservation(s) confirmée(s) ou utilisée(s)</p>
        </div>
        {/* Maquette 18 : rappel des prestations publiées et de leur durée. */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <strong>Prestations rapides</strong>
            <Link href="/partner/prestations" aria-label="Gérer les prestations"><ChevronRight size={18} /></Link>
          </div>
          {location.offers.filter((o) => o.is_active).map((o, i) => (
            <div key={o.id} className="list-row" style={{ fontSize: 14 }}>
              <span aria-hidden style={{ width: 12, height: 12, borderRadius: 6, background: i % 2 ? "var(--lavender-strong)" : "var(--coral-brand)" }} />
              <span style={{ flex: 1 }}>{o.current.title}</span>
              <span className="muted">{duration(o.current.duration_min)}</span>
            </div>
          ))}
          {location.offers.every((o) => !o.is_active) && <p className="muted" style={{ fontSize: 13, marginTop: 8 }}>Aucune prestation publiée.</p>}
        </div>
      </aside>
    </div>
    </>
  );
}

function DayView({ location, day, bookings, blocks }: {
  location: NonNullable<Awaited<ReturnType<typeof getManagedLocation>>>;
  day: Date;
  bookings: PartnerBooking[];
  blocks: PartnerBlock[];
}) {
  const weekday = (day.getUTCDay() + 6) % 7;
  const exception = location.exceptions.find((e) => e.day === isoDate(day));
  const windows = exception
    ? exception.is_closed ? [] : [{ opens_at: exception.opens_at!, closes_at: exception.closes_at! }]
    : location.hours.filter((h) => h.weekday === weekday);
  const allHours = location.hours.length ? location.hours : [{ opens_at: "09:00", closes_at: "19:00" }];
  const start = Math.floor(Math.min(...allHours.map((h) => toMinutes(h.opens_at))) / 60);
  const end = Math.ceil(Math.max(...allHours.map((h) => toMinutes(h.closes_at))) / 60);
  const hours = Array.from({ length: Math.max(end - start, 1) }, (_, i) => start + i);
  const isOpen = (hour: number) => windows.some((w) => toMinutes(w.opens_at) <= hour * 60 && hour * 60 < toMinutes(w.closes_at));
  const active = location.resources.filter((r) => r.is_active);
  const columns = active.length ? active : [{ id: "lieu", name: location.name, role_label: "Établissement" }];
  const place = (startIso: string, endIso: string) => {
    const top = ((toMinutes(startIso.slice(11)) - start * 60) / 60) * HOUR_PX;
    const height = ((toMinutes(endIso.slice(11)) - toMinutes(startIso.slice(11))) / 60) * HOUR_PX;
    return { top, height: Math.max(height - 4, 22) };
  };
  const collective = bookings.filter((b) => !b.resource_id);

  return (
    <>
      {exception && <Notice>{exception.is_closed ? "Fermeture exceptionnelle" : "Horaires exceptionnels"}{exception.reason ? ` : ${exception.reason}` : ""}.</Notice>}
      <div style={{ overflowX: "auto" }}>
        <div className="planning" style={{ ["--cols" as string]: columns.length }}>
          <div />
          {columns.map((c) => (
            <div key={c.id} className="head">
              <div className="avatar">{initials(c.name)}</div>
              <div>
                <strong style={{ display: "block" }}>{c.name}</strong>
                <span className="muted" style={{ fontSize: 13 }}>{c.role_label}</span>
              </div>
            </div>
          ))}
          <div>
            {hours.map((h) => (
              <div key={h} className="hour">{String(h).padStart(2, "0")}:00</div>
            ))}
          </div>
          {columns.map((c) => (
            <div key={c.id} style={{ position: "relative" }}>
              {hours.map((h) => (
                <div key={h} className={`cell ${isOpen(h) ? "" : "closed"}`} />
              ))}
              {blocks.filter((b) => b.resource_id === c.id).map((b) => (
                <div key={b.id} className="slot-block blocked" style={place(b.local_start, b.local_end)} title={b.reason}>
                  <span className="time">{b.local_start.slice(11)} – {b.local_end.slice(11)}</span>
                  <strong>Bloqué</strong>
                  <span>{b.reason}</span>
                </div>
              ))}
              {bookings.filter((b) => b.resource_id === c.id).map((b) => (
                <div key={b.id} className={`slot-block ${b.status === "held" ? "held" : ""}`} style={place(b.local_start, b.local_end)} title={`${b.offer_title} · ${b.customer_name}`}>
                  <span className="time">{b.local_start.slice(11)} – {b.local_end.slice(11)}</span>
                  <strong>{b.offer_title}</strong>
                  <span>{b.customer_name}{b.status === "held" ? " · en attente" : b.status === "redeemed" ? " · venu ✓" : b.status === "no_show" ? " · absent" : ""}</span>
                  <span>{priceLabel(b)}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
      {collective.length > 0 && (
        <div className="card">
          <h3>Séances collectives</h3>
          {collective.map((b) => (
            <div key={b.id} className="list-row">
              <strong style={{ width: 110 }}>{b.local_start.slice(11)}</strong>
              <span style={{ flex: 1 }}>{b.offer_title} · {b.customer_name}</span>
              <span className="muted">{b.party_size} pers. · {priceLabel(b)}</span>
              <Badge tone={b.status === "held" ? "lavender" : b.status === "no_show" ? "grey" : "mint"}>
                {b.status === "held" ? "En attente" : b.status === "no_show" ? "Absent (payé)" : b.status === "redeemed" ? "Venu" : "Confirmée"}
              </Badge>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function WeekView({ from, today, bookings, blocks }: { from: Date; today: string; bookings: PartnerBooking[]; blocks: PartnerBlock[] }) {
  const days = Array.from({ length: 7 }, (_, i) => new Date(from.getTime() + i * DAY));
  return (
    <div style={{ overflowX: "auto" }}>
      <div className="week-grid">
        {days.map((d) => {
          const iso = isoDate(d);
          const items = [
            ...bookings.filter((b) => b.local_start.startsWith(iso)).map((b) => ({ key: b.id, at: b.local_start, kind: b.status === "held" ? "held" : "", text: `${b.offer_title} · ${b.customer_name}${b.resource_name ? ` · ${b.resource_name}` : ""}` })),
            ...blocks.filter((b) => b.local_start.startsWith(iso)).map((b) => ({ key: b.id, at: b.local_start, kind: "blocked", text: `Bloqué · ${b.resource_name} · ${b.reason}` })),
          ].sort((a, b) => a.at.localeCompare(b.at));
          return (
            <Link key={iso} href={`?date=${iso}`} className={`week-day ${iso === today ? "today" : ""}`} aria-label={`Ouvrir le ${fmt(d, { weekday: "long", day: "numeric", month: "long" })}`}>
              <strong style={{ textTransform: "capitalize" }}>{fmt(d, { weekday: "short", day: "numeric" })}</strong>
              {items.length === 0 && <span className="muted" style={{ fontSize: 12 }}>—</span>}
              {items.map((it) => (
                <div key={it.key} className={`week-item ${it.kind}`}>
                  <strong>{it.at.slice(11, 16)}</strong> {it.text}
                </div>
              ))}
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function duration(min: number) {
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? `${h} h ${String(m).padStart(2, "0")}` : `${h} h`;
}

/** Prix payé par personne, avec l'ajustement appliqué à la réservation (heure de pointe, dernière minute…). */
function priceLabel(b: PartnerBooking): string {
  const up = b.price_adjustments.includes("peak") || b.price_adjustments.includes("demand");
  const down = b.price_adjustments.includes("last_minute");
  return `${b.price_credits_per_person} cr./pers.${up ? " ↑" : down ? " ↓" : ""}`;
}
