"use client";

import { ImagePlus, Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { BookingModeEditable, ManagedLocation, PartnerBlock } from "@/lib/types";

import * as actions from "./manage-actions";
import { uploadPhoto } from "./photo-actions";

type Result = Awaited<ReturnType<typeof actions.saveHours>>;

/** Exécute une action serveur et affiche son résultat réel (jamais de succès supposé). */
function useAction() {
  const [pending, start] = useTransition();
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string }>();
  const run = (fn: () => Promise<Result>, success: string, after?: () => void) => {
    setMessage(undefined);
    start(async () => {
      const res = await fn();
      if (!res.ok) {
        setMessage({ tone: "error", text: res.error });
        return;
      }
      const warn = res.bookingsOutsideHours
        ? ` Attention : ${res.bookingsOutsideHours} réservation(s) à venir tombent hors des horaires. Elles restent maintenues ; contactez les clients si nécessaire.`
        : "";
      setMessage({ tone: "ok", text: success + warn });
      after?.();
    });
  };
  const feedback = message && (
    <p role={message.tone === "error" ? "alert" : "status"} className={message.tone === "error" ? "error" : "notice mint"}>
      {message.text}
    </p>
  );
  return { pending, run, feedback };
}

const DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];
const MODE_LABEL: Record<BookingModeEditable, string> = {
  resource_slot: "Sur rendez-vous (avec un professionnel)",
  capacity_session: "Séance à capacité (cours, atelier)",
  open_access: "Accès libre avec capacité",
};

// ---------------------------------------------------------------- prestation

type Offer = ManagedLocation["offers"][number];

export function OfferEditor({ location, offer, currentPhoto = null }: { location: ManagedLocation; offer?: Offer; currentPhoto?: string | null }) {
  const router = useRouter();
  const { pending, run, feedback } = useAction();
  const [preview, setPreview] = useState<string | null>(currentPhoto);
  const [photo, setPhoto] = useState<File | null>(null);
  const [createdId, setCreatedId] = useState<string | null>(null);
  const v = offer?.current;
  const [mode, setMode] = useState<BookingModeEditable>(
    offer && offer.booking_mode !== "external_ticket" ? offer.booking_mode : "resource_slot",
  );
  const [form, setForm] = useState({
    title: v?.title ?? "",
    summary: v?.summary ?? "",
    duration_min: String(v?.duration_min ?? 30),
    price_credits: String(v?.price_credits ?? ""),
    participants_min: String(v?.participants_min ?? 1),
    participants_max: String(v?.participants_max ?? 1),
    capacity: v?.capacity ? String(v.capacity) : "",
    free_cancellation_hours: String(v?.free_cancellation_hours ?? 24),
  });
  const [resourceIds, setResourceIds] = useState<string[]>(offer?.resource_ids ?? []);
  const [publish, setPublish] = useState(false);
  const readOnly = !location.can_edit || offer?.booking_mode === "external_ticket";
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.value });

  const sendPhoto = async (offerId: string, file: File) => {
    const data = new FormData();
    data.set("file", file, file.name);
    return uploadPhoto(location.id, offerId, data);
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload = { ...form, capacity: mode === "resource_slot" || !form.capacity ? null : form.capacity, resource_ids: resourceIds };
    run(
      async () => {
        const knownId = offer?.id ?? createdId;
        const res = await actions.saveOffer(location.id, knownId, payload, knownId ? undefined : { booking_mode: mode, publish });
        if (!res.ok) return res;
        if (res.id) setCreatedId(res.id);
        if (!photo) return res;
        const offerId = knownId ?? res.id;
        if (!offerId) return { ok: false, error: "Prestation créée, mais la photo n’a pas pu être liée." };
        const up = await sendPhoto(offerId, photo);
        if (!up.ok) return { ok: false, error: `La prestation est enregistrée. La photo n’a pas été envoyée : ${up.error} Vous pouvez la renvoyer.` };
        return res;
      },
      offer ? "Nouvelle version enregistrée. Les réservations existantes gardent leur prix." : "Prestation créée.",
      () => !offer && router.push("/partner/prestations"),
    );
  };

  return (
    <form onSubmit={submit} className="card side-panel" aria-label={offer ? "Modifier la prestation" : "Créer une prestation"}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3>{offer ? "Modifier la prestation" : "Créer une prestation"}</h3>
        <a href="/partner/prestations" className="btn ghost" aria-label="Fermer">✕</a>
      </div>
      {offer && (
        <p className="muted" style={{ fontSize: 13 }}>
          Version {offer.current.version} · chaque enregistrement crée une nouvelle version ; les réservations déjà faites
          conservent prix, durée et conditions d’annulation.
        </p>
      )}
      <label className="field">
        <span>Nom de la prestation</span>
        <input value={form.title} onChange={set("title")} disabled={readOnly} required maxLength={120} />
      </label>
      <label className="field">
        <span>Crédits</span>
        <input type="number" min={1} value={form.price_credits} onChange={set("price_credits")} disabled={readOnly} required />
        <small className="muted">Prix payé par le salarié. Ce nombre de crédits s’affiche dans l’application.</small>
      </label>
      <label className="field">
        <span>Description</span>
        <textarea value={form.summary} onChange={set("summary")} disabled={readOnly} maxLength={240} />
      </label>
      <div>
        <strong>Photos</strong>
        <p className="muted" style={{ fontSize: 13, margin: "4px 0 10px" }}>
          Cette photo s’affiche dans l’application, sur la fiche de la prestation.
        </p>
        <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
          {preview ? (
            <img src={preview} alt="" style={{ width: 180, height: 120, objectFit: "cover", borderRadius: 14 }} />
          ) : (
            <span className="thumb" style={{ width: 180, height: 120, display: "grid", placeItems: "center" }}><ImagePlus aria-hidden /></span>
          )}
          <label className="field" style={{ flex: 1, minWidth: 180 }}>
            <span>Photo</span>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={readOnly}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                setPhoto(file);
                setPreview(URL.createObjectURL(file));
              }}
            />
            <small className="muted">JPEG, PNG ou WebP, 8 Mo maximum, 400 pixels minimum de côté.</small>
          </label>
        </div>
      </div>
      {!offer && (
        <label className="field">
          <span>Mode de réservation</span>
          <select value={mode} onChange={(e) => setMode(e.target.value as BookingModeEditable)}>
            {Object.entries(MODE_LABEL).map(([k, l]) => (
              <option key={k} value={k}>{l}</option>
            ))}
          </select>
        </label>
      )}
      <strong>Durée et tarification</strong>
      <div className="form-grid">
        <label className="field">
          <span>Durée</span>
          <select value={form.duration_min} onChange={set("duration_min")} disabled={readOnly}>
            {[15, 30, 45, 60, 75, 90, 120, 150, 180, 240].map((d) => (
              <option key={d} value={d}>{d < 60 ? `${d} min` : `${Math.floor(d / 60)} h${d % 60 ? ` ${d % 60}` : ""}`}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Annulation gratuite (heures avant)</span>
          <input type="number" min={0} max={168} value={form.free_cancellation_hours} onChange={set("free_cancellation_hours")} disabled={readOnly} />
        </label>
      </div>
      <div className="form-grid">
        <label className="field">
          <span>Participants min.</span>
          <input type="number" min={1} value={form.participants_min} onChange={set("participants_min")} disabled={readOnly} />
        </label>
        <label className="field">
          <span>Participants max.</span>
          <input type="number" min={1} value={form.participants_max} onChange={set("participants_max")} disabled={readOnly} />
        </label>
        {mode !== "resource_slot" && (
          <label className="field">
            <span>Capacité de la séance</span>
            <input type="number" min={1} value={form.capacity} onChange={set("capacity")} disabled={readOnly} required />
          </label>
        )}
      </div>
      {mode === "resource_slot" && (
        <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
          <legend><strong>Professionnels et ressources</strong></legend>
          <p className="muted" style={{ fontSize: 13 }}>Sélectionnez qui peut réaliser cette prestation.</p>
          {location.resources.filter((r) => r.is_active).map((r) => (
            <label key={r.id} className="check-row">
              <input
                type="checkbox"
                checked={resourceIds.includes(r.id)}
                disabled={readOnly}
                onChange={(e) => setResourceIds(e.target.checked ? [...resourceIds, r.id] : resourceIds.filter((x) => x !== r.id))}
              />
              <span>{r.name}</span>
              <span className="pill">{r.role_label}</span>
            </label>
          ))}
        </fieldset>
      )}
      {!offer && (
        <label className="check-row">
          <input type="checkbox" checked={publish} onChange={(e) => setPublish(e.target.checked)} />
          <span>Publier immédiatement (sinon : brouillon, invisible des clients)</span>
        </label>
      )}
      {feedback}
      {readOnly ? (
        <p className="muted">
          {offer?.booking_mode === "external_ticket"
            ? "Billet externe : configuré par l’équipe XPASS."
            : "Lecture seule : seul le responsable de l’établissement peut modifier les prestations."}
        </p>
      ) : (
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <a className="btn outline" href="/partner/prestations">Annuler</a>
          <button className="btn primary" type="submit" disabled={pending}>{pending ? "Enregistrement…" : "Enregistrer"}</button>
        </div>
      )}
    </form>
  );
}

export function OfferActiveToggle({ locationId, offerId, active, canEdit }: { locationId: string; offerId: string; active: boolean; canEdit: boolean }) {
  const { pending, run, feedback } = useAction();
  if (!canEdit) return null;
  return (
    <div>
      <button
        className="btn ghost"
        disabled={pending}
        onClick={() => run(() => actions.setOfferActive(locationId, offerId, !active), active ? "Prestation retirée de la vente." : "Prestation publiée.")}
      >
        {active ? "Dépublier" : "Publier"}
      </button>
      {feedback}
    </div>
  );
}

// ---------------------------------------------------------------- équipe

export function TeamManager({ location }: { location: ManagedLocation }) {
  const { pending, run, feedback } = useAction();
  const [draft, setDraft] = useState({ kind: "staff" as "staff" | "equipment" | "room", name: "", role_label: "" });
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="grid grid-3">
        {location.resources.map((r) => (
          <ResourceCard key={r.id} locationId={location.id} resource={r} canEdit={location.can_edit} />
        ))}
      </div>
      {location.can_edit && (
        <form
          className="card"
          onSubmit={(e) => {
            e.preventDefault();
            run(() => actions.createResource(location.id, draft), `${draft.name} ajouté(e) à l’équipe.`, () =>
              setDraft({ ...draft, name: "", role_label: "" }),
            );
          }}
          style={{ display: "flex", flexDirection: "column", gap: 12 }}
        >
          <h3>Ajouter un membre ou une ressource</h3>
          <div className="form-grid">
            <label className="field">
              <span>Type</span>
              <select value={draft.kind} onChange={(e) => setDraft({ ...draft, kind: e.target.value as typeof draft.kind })}>
                <option value="staff">Professionnel</option>
                <option value="room">Salle</option>
                <option value="equipment">Équipement</option>
              </select>
            </label>
            <label className="field">
              <span>Nom</span>
              <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} required maxLength={80} />
            </label>
            <label className="field">
              <span>Rôle ou description</span>
              <input value={draft.role_label} onChange={(e) => setDraft({ ...draft, role_label: e.target.value })} required maxLength={80} placeholder="Coiffeuse, Fauteuil…" />
            </label>
          </div>
          {feedback}
          <button className="btn primary" type="submit" disabled={pending} style={{ alignSelf: "flex-start" }}>
            <Plus size={18} /> {pending ? "Ajout…" : "Ajouter"}
          </button>
        </form>
      )}
    </div>
  );
}

function ResourceCard({ locationId, resource, canEdit }: { locationId: string; resource: ManagedLocation["resources"][number]; canEdit: boolean }) {
  const { pending, run, feedback } = useAction();
  const [name, setName] = useState(resource.name);
  const [role, setRole] = useState(resource.role_label);
  const save = (active: boolean) =>
    run(() => actions.updateResource(locationId, resource.id, { name, role_label: role, active }), active ? "Enregistré." : "Désactivé(e).");
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10, opacity: resource.is_active ? 1 : 0.65 }}>
      <label className="field">
        <span className="muted" style={{ fontSize: 13 }}>Nom</span>
        <input value={name} onChange={(e) => setName(e.target.value)} disabled={!canEdit} aria-label={`Nom de ${resource.name}`} />
      </label>
      <label className="field">
        <span className="muted" style={{ fontSize: 13 }}>Rôle</span>
        <input value={role} onChange={(e) => setRole(e.target.value)} disabled={!canEdit} aria-label={`Rôle de ${resource.name}`} />
      </label>
      <span className="muted" style={{ fontSize: 13 }}>{resource.is_active ? "Actif" : "Désactivé"}</span>
      {feedback}
      {canEdit && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="btn outline" disabled={pending} onClick={() => save(resource.is_active)}>Enregistrer</button>
          <button className="btn ghost" disabled={pending} onClick={() => save(!resource.is_active)}>
            {resource.is_active ? "Désactiver" : "Réactiver"}
          </button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- établissement

export function LocationForm({ location }: { location: ManagedLocation }) {
  const { pending, run, feedback } = useAction();
  const [form, setForm] = useState({
    description: location.description,
    access_info: location.access_info ?? "",
    meeting_point: location.meeting_point ?? "",
    wheelchair_accessible: location.wheelchair_accessible,
    review_url: location.review_url ?? "",
  });
  const ro = !location.can_edit;
  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
      onSubmit={(e) => {
        e.preventDefault();
        run(
          () =>
            actions.updateLocation(location.id, {
              ...form,
              access_info: form.access_info || null,
              meeting_point: form.meeting_point || null,
              review_url: form.review_url || null,
            }),
          "Informations enregistrées.",
        );
      }}
    >
      <h3>Informations publiques</h3>
      <label className="field">
        <span>Description</span>
        <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} disabled={ro} maxLength={2000} />
      </label>
      <label className="field">
        <span>Accès (transports, étage…)</span>
        <input value={form.access_info} onChange={(e) => setForm({ ...form, access_info: e.target.value })} disabled={ro} maxLength={240} />
      </label>
      <label className="field">
        <span>Point de rendez-vous</span>
        <input value={form.meeting_point} onChange={(e) => setForm({ ...form, meeting_point: e.target.value })} disabled={ro} maxLength={240} />
      </label>
      <label className="field">
        <span>Lien d’avis Google (proposé au client après sa visite)</span>
        <input type="url" placeholder="https://…" value={form.review_url} onChange={(e) => setForm({ ...form, review_url: e.target.value })} disabled={ro} />
      </label>
      <label className="check-row">
        <input type="checkbox" checked={form.wheelchair_accessible} onChange={(e) => setForm({ ...form, wheelchair_accessible: e.target.checked })} disabled={ro} />
        <span>Accessible aux personnes à mobilité réduite</span>
      </label>
      {feedback}
      {!ro && <button className="btn primary" type="submit" disabled={pending} style={{ alignSelf: "flex-start" }}>{pending ? "Enregistrement…" : "Enregistrer"}</button>}
    </form>
  );
}

export function HoursEditor({ location }: { location: ManagedLocation }) {
  const { pending, run, feedback } = useAction();
  const [rows, setRows] = useState(location.hours.map((h) => ({ ...h, opens_at: h.opens_at.slice(0, 5), closes_at: h.closes_at.slice(0, 5) })));
  const ro = !location.can_edit;
  const update = (i: number, patch: Partial<(typeof rows)[number]>) => setRows(rows.map((r, j) => (i === j ? { ...r, ...patch } : r)));
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <h3>Horaires hebdomadaires</h3>
      {DAYS.map((label, day) => {
        const items = rows.map((r, i) => [r, i] as const).filter(([r]) => r.weekday === day);
        return (
          <div key={label} style={{ display: "grid", gridTemplateColumns: "110px 1fr auto", gap: 10, alignItems: "center" }}>
            <strong>{label}</strong>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {items.length === 0 && <span className="muted">Fermé</span>}
              {items.map(([r, i]) => (
                <span key={i} className="pill">
                  <input type="time" aria-label={`${label} ouverture`} value={r.opens_at} disabled={ro} onChange={(e) => update(i, { opens_at: e.target.value })} />
                  –
                  <input type="time" aria-label={`${label} fermeture`} value={r.closes_at} disabled={ro} onChange={(e) => update(i, { closes_at: e.target.value })} />
                  {!ro && (
                    <button type="button" className="btn ghost" aria-label={`Supprimer la plage du ${label}`} onClick={() => setRows(rows.filter((_, j) => j !== i))}>
                      <Trash2 size={16} />
                    </button>
                  )}
                </span>
              ))}
            </div>
            {!ro && (
              <button type="button" className="btn ghost" aria-label={`Ajouter une plage le ${label}`} onClick={() => setRows([...rows, { weekday: day, opens_at: "09:00", closes_at: "18:00" }])}>
                <Plus size={16} />
              </button>
            )}
          </div>
        );
      })}
      {feedback}
      {!ro && (
        <button className="btn primary" disabled={pending} style={{ alignSelf: "flex-start" }} onClick={() => run(() => actions.saveHours(location.id, rows), "Horaires enregistrés.")}>
          {pending ? "Enregistrement…" : "Enregistrer les horaires"}
        </button>
      )}
    </div>
  );
}

export function ExceptionsManager({ location }: { location: ManagedLocation }) {
  const { pending, run, feedback } = useAction();
  const [draft, setDraft] = useState({ day: "", is_closed: true, opens_at: "10:00", closes_at: "16:00", reason: "" });
  const ro = !location.can_edit;
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <h3>Fermetures et horaires exceptionnels</h3>
      {location.exceptions.length === 0 && <p className="muted">Aucune fermeture à venir.</p>}
      {location.exceptions.map((e) => (
        <div key={e.id} className="list-row" style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <strong style={{ width: 140 }}>
            {new Intl.DateTimeFormat("fr-FR", { weekday: "short", day: "numeric", month: "long" }).format(new Date(`${e.day}T12:00:00Z`))}
          </strong>
          <span style={{ flex: 1 }}>
            {e.is_closed ? "Fermé" : `${e.opens_at} – ${e.closes_at}`}
            {e.reason ? ` · ${e.reason}` : ""}
          </span>
          {!ro && (
            <button className="btn ghost" disabled={pending} aria-label="Supprimer cette fermeture" onClick={() => run(() => actions.deleteException(location.id, e.id), "Fermeture supprimée.")}>
              <Trash2 size={16} />
            </button>
          )}
        </div>
      ))}
      {!ro && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            run(
              () =>
                actions.addException(location.id, {
                  day: draft.day,
                  is_closed: draft.is_closed,
                  opens_at: draft.is_closed ? null : draft.opens_at,
                  closes_at: draft.is_closed ? null : draft.closes_at,
                  reason: draft.reason || null,
                }),
              "Exception enregistrée : les créneaux de ce jour sont mis à jour.",
            );
          }}
          className="form-grid"
          style={{ alignItems: "end" }}
        >
          <label className="field">
            <span>Date</span>
            <input type="date" value={draft.day} onChange={(e) => setDraft({ ...draft, day: e.target.value })} required />
          </label>
          <label className="field">
            <span>Type</span>
            <select value={draft.is_closed ? "closed" : "special"} onChange={(e) => setDraft({ ...draft, is_closed: e.target.value === "closed" })}>
              <option value="closed">Fermé toute la journée</option>
              <option value="special">Horaires spéciaux</option>
            </select>
          </label>
          {!draft.is_closed && (
            <>
              <label className="field">
                <span>Ouverture</span>
                <input type="time" value={draft.opens_at} onChange={(e) => setDraft({ ...draft, opens_at: e.target.value })} />
              </label>
              <label className="field">
                <span>Fermeture</span>
                <input type="time" value={draft.closes_at} onChange={(e) => setDraft({ ...draft, closes_at: e.target.value })} />
              </label>
            </>
          )}
          <label className="field">
            <span>Motif (facultatif)</span>
            <input value={draft.reason} onChange={(e) => setDraft({ ...draft, reason: e.target.value })} maxLength={160} />
          </label>
          <button className="btn primary" type="submit" disabled={pending}>Ajouter</button>
        </form>
      )}
      {feedback}
    </div>
  );
}

// ---------------------------------------------------------------- blocages (planning)

export function BlockForm({ location, day, blocks }: { location: ManagedLocation; day: string; blocks: PartnerBlock[] }) {
  const { pending, run, feedback } = useAction();
  const active = location.resources.filter((r) => r.is_active);
  const [draft, setDraft] = useState({ resource_id: active[0]?.id ?? "", start: "12:00", end: "13:00", reason: "" });
  if (!active.length) return null;
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }} id="bloquer">
      <strong>Bloquer une plage</strong>
      <p className="muted" style={{ fontSize: 13 }}>Rendez-vous pris hors XPASS, pause, absence : la plage n’est plus réservable.</p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(
            () =>
              actions.createBlock(location.id, {
                resource_id: draft.resource_id,
                local_start: `${day}T${draft.start}`,
                local_end: `${day}T${draft.end}`,
                reason: draft.reason,
              }),
            "Plage bloquée.",
            () => setDraft({ ...draft, reason: "" }),
          );
        }}
        style={{ display: "flex", flexDirection: "column", gap: 8 }}
      >
        <label className="field">
          <span>Ressource</span>
          <select value={draft.resource_id} onChange={(e) => setDraft({ ...draft, resource_id: e.target.value })}>
            {active.map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        </label>
        <div style={{ display: "flex", gap: 8 }}>
          <label className="field" style={{ flex: 1 }}>
            <span>De</span>
            <input type="time" value={draft.start} onChange={(e) => setDraft({ ...draft, start: e.target.value })} />
          </label>
          <label className="field" style={{ flex: 1 }}>
            <span>À</span>
            <input type="time" value={draft.end} onChange={(e) => setDraft({ ...draft, end: e.target.value })} />
          </label>
        </div>
        <label className="field">
          <span>Motif</span>
          <input value={draft.reason} onChange={(e) => setDraft({ ...draft, reason: e.target.value })} required minLength={2} maxLength={160} />
        </label>
        <button className="btn primary" type="submit" disabled={pending}>{pending ? "Blocage…" : "Bloquer"}</button>
      </form>
      {feedback}
      {blocks.map((b) => (
        <div key={b.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14 }}>
          <span style={{ flex: 1 }}>
            {b.local_start.slice(11)}–{b.local_end.slice(11)} · {b.resource_name} · {b.reason}
          </span>
          <button className="btn ghost" disabled={pending} aria-label={`Débloquer ${b.reason}`} onClick={() => run(() => actions.deleteBlock(location.id, b.id), "Plage débloquée.")}>
            <Trash2 size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}
