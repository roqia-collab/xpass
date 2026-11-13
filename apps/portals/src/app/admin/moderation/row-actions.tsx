"use client";

import { useState, useTransition } from "react";

import { moderateLocation } from "../actions";

/** Publier ou retirer un établissement depuis la liste, avec un motif. */
export function ModerationActions({ id, published }: { id: string; published: boolean }) {
  const [reason, setReason] = useState("");
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  return (
    <form
      style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}
      onSubmit={(e) => {
        e.preventDefault();
        start(async () => {
          const res = await moderateLocation(id, !published, reason);
          setMsg(res.ok
            ? { ok: true, text: published ? "Retiré de l’application." : "Publié dans l’application." }
            : { ok: false, text: res.error });
        });
      }}
    >
      <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Motif" aria-label="Motif" required style={{ minWidth: 140 }} />
      <button className="btn outline" disabled={pending}>{published ? "Supprimer" : "Ajouter"}</button>
      {msg && <span className={msg.ok ? "muted" : "error"}>{msg.text}</span>}
    </form>
  );
}
