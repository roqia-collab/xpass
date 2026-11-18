"use client";

import { CalendarDays, Check, ChevronRight, QrCode, ScanLine, Sparkles, Wallet, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

export type DemoKind = "planning" | "revenus";

const euros = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });

/** Fenêtre plein écran (feuille sur mobile) qui présente une interface de démonstration. */
export function DemoSheet({ kind, onClose }: { kind: DemoKind | null; onClose: () => void }) {
  const panel = useRef<HTMLDivElement>(null);
  const [closing, setClosing] = useState(false);

  const close = () => {
    setClosing(true);
    window.setTimeout(() => { setClosing(false); onClose(); }, 320);
  };

  useEffect(() => {
    if (!kind) return;
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = overflow;
      window.removeEventListener("keydown", onKey);
      previous?.focus();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind]);

  if (!kind) return null;
  const title = kind === "planning" ? "Votre espace commerçant" : "Vos revenus XPASS";
  return createPortal(
    <div className={`xp-sheet-root${closing ? " is-closing" : ""}`} role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div className="xp-sheet" role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} ref={panel}>
        <header className="xp-sheet-head">
          <div className="xp-sheet-brand"><img src="/logo.png" alt="XPASS" /><span>Démo</span></div>
          <strong>{title}</strong>
          <button type="button" className="xp-close" onClick={close} aria-label="Fermer"><X size={20} aria-hidden /></button>
        </header>
        <div className="xp-sheet-body">{kind === "planning" ? <PlanningDemo /> : <RevenueDemo />}</div>
        <footer className="xp-sheet-foot">
          <span>Interface de démonstration : les données sont fictives.</span>
          <a className="btn primary" href="#demarrer" onClick={close}>Ouvrir mon compte <ChevronRight size={18} aria-hidden /></a>
        </footer>
      </div>
    </div>,
    document.body,
  );
}

function Card({ children, className = "", delay = 0 }: { children: ReactNode; className?: string; delay?: number }) {
  return <section className={`xp-card ${className}`} style={{ animationDelay: `${120 + delay * 70}ms` }}>{children}</section>;
}

// ---------------------------------------------------------------- planning

const DAYS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
const HOURS = ["10 h", "12 h", "14 h", "16 h", "18 h", "20 h"];
type Slot = "closed" | "open" | "booked";

function initialSlots(): Slot[][] {
  const booked = new Set(["0-4", "1-4", "2-5", "4-4", "4-5", "5-1", "5-2", "6-1"]);
  const open = new Set(["0-3", "1-5", "2-4", "3-4", "3-5", "4-3", "5-0", "5-3", "6-0", "6-2"]);
  return DAYS.map((_, d) => HOURS.map((_, h) => (booked.has(`${d}-${h}`) ? "booked" : open.has(`${d}-${h}`) ? "open" : "closed")));
}

const SERVICES = [
  { name: "Cours collectif · 60 min", credits: 12, on: true },
  { name: "Accès libre · 2 h", credits: 8, on: true },
  { name: "Séance découverte", credits: 6, on: false },
];

function PlanningDemo() {
  const [slots, setSlots] = useState<Slot[][]>(initialSlots);
  const [services, setServices] = useState(SERVICES);
  const [scan, setScan] = useState<"idle" | "scanning" | "ok">("idle");

  const stats = useMemo(() => {
    const flat = slots.flat();
    const open = flat.filter((s) => s === "open").length;
    const booked = flat.filter((s) => s === "booked").length;
    return { open, booked, credits: booked * 12 };
  }, [slots]);

  const toggle = (d: number, h: number) => setSlots((prev) => prev.map((row, i) => row.map((s, j) => {
    if (i !== d || j !== h || s === "booked") return s;
    return s === "open" ? "closed" : "open";
  })));

  const runScan = () => {
    if (scan === "scanning") return;
    setScan("scanning");
    window.setTimeout(() => setScan("ok"), 1400);
    window.setTimeout(() => setScan("idle"), 3600);
  };

  return (
    <div className="xp-grid xp-grid-planning">
      <Card className="xp-kpis" delay={0}>
        <div><small>Places ouvertes</small><b key={stats.open} className="xp-bump">{stats.open}</b></div>
        <div><small>Réservées</small><b key={stats.booked} className="xp-bump">{stats.booked}</b></div>
        <div><small>Crédits attendus</small><b>{stats.credits}</b></div>
      </Card>

      <Card className="xp-planning" delay={1}>
        <div className="xp-card-title"><CalendarDays size={18} aria-hidden /><strong>Semaine du 23 novembre</strong><span>Touchez un créneau pour l’ouvrir ou le fermer</span></div>
        <div className="xp-week" role="grid" aria-label="Planning de la semaine">
          <span />
          {DAYS.map((d) => <span key={d} className="xp-day">{d}</span>)}
          {HOURS.map((hour, h) => (
            <div key={hour} className="xp-row" role="row">
              <span className="xp-hour">{hour}</span>
              {DAYS.map((day, d) => {
                const s = slots[d][h];
                return (
                  <button
                    key={day}
                    type="button"
                    role="gridcell"
                    className={`xp-slot is-${s}`}
                    style={{ animationDelay: `${200 + (d + h) * 28}ms` }}
                    onClick={() => toggle(d, h)}
                    aria-label={`${day} ${hour} : ${s === "booked" ? "réservé" : s === "open" ? "ouvert" : "fermé"}`}
                    disabled={s === "booked"}
                  >
                    {s === "booked" ? <Check size={14} aria-hidden /> : s === "open" ? "2" : ""}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
        <div className="xp-legend"><i className="is-open" />Ouvert <i className="is-booked" />Réservé <i className="is-closed" />Fermé</div>
      </Card>

      <Card className="xp-services" delay={2}>
        <div className="xp-card-title"><Sparkles size={18} aria-hidden /><strong>Prestations</strong></div>
        <ul>
          {services.map((s, i) => (
            <li key={s.name}>
              <div><strong>{s.name}</strong><span>{s.credits} crédits · {euros.format(s.credits * 0.9)} pour vous</span></div>
              <button
                type="button"
                className={`xp-switch${s.on ? " is-on" : ""}`}
                role="switch"
                aria-checked={s.on}
                aria-label={`Publier ${s.name}`}
                onClick={() => setServices((prev) => prev.map((x, j) => (j === i ? { ...x, on: !x.on } : x)))}
              ><i /></button>
            </li>
          ))}
        </ul>
      </Card>

      <Card className={`xp-scanner is-${scan}`} delay={3}>
        <div className="xp-card-title"><QrCode size={18} aria-hidden /><strong>Scanner au comptoir</strong></div>
        <div className="xp-scan-view" aria-live="polite">
          <div className="xp-scan-frame"><ScanLine size={56} strokeWidth={1.4} aria-hidden /><i className="xp-scan-beam" /></div>
          <p>{scan === "ok" ? "Visite validée · 12 crédits" : scan === "scanning" ? "Lecture du QR code…" : "Présentez le QR code du membre"}</p>
        </div>
        <button type="button" className="btn primary" onClick={runScan}>{scan === "ok" ? <><Check size={18} aria-hidden /> Validé</> : "Scanner un QR code"}</button>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------- revenus

const PAYOUTS = [
  { week: "Semaine 46", visits: 31, amount: 334.8 },
  { week: "Semaine 45", visits: 27, amount: 291.6 },
  { week: "Semaine 44", visits: 22, amount: 237.6 },
];

function RevenueDemo() {
  const [visits, setVisits] = useState(30);
  const [credits, setCredits] = useState(10);
  const gross = visits * credits;
  const net = gross * 0.9;
  const weeks = [0.62, 0.78, 0.9, 1].map((k, i) => ({ label: `S${i + 1}`, value: Math.round(net * k) }));
  const max = Math.max(...weeks.map((w) => w.value), 1);
  const animated = useCountUp(net);

  return (
    <div className="xp-grid xp-grid-revenue">
      <Card className="xp-hero-figure" delay={0}>
        <small>Versé chaque semaine</small>
        <b>{euros.format(animated)}</b>
        <span>{visits} visites × {credits} crédits = {gross} crédits · 10 % retenus par XPASS</span>
      </Card>

      <Card className="xp-controls" delay={1}>
        <label>
          <span>Visites scannées par semaine <b>{visits}</b></span>
          <input type="range" min={5} max={80} value={visits} onChange={(e) => setVisits(+e.target.value)} />
        </label>
        <label>
          <span>Crédits par visite <b>{credits}</b></span>
          <input type="range" min={4} max={20} value={credits} onChange={(e) => setCredits(+e.target.value)} />
        </label>
      </Card>

      <Card className="xp-chart" delay={2}>
        <div className="xp-card-title"><Wallet size={18} aria-hidden /><strong>Montée en charge sur un mois</strong></div>
        <div className="xp-bars">
          {weeks.map((w, i) => (
            <div key={w.label} className="xp-bar">
              <em>{euros.format(w.value)}</em>
              <i style={{ height: `${(w.value / max) * 100}%`, animationDelay: `${300 + i * 90}ms` }} />
              <span>{w.label}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card className="xp-flow" delay={3}>
        <div className="xp-card-title"><ChevronRight size={18} aria-hidden /><strong>Le chemin d’un crédit</strong></div>
        <ol>
          <li><b>1</b><div><strong>Scan au comptoir</strong><span>La visite est validée.</span></div></li>
          <li><b>2</b><div><strong>Relevé du lundi</strong><span>Toutes les visites de la semaine.</span></div></li>
          <li><b>3</b><div><strong>Virement</strong><span>0,90 € par crédit, sur votre compte.</span></div></li>
        </ol>
      </Card>

      <Card className="xp-payouts" delay={4}>
        <div className="xp-card-title"><Check size={18} aria-hidden /><strong>Derniers versements</strong></div>
        <ul>
          {PAYOUTS.map((p) => (
            <li key={p.week}><span>{p.week}</span><span>{p.visits} visites</span><b>{euros.format(p.amount)}</b><em>Versé</em></li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

/** Chiffre qui glisse vers sa nouvelle valeur. */
function useCountUp(target: number) {
  const [value, setValue] = useState(0);
  const from = useRef(0);
  useEffect(() => {
    const start = performance.now();
    const origin = from.current;
    let frame = 0;
    const tick = (now: number) => {
      const k = Math.min((now - start) / 700, 1);
      const v = origin + (target - origin) * (1 - Math.pow(1 - k, 3));
      from.current = v;
      setValue(v);
      if (k < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target]);
  return value;
}
