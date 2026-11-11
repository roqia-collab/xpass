"use client";

import { useState, useTransition } from "react";

import { createMerchant, locateAddress, setMerchantVisibility, updateMerchant, uploadMerchantPhoto } from "./actions";

export interface MerchantDraft {
  display_name: string;
  owner_email: string;
  location_name: string;
  subcategory_slug: string;
  address_line: string;
  postal_code: string;
  city: string;
  description: string;
  price_credits: string;
}

const empty = (slug: string): MerchantDraft => ({
  display_name: "", owner_email: "", location_name: "", subcategory_slug: slug,
  address_line: "", postal_code: "", city: "Paris", description: "", price_credits: "8",
});

function Fields({
  categories,
  initial,
  merchantId,
  onDone,
}: {
  categories: { name: string; subs: { slug: string; name: string }[] }[];
  initial: MerchantDraft;
  merchantId?: string;
  onDone?: () => void;
}) {
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const [place, setPlace] = useState<{ label: string; latitude: number; longitude: number } | null>(null);
  const [form, setForm] = useState(initial);
  const [file, setFile] = useState<File | null>(null);
  const set = (key: keyof MerchantDraft) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setPlace(null);
    setForm({ ...form, [key]: e.target.value });
  };
  const locate = () => {
    setMsg(undefined);
    start(async () => {
      const res = await locateAddress(form);
      if (!res.ok || !res.data) {
        setPlace(null);
        setMsg({ ok: false, text: res.ok ? "Adresse introuvable." : res.error });
        return;
      }
      setPlace(res.data);
      setMsg({ ok: true, text: `Adresse confirmée : ${res.data.label}` });
    });
  };
  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
      onSubmit={(e) => {
        e.preventDefault();
        if (!place) {
          setMsg({ ok: false, text: "Vérifiez l’adresse avant d’enregistrer. Elle doit exister dans la Base Adresse Nationale." });
          return;
        }
        setMsg(undefined);
        start(async () => {
          const res = merchantId ? await updateMerchant(merchantId, form) : await createMerchant(form);
          if (!res.ok) {
            setMsg({ ok: false, text: res.error });
            return;
          }
          const created = res.data as { id?: string } | null;
          const id = merchantId ?? created?.id ?? "";
          if (file && id) {
            const body = new FormData();
            body.set("file", file);
            const photo = await uploadMerchantPhoto(id, body);
            if (!photo.ok) {
              setMsg({ ok: false, text: photo.error });
              return;
            }
          }
          setMsg({ ok: true, text: merchantId ? "Commerçant mis à jour." : "Commerçant publié dans l’application, avec cette adresse." });
          onDone?.();
        });
      }}
    >
      <h3>{merchantId ? "Modifier le commerçant" : "Nouveau commerçant"}</h3>
      <p className="muted" style={{ fontSize: 14 }}>
        L’adresse est vérifiée sur la carte officielle. La photo apparaît dans l’application. Seule Paris est ouverte.
      </p>
      <label className="field"><span>Nom commercial</span><input value={form.display_name} onChange={set("display_name")} required /></label>
      <label className="field"><span>E-mail du responsable</span><input type="email" value={form.owner_email} onChange={set("owner_email")} required /></label>
      <label className="field"><span>Nom de l’établissement</span><input value={form.location_name} onChange={set("location_name")} required /></label>
      <label className="field">
        <span>Activité</span>
        <select value={form.subcategory_slug} onChange={set("subcategory_slug")}>
          {categories.map((c) => (
            <optgroup key={c.name} label={c.name}>
              {c.subs.map((s) => <option key={s.slug} value={s.slug}>{s.name}</option>)}
            </optgroup>
          ))}
        </select>
      </label>
      <label className="field"><span>Numéro et rue</span><input value={form.address_line} onChange={set("address_line")} placeholder="5 rue de la Roquette" required /></label>
      <div className="grid grid-2">
        <label className="field"><span>Code postal</span><input value={form.postal_code} onChange={set("postal_code")} placeholder="75011" required /></label>
        <label className="field"><span>Ville</span><input value={form.city} onChange={set("city")} required /></label>
      </div>
      <button type="button" className="btn outline" style={{ alignSelf: "flex-start" }} disabled={pending} onClick={locate}>
        Vérifier l’adresse
      </button>
      {place && (
        <p className="notice mint">
          {place.label}
          {" · "}
          <a href={`https://www.openstreetmap.org/?mlat=${place.latitude}&mlon=${place.longitude}#map=17/${place.latitude}/${place.longitude}`} target="_blank" rel="noreferrer">Voir sur la carte</a>
        </p>
      )}
      <label className="field"><span>Prix de la prestation (crédits)</span><input type="number" min={1} max={500} value={form.price_credits} onChange={set("price_credits")} required /></label>
      <label className="field"><span>Description</span><textarea value={form.description} onChange={set("description")} /></label>
      <label className="field">
        <span>Photo de l’établissement</span>
        <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      </label>
      <span className="muted" style={{ fontSize: 13 }}>JPEG, PNG ou WebP, 8 Mo maximum, au moins 400 pixels de côté.</span>
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        {onDone && <button type="button" className="btn ghost" onClick={onDone}>Fermer</button>}
        <button className="btn primary" disabled={pending || !place}>{merchantId ? "Enregistrer" : "Publier dans l’application"}</button>
      </div>
    </form>
  );
}

export function CreateMerchantForm({ categories }: { categories: { name: string; subs: { slug: string; name: string }[] }[] }) {
  const [open, setOpen] = useState(false);
  const first = categories[0]?.subs[0]?.slug ?? "";
  if (!open) return <button className="btn primary" onClick={() => setOpen(true)}>Ajouter un commerçant</button>;
  return <Fields categories={categories} initial={empty(first)} onDone={() => setOpen(false)} />;
}

export function EditMerchantForm({
  categories,
  merchantId,
  initial,
  published,
  onDone,
}: {
  categories: { name: string; subs: { slug: string; name: string }[] }[];
  merchantId: string;
  initial: MerchantDraft;
  published: boolean;
  onDone: () => void;
}) {
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<string>();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Fields categories={categories} initial={initial} merchantId={merchantId} onDone={onDone} />
      <button
        type="button"
        className="btn ghost"
        disabled={pending}
        onClick={() => {
          const verb = published ? "Retirer cet établissement de l’application ?" : "Republier cet établissement dans l’application ?";
          if (!window.confirm(verb)) return;
          start(async () => {
            const res = await setMerchantVisibility(merchantId, !published);
            setMsg(res.ok ? (published ? "Retiré de l’application." : "De nouveau visible.") : res.error);
            if (res.ok) onDone();
          });
        }}
      >
        {published ? "Supprimer de l’application" : "Remettre dans l’application"}
      </button>
      {msg && <p className="muted">{msg}</p>}
    </div>
  );
}
