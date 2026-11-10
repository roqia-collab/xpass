"use client";

import { ImagePlus } from "lucide-react";
import { useRef, useState, useTransition } from "react";

import { uploadPhoto } from "./photo-actions";

/** Envoi d'une photo : JPEG, PNG ou WebP, 8 Mo maximum, 400 px minimum de côté (contrôlé par l'API). */
export function PhotoUpload({ locationId, offerId = null, current, label }: { locationId: string; offerId?: string | null; current: string | null; label: string }) {
  const input = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(current);
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  return (
    <div className="card" style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
      {preview ? (
        <img src={preview} alt="" style={{ width: 180, height: 120, objectFit: "cover", borderRadius: 14 }} />
      ) : (
        <span className="thumb" style={{ width: 180, height: 120, display: "grid", placeItems: "center" }}><ImagePlus aria-hidden /></span>
      )}
      <form
        style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1, minWidth: 220 }}
        onSubmit={(e) => {
          e.preventDefault();
          const data = new FormData(e.currentTarget);
          setMsg(undefined);
          start(async () => {
            const r = await uploadPhoto(locationId, offerId, data);
            setMsg(r.ok ? { ok: true, text: "Photo enregistrée." } : { ok: false, text: r.error });
            if (r.ok && input.current) input.current.value = "";
          });
        }}
      >
        <label className="field">
          <span>{label}</span>
          <input
            ref={input}
            type="file"
            name="file"
            accept="image/jpeg,image/png,image/webp"
            required
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) setPreview(URL.createObjectURL(f));
            }}
          />
        </label>
        <span className="muted" style={{ fontSize: 13 }}>JPEG, PNG ou WebP, 8 Mo maximum. Utilisez une photo dont vous avez les droits.</span>
        <button className="btn outline" type="submit" disabled={pending} style={{ alignSelf: "flex-start" }}>
          {pending ? "Envoi…" : "Enregistrer la photo"}
        </button>
        {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
      </form>
    </div>
  );
}
