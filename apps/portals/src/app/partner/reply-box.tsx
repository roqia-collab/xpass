"use client";

import { Send } from "lucide-react";
import { useState, useTransition } from "react";

/** Zone de réponse (message ou réponse à un avis). Réponse immédiate : le texte s'affiche « Envoi… » et le champ se
 * vide tout de suite ; la liste réelle (rafraîchie par l'action serveur) le remplace, ou le texte revient si l'envoi échoue. */
export function ReplyBox({ label, placeholder, max, submit }: {
  label: string;
  placeholder: string;
  max: number;
  submit: (text: string) => Promise<{ ok: boolean; error?: string }>;
}) {
  const [text, setText] = useState("");
  const [pending, start] = useTransition();
  const [error, setError] = useState<string>();
  const [sending, setSending] = useState<string | null>(null);
  return (
    <>
    {sending && (
      <div className="list-row" aria-live="polite" style={{ opacity: 0.65, display: "flex", flexDirection: "column", gap: 4 }}>
        <span style={{ whiteSpace: "pre-wrap" }}>{sending}</span>
        <span className="muted" style={{ fontSize: 12 }}>Envoi…</span>
      </div>
    )}
    <form
      style={{ display: "flex", flexDirection: "column", gap: 8 }}
      onSubmit={(e) => {
        e.preventDefault();
        setError(undefined);
        const value = text.trim();
        setSending(value);
        setText("");
        start(async () => {
          const r = await submit(value);
          setSending(null);
          if (!r.ok) {
            setText(value);
            setError(r.error);
          }
        });
      }}
    >
      <label className="field">
        <span>{label}</span>
        <textarea value={text} onChange={(e) => setText(e.target.value)} maxLength={max} placeholder={placeholder} required />
      </label>
      <button className="btn primary" type="submit" disabled={pending || !text.trim()} style={{ alignSelf: "flex-end" }}>
        <Send size={16} aria-hidden /> Envoyer
      </button>
      {error && <p className="error" role="alert">{error}</p>}
    </form>
    </>
  );
}
