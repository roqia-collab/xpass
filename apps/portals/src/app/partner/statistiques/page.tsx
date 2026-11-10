import { CalendarCheck, Coins, Users, Wallet } from "lucide-react";
import Link from "next/link";

import { ErrorCard, Kpi, Notice, PageHead } from "@/components/ui";
import { ApiError, apiFetch } from "@/lib/session";

import { getCurrentLocation } from "../data";

export const metadata = { title: "Statistiques" };

interface Stats {
  days: number;
  currency: string;
  visits: number;
  unique_customers: number;
  credits_used: number;
  gross_minor: number;
  commission_minor: number;
  net_minor: number;
  pending_valuation: number;
  upcoming_bookings: number;
  cancellations: number;
  late_cancellations: number;
  no_shows: number;
  surcharged_visits: number;
  discounted_visits: number;
  weeks: { week_start: string; visits: number; gross_minor: number }[];
  top_offers: { title: string; visits: number; credits: number }[];
  weekdays: number[];
}

const PERIODS = [7, 30, 90, 365] as const;
const DAYS = ["Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim."];
const money = (minor: number, currency: string) => new Intl.NumberFormat("fr-FR", { style: "currency", currency }).format(minor / 100);
const weekFmt = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short" });

/** Statistiques de l'établissement actif (maquette 21, entrée « Statistiques ») : données réelles uniquement. */
export default async function StatsPage({ searchParams }: { searchParams: Promise<{ jours?: string }> }) {
  const location = await getCurrentLocation();
  if (!location) return <ErrorCard message="Aucun établissement n’est rattaché à ce compte." />;
  const { jours } = await searchParams;
  const days = PERIODS.find((p) => String(p) === jours) ?? 30;
  let s: Stats;
  try {
    s = await apiFetch<Stats>(`/partner/locations/${location.id}/stats?days=${days}`);
  } catch (e) {
    return <ErrorCard message={e instanceof ApiError && e.status === 403 ? "Les statistiques sont réservées au responsable de l’établissement." : "Statistiques indisponibles."} />;
  }
  const maxWeek = Math.max(1, ...s.weeks.map((w) => w.visits));
  const maxDay = Math.max(1, ...s.weekdays);
  return (
    <>
      <PageHead
        eyebrow={`${location.name} · ${location.district_label}`}
        title="Statistiques"
        subtitle="Visites validées par le scanner, crédits utilisés et montants qui vous reviennent."
        action={
          <div style={{ display: "flex", gap: 6 }} role="group" aria-label="Période">
            {PERIODS.map((p) => (
              <Link key={p} href={`?jours=${p}`} className={`btn ${p === days ? "outline" : "ghost"}`} aria-current={p === days ? "page" : undefined}>
                {p === 365 ? "1 an" : `${p} j`}
              </Link>
            ))}
          </div>
        }
      />
      <div className="grid grid-3">
        <Kpi icon={<CalendarCheck />} label="Visites" value={s.visits} detail={`${s.unique_customers} client(s) différent(s)`} />
        <Kpi icon={<Coins />} label="Crédits utilisés" value={s.credits_used} detail={`${s.upcoming_bookings} réservation(s) à venir`} />
        <Kpi icon={<Wallet />} label="Net pour vous" value={money(s.net_minor, s.currency)} detail={`Brut ${money(s.gross_minor, s.currency)} · commission ${money(s.commission_minor, s.currency)}`} tone="coral" />
      </div>
      {s.pending_valuation > 0 && (
        <Notice>{s.pending_valuation} prestation(s) pas encore valorisée(s) : leur montant apparaîtra après application du barème.</Notice>
      )}

      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <section className="card">
          <h3>Visites par semaine</h3>
          {s.weeks.length === 0 ? (
            <p className="muted" style={{ marginTop: 8 }}>Aucune visite sur la période.</p>
          ) : (
            <div className="bars" role="list" aria-label="Visites par semaine">
              {s.weeks.map((w) => (
                <div key={w.week_start} className="bar" role="listitem" aria-label={`Semaine du ${weekFmt.format(new Date(`${w.week_start}T12:00:00Z`))} : ${w.visits} visite(s)`}>
                  <span className="value">{w.visits}</span>
                  <span className="fill" style={{ height: `${(w.visits / maxWeek) * 100}%` }} />
                  <span className="label">{weekFmt.format(new Date(`${w.week_start}T12:00:00Z`))}</span>
                </div>
              ))}
            </div>
          )}
        </section>
        <section className="card">
          <h3>Jours les plus fréquentés</h3>
          <div className="bars" role="list" aria-label="Visites par jour de la semaine">
            {s.weekdays.map((n, i) => (
              <div key={DAYS[i]} className="bar" role="listitem" aria-label={`${DAYS[i]} : ${n} visite(s)`}>
                <span className="value">{n}</span>
                <span className="fill lavender" style={{ height: `${(n / maxDay) * 100}%` }} />
                <span className="label">{DAYS[i]}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <section className="card" style={{ overflowX: "auto" }}>
          <h3>Prestations les plus utilisées</h3>
          <table className="table">
            <thead><tr><th>Prestation</th><th>Visites</th><th>Crédits</th></tr></thead>
            <tbody>
              {s.top_offers.map((o) => <tr key={o.title}><td>{o.title}</td><td>{o.visits}</td><td>{o.credits}</td></tr>)}
              {s.top_offers.length === 0 && <tr><td colSpan={3} className="muted">Aucune visite sur la période.</td></tr>}
            </tbody>
          </table>
        </section>
        <section className="card">
          <h3><Users size={18} aria-hidden /> Annulations et absences</h3>
          <p style={{ marginTop: 8 }}><strong>{s.cancellations}</strong> annulation(s) sur la période, dont <strong>{s.late_cancellations}</strong> tardive(s) (la moitié des crédits vous est versée).</p>
          <p style={{ marginTop: 8 }}><strong>{s.no_shows}</strong> client(s) absent(s) sans annuler : la totalité des crédits vous est versée.</p>
          <h3 style={{ marginTop: 16 }}>Prix variable</h3>
          <p style={{ marginTop: 8 }}>
            <strong>{s.surcharged_visits}</strong> visite(s) à prix majoré (heure de pointe ou forte demande) et{" "}
            <strong>{s.discounted_visits}</strong> à prix réduit (dernière minute) : vos créneaux creux se remplissent,
            les créneaux recherchés rapportent davantage.
          </p>
        </section>
      </div>
    </>
  );
}
