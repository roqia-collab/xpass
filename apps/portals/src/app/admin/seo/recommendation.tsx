"use client";

import { useState, useTransition } from "react";

import { Badge } from "@/components/ui";
import { PRIORITY_LABEL, RECO_STATUS_LABEL, SEO_FIELD_LABEL, type SeoRecommendation } from "@/lib/seo";

import { applyRecommendation, rejectRecommendation, revertChange, type SeoActionResult, validateRecommendation } from "./actions";

const fmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short", timeZone: "Europe/Paris" });

function Value({ label, value, empty = "— (vide)" }: { label: string; value: string | null; empty?: string }) {
  return (
    <div className="seo-value">
      <span className="muted">{label}</span>
      <code>{value === null || value === "" ? empty : value}</code>
    </div>
  );
}

/**
 * Une recommandation : Valider, Rejeter, Modifier avant validation, Appliquer (avec confirmation explicite).
 * Les valeurs sont affichées comme du texte (React échappe tout) ; rien n’est interprété comme du HTML.
 */
export function RecommendationCard({ reco, defaultValue }: { reco: SeoRecommendation; defaultValue: string | null }) {
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const [note, setNote] = useState("");
  const [editing, setEditing] = useState(false);
  const [edited, setEdited] = useState(reco.proposed_value ?? "");
  const [confirming, setConfirming] = useState(false);
  const [checked, setChecked] = useState(false);
  const status = RECO_STATUS_LABEL[reco.status];
  const live = reco.live_value ?? defaultValue;
  const fieldLabel = reco.field ? SEO_FIELD_LABEL[reco.field] : reco.category;
  const canDecide = reco.status !== "applied";

  const run = (fn: () => Promise<SeoActionResult>, success: string) => {
    setMsg(undefined);
    start(async () => {
      const res = await fn();
      setMsg(res.ok ? { ok: true, text: success } : { ok: false, text: res.error });
      if (res.ok) {
        setNote("");
        setEditing(false);
        setConfirming(false);
        setChecked(false);
      }
    });
  };

  return (
    <article className="card seo-reco">
      <div className="request-line">
        <Badge tone={status.tone}>{status.label}</Badge>
        <Badge tone={reco.priority === "critical" || reco.priority === "high" ? "coral" : "grey"}>
          Priorité {PRIORITY_LABEL[reco.priority] ?? reco.priority}
        </Badge>
        <Badge tone="lavender">{fieldLabel}</Badge>
        <span className="muted">#{reco.external_id}</span>
      </div>
      <p style={{ marginTop: 8 }}><strong>{reco.issue}</strong></p>
      <p className="muted" style={{ fontSize: 14 }}>
        Page : <span style={{ wordBreak: "break-all" }}>{reco.page_url}</span>
        {reco.reason && <> · {reco.reason}</>}
      </p>
      <div className="seo-values">
        <Value label="Valeur constatée par le rapport" value={reco.current_value} />
        <Value label="Valeur proposée par le rapport" value={reco.suggested_value} />
        {reco.edited_value !== null && <Value label="Valeur modifiée par l’administration" value={reco.edited_value} />}
      </div>
      {!reco.applicable && <p className="notice">Application manuelle : {reco.not_applicable_reason}</p>}
      {reco.decision_note && <p className="muted" style={{ fontSize: 14 }}>Note : {reco.decision_note}</p>}
      {reco.decided_at && (
        <p className="muted" style={{ fontSize: 13 }}>
          Décision : {reco.decided_by_name ?? "—"}, le {fmt.format(new Date(reco.decided_at))}
          {reco.applied_at && <> · Appliquée par {reco.applied_by_name ?? "—"}, le {fmt.format(new Date(reco.applied_at))}</>}
        </p>
      )}
      {reco.last_error && (
        <p className="error" role="alert">
          Dernière erreur{reco.last_error_at ? ` (${fmt.format(new Date(reco.last_error_at))})` : ""} : {reco.last_error}
        </p>
      )}

      {canDecide && (
        <div className="seo-actions">
          {editing && (
            <label className="field">
              <span>Nouvelle valeur (modifiée avant validation)</span>
              <textarea value={edited} onChange={(e) => setEdited(e.target.value)} rows={reco.field === "json_ld" ? 8 : 3} />
            </label>
          )}
          <label className="field">
            <span>Note de décision (obligatoire pour un rejet)</span>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} placeholder="Pourquoi vous validez ou rejetez…" />
          </label>
          <div className="seo-buttons">
            {reco.status !== "validated" || editing ? (
              <button
                className="btn primary"
                disabled={pending}
                onClick={() => run(() => validateRecommendation(reco.id, note, editing ? edited : null), "Recommandation validée. Elle n’est pas encore appliquée.")}
              >
                {editing ? "Valider la valeur modifiée" : "Valider"}
              </button>
            ) : null}
            <button className="btn outline" disabled={pending} onClick={() => setEditing((v) => !v)}>
              {editing ? "Annuler la modification" : "Modifier avant validation"}
            </button>
            {reco.status !== "rejected" && (
              <button className="btn ghost" disabled={pending} onClick={() => run(() => rejectRecommendation(reco.id, note), "Recommandation rejetée.")}>
                Rejeter
              </button>
            )}
            {reco.status === "validated" && reco.applicable && !editing && (
              <button className="btn primary" disabled={pending} onClick={() => setConfirming(true)}>
                Appliquer…
              </button>
            )}
          </div>
        </div>
      )}

      {confirming && (
        <div className="seo-confirm" role="dialog" aria-label="Confirmer l’application">
          <h3>Confirmer l’application</h3>
          <dl>
            <dt>Page concernée</dt>
            <dd>{reco.page_path}</dd>
            <dt>Catégorie</dt>
            <dd>{fieldLabel} ({reco.category})</dd>
            <dt>Valeur actuelle sur le site</dt>
            <dd><code>{live ?? "— (balise absente)"}</code>{reco.live_value === null && live !== null && <span className="muted"> · valeur par défaut du code</span>}</dd>
            <dt>Nouvelle valeur</dt>
            <dd><code>{reco.proposed_value ?? "—"}</code></dd>
          </dl>
          <p className="muted" style={{ fontSize: 14 }}>
            Seule cette balise de cette page change. L’ancienne valeur est conservée dans l’historique et la modification pourra être annulée.
            Les pages publiques se mettent à jour en quelques minutes au plus.
          </p>
          <label style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
            <input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} />
            <span>Je confirme appliquer cette nouvelle valeur sur {reco.page_path}.</span>
          </label>
          <div className="seo-buttons">
            <button className="btn ghost" disabled={pending} onClick={() => { setConfirming(false); setChecked(false); }}>Annuler</button>
            <button
              className="btn primary"
              disabled={pending || !checked}
              onClick={() => run(() => applyRecommendation(reco.id, checked), "Modification appliquée et enregistrée dans l’historique.")}
            >
              Confirmer l’application
            </button>
          </div>
        </div>
      )}

      {reco.status === "applied" && reco.active_change_id && (
        <RevertButton changeId={reco.active_change_id} label="Annuler cette modification" />
      )}
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
    </article>
  );
}

export function RevertButton({ changeId, label = "Annuler" }: { changeId: string; label?: string }) {
  const [pending, start] = useTransition();
  const [error, setError] = useState<string>();
  return (
    <span>
      <button
        className="btn ghost"
        disabled={pending}
        onClick={() => {
          if (!window.confirm("Restaurer l’ancienne valeur de cette balise ? La modification restera visible dans l’historique.")) return;
          start(async () => {
            const res = await revertChange(changeId, true);
            setError(res.ok ? undefined : res.error);
          });
        }}
      >
        {label}
      </button>
      {error && <span className="error"> {error}</span>}
    </span>
  );
}
