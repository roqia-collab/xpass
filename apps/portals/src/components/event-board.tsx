"use client";

import { useState, useTransition, type ChangeEvent } from "react";

import { Badge } from "@/components/ui";

export interface VenueOption {
  id: string;
  label: string;
}

export interface VenueEventRow {
  id: string;
  title: string;
  summary: string;
  starts_at: string;
  ends_at: string;
  price_credits: number;
  status: string;
  location_id: string;
  location_name: string;
  organization_name: string;
  district_label: string;
  cover_image_key: string | null;
  photoUrl: string | null;
}

type Save = (id: string | null, body: Record<string, unknown>) => Promise<{ ok: true; id: string } | { ok: false; error: string }>;
type Hide = (id: string, published: boolean) => Promise<{ ok: boolean; error?: string }>;
type Upload = (id: string, file: File) => Promise<{ ok: boolean; error?: string }>;

const day = new Intl.DateTimeFormat("fr-FR", { day: "numeric" });
const month = new Intl.DateTimeFormat("fr-FR", { month: "short" });
const clock = new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit" });
const full = new Intl.DateTimeFormat("fr-FR", { weekday: "long", day: "numeric", month: "long" });

function localInput(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function withZone(value: string) {
  const d = new Date(value);
  const off = -d.getTimezoneOffset();
  const sign = off >= 0 ? "+" : "-";
  const abs = Math.abs(off);
  const hh = String(Math.floor(abs / 60)).padStart(2, "0");
  const mm = String(abs % 60).padStart(2, "0");
  return `${value}:00${sign}${hh}:${mm}`;
}

function nextSession() {
  const d = new Date();
  const add = (6 - d.getDay() + 7) % 7 || 7;
  d.setDate(d.getDate() + add);
  const pad = (n: number) => String(n).padStart(2, "0");
  const dayKey = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  return { starts_at: `${dayKey}T18:00`, ends_at: `${dayKey}T20:00` };
}

function Editor({
  venues,
  initial,
  eventId,
  save,
  upload,
  onDone,
}: {
  venues: VenueOption[];
  initial: { location_id: string; title: string; summary: string; starts_at: string; ends_at: string; price_credits: string };
  eventId: string | null;
  save: Save;
  upload: Upload;
  onDone: () => void;
}) {
  const [form, setForm] = useState(initial);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const set = (key: string) => (e: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [key]: e.target.value });
  const venue = venues.find((v) => v.id === form.location_id);
  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 14 }}
      onSubmit={(e) => {
        e.preventDefault();
        setMsg(undefined);
        start(async () => {
          const res = await save(eventId, {
            location_id: form.location_id,
            title: form.title,
            summary: form.summary,
            starts_at: withZone(form.starts_at),
            ends_at: withZone(form.ends_at),
            price_credits: Number(form.price_credits),
          });
          if (!res.ok) {
            setMsg({ ok: false, text: res.error });
            return;
          }
          if (file) {
            const photo = await upload(res.id, file);
            if (!photo.ok) {
              setMsg({ ok: false, text: photo.error ?? "Photo refusée." });
              return;
            }
          }
          setMsg({ ok: true, text: "Événement publié. Il apparaît dans l’application." });
          onDone();
        });
      }}
    >
      <div>
        <p className="eyebrow">{eventId ? "Modification" : "Nouvel événement"}</p>
        <h3 style={{ marginTop: 6 }}>{eventId ? "Mettre à jour la séance" : "Publier une séance"}</h3>
        <p className="muted" style={{ marginTop: 6 }}>
          L’événement est rattaché à un commerçant déjà publié. Le client le voit dans l’application, avec la date, le lieu et le prix en crédits.
        </p>
      </div>
      <label className="field">
        <span>Commerçant</span>
        <select value={form.location_id} onChange={set("location_id")} required disabled={venues.length === 0}>
          {venues.length === 0 && <option value="">Aucun commerçant publié</option>}
          {venues.map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
        </select>
      </label>
      <label className="field">
        <span>Titre de la séance</span>
        <input value={form.title} onChange={set("title")} placeholder="Nocturne, cours, séance, représentation…" required />
      </label>
      <div className="grid grid-2">
        <label className="field"><span>Début</span><input type="datetime-local" value={form.starts_at} onChange={set("starts_at")} required /></label>
        <label className="field"><span>Fin</span><input type="datetime-local" value={form.ends_at} onChange={set("ends_at")} required /></label>
      </div>
      <label className="field">
        <span>Prix en crédits</span>
        <input type="number" min={1} max={500} value={form.price_credits} onChange={set("price_credits")} required />
      </label>
      <label className="field">
        <span>Ce que le client doit savoir</span>
        <textarea value={form.summary} onChange={set("summary")} placeholder="Durée, public, ce qui est inclus." />
      </label>
      <label className="field">
        <span>Photo de l’événement</span>
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => {
            const next = e.target.files?.[0] ?? null;
            setFile(next);
            setPreview(next ? URL.createObjectURL(next) : null);
          }}
        />
      </label>
      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        {preview ? (
          <img src={preview} alt="" style={{ width: 160, height: 100, objectFit: "cover", borderRadius: 14 }} />
        ) : (
          <span className="thumb" style={{ width: 160, height: 100 }} />
        )}
        <p className="muted" style={{ margin: 0, maxWidth: 420 }}>
          {venue ? venue.label : "Choisissez un commerçant."}
          {form.title ? ` · ${form.title}` : ""}
          {form.price_credits ? ` · ${form.price_credits} crédits` : ""}
          . Sans photo, celle de l’établissement est utilisée.
        </p>
      </div>
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button type="button" className="btn ghost" onClick={onDone}>Fermer</button>
        <button className="btn primary" disabled={pending || venues.length === 0}>
          {pending ? "Publication…" : eventId ? "Enregistrer" : "Publier dans l’application"}
        </button>
      </div>
    </form>
  );
}

export function EventBoard({
  events,
  venues,
  save,
  hide,
  upload,
}: {
  events: VenueEventRow[];
  venues: VenueOption[];
  save: Save;
  hide: Hide;
  upload: Upload;
}) {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const session = nextSession();
  const blank = {
    location_id: venues[0]?.id ?? "",
    title: "",
    summary: "",
    starts_at: session.starts_at,
    ends_at: session.ends_at,
    price_credits: "8",
  };
  const visible = events.filter((event) => event.status === "published").length;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <p className="muted" style={{ margin: 0 }}>
          {events.length === 0 ? "Aucune séance" : `${events.length} séance${events.length > 1 ? "s" : ""} · ${visible} visible${visible > 1 ? "s" : ""} dans l’application`}
        </p>
        {!open && !editing && (
          <button className="btn primary" onClick={() => setOpen(true)}>Ajouter un événement</button>
        )}
      </div>
      {open && <Editor venues={venues} initial={blank} eventId={null} save={save} upload={upload} onDone={() => setOpen(false)} />}
      {events.map((event) => {
        const published = event.status === "published";
        if (editing === event.id) {
          return (
            <Editor
              key={event.id}
              venues={venues}
              eventId={event.id}
              save={save}
              upload={upload}
              onDone={() => setEditing(null)}
              initial={{
                location_id: event.location_id,
                title: event.title,
                summary: event.summary,
                starts_at: localInput(event.starts_at),
                ends_at: localInput(event.ends_at),
                price_credits: String(event.price_credits),
              }}
            />
          );
        }
        return (
          <EventLine key={event.id} event={event} published={published} onEdit={() => setEditing(event.id)} hide={hide} />
        );
      })}
      {events.length === 0 && !open && (
        <section className="card">
          <h2>Aucune séance publiée</h2>
          <p className="muted">Ajoutez un événement sur un commerçant. Il s’affiche ensuite dans l’application, avec sa date et son prix.</p>
        </section>
      )}
    </div>
  );
}

function EventLine({ event, published, onEdit, hide }: { event: VenueEventRow; published: boolean; onEdit: () => void; hide: Hide }) {
  const [pending, begin] = useTransition();
  const [msg, setMsg] = useState<string>();
  const starts = new Date(event.starts_at);
  const ends = new Date(event.ends_at);
  return (
    <section className="card" style={{ display: "flex", gap: 16, alignItems: "stretch", flexWrap: "wrap" }}>
      {event.photoUrl ? (
        <img src={event.photoUrl} alt="" style={{ width: 200, height: 132, objectFit: "cover", borderRadius: 16 }} />
      ) : (
        <span className="thumb" style={{ width: 200, height: 132 }} />
      )}
      <div style={{ width: 76, textAlign: "center", background: "var(--cream)", borderRadius: 16, padding: "12px 8px", alignSelf: "center" }}>
        <div className="eyebrow">{month.format(starts).replace(".", "")}</div>
        <div style={{ fontFamily: "Syne, sans-serif", fontSize: 28, lineHeight: 1.1 }}>{day.format(starts)}</div>
        <div style={{ fontSize: 13, marginTop: 4 }}>{clock.format(starts)}</div>
      </div>
      <div style={{ flex: 1, minWidth: 220, display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ display: "flex", gap: 10, alignItems: "baseline", flexWrap: "wrap" }}>
          <h2 style={{ margin: 0 }}>{event.title}</h2>
          <Badge tone={published ? "mint" : "grey"}>{published ? "Dans l’application" : "Retiré"}</Badge>
        </div>
        <p className="muted" style={{ margin: 0 }}>
          {event.organization_name} · {event.location_name} · {event.district_label}
        </p>
        <p style={{ margin: 0 }}>
          {full.format(starts)} · {clock.format(starts)} – {clock.format(ends)} · {event.price_credits} crédits
        </p>
        {event.summary && <p className="muted" style={{ margin: 0 }}>{event.summary}</p>}
        <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
          <button className="btn outline" onClick={onEdit}>Modifier</button>
          <button
            className="btn ghost"
            disabled={pending}
            onClick={() => {
              if (!window.confirm(published ? "Retirer cet événement de l’application ?" : "Republier cet événement ?")) return;
              begin(async () => {
                const res = await hide(event.id, !published);
                setMsg(res.ok ? "" : res.error);
              });
            }}
          >
            {published ? "Retirer de l’application" : "Remettre"}
          </button>
        </div>
        {msg && <p className="error">{msg}</p>}
      </div>
    </section>
  );
}
