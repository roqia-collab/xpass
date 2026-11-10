"use client";

import { useState, useTransition } from "react";

import type { ActionResult } from "./actions";
import * as actions from "./actions";

/**
 * Bloc de décision : motif obligatoire, un bouton par décision possible.
 * Le résultat affiché est celui de l'API (aucun succès supposé).
 */
export function DecisionPanel({
  title,
  description,
  buttons,
  defaultReason = "",
  extra,
}: {
  title: string;
  description?: string;
  buttons: { label: string; tone?: "primary" | "outline"; confirm?: string; run: (reason: string, extra: string) => Promise<ActionResult> }[];
  defaultReason?: string;
  extra?: { label: string; placeholder?: string; type?: "number" | "text"; defaultValue?: string; help?: string };
}) {
  const [reason, setReason] = useState(defaultReason);
  const [extraValue, setExtraValue] = useState(extra?.defaultValue ?? "");
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <h3>{title}</h3>
      {description && <p className="muted" style={{ fontSize: 14 }}>{description}</p>}
      {extra && (
        <label className="field">
          <span>{extra.label}</span>
          <input type={extra.type ?? "text"} value={extraValue} placeholder={extra.placeholder} onChange={(e) => setExtraValue(e.target.value)} />
          {extra.help && <span className="muted" style={{ fontSize: 12 }}>{extra.help}</span>}
        </label>
      )}
      <label className="field">
        <span>Motif de la décision *</span>
        <textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Précisez votre décision et les éléments qui l’ont motivée…" />
      </label>
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "flex-end" }}>
        {buttons.map((b) => (
          <button
            key={b.label}
            className={`btn ${b.tone ?? "outline"}`}
            disabled={pending}
            onClick={() => {
              if (b.confirm && !window.confirm(b.confirm)) return;
              setMsg(undefined);
              start(async () => {
                const res = await b.run(reason, extraValue);
                setMsg(res.ok ? { ok: true, text: "Décision enregistrée dans le journal d’audit." } : { ok: false, text: res.error });
                if (res.ok) setReason("");
              });
            }}
          >
            {b.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function MerchantDecision({ id, status, sandbox, pspVerified, canDecide }: { id: string; status: string; sandbox: boolean; pspVerified: boolean; canDecide: boolean }) {
  if (!canDecide) return <p className="muted">Décision réservée aux administrateurs XPASS.</p>;
  const buttons = [
    ...(status !== "documents_missing" ? [{ label: "Demander des compléments", run: (r: string) => actions.merchantDecision(id, "request_documents", r) }] : []),
    ...(status === "approved"
      ? [{ label: "Suspendre", confirm: "Suspendre ce partenaire ? Ses établissements ne seront plus visibles.", run: (r: string) => actions.merchantDecision(id, "suspend", r) }]
      : [{ label: "Valider le dossier commercial", tone: "primary" as const, run: (r: string) => actions.merchantDecision(id, "approve", r) }]),
    ...(sandbox && !pspVerified ? [{ label: "Simuler la vérification PSP (bac à sable)", run: (r: string) => actions.pspSandboxVerify(id, r) }] : []),
  ];
  return <DecisionPanel title="Décision et audit" description="La décision et son motif sont enregistrés dans l’historique du partenaire." buttons={buttons} />;
}

export function ModerationButtons({ id, status }: { id: string; status: string }) {
  return (
    <DecisionPanel
      title="Modération"
      buttons={
        status === "published"
          ? [{ label: "Masquer du catalogue", confirm: "Masquer cet établissement pour les clients ?", run: (r) => actions.moderateLocation(id, false, r) }]
          : [{ label: "Publier", tone: "primary", run: (r) => actions.moderateLocation(id, true, r) }]
      }
    />
  );
}

export function DisputeActions({ id, netMinor, open }: { id: string; netMinor: number | null; open: boolean }) {
  if (!open) return null;
  return (
    <DecisionPanel
      title="Décision"
      description="La restitution recrée au client les crédits consommés, source par source. Un éventuel ajustement est déduit d’un prochain versement du partenaire (un versement déjà payé n’est pas modifié)."
      extra={{
        label: "Ajustement partenaire (centimes, 0 = aucun)",
        type: "number",
        defaultValue: "0",
        help: netMinor !== null ? `Maximum : ${netMinor} centimes (montant revenant au partenaire).` : "Aucune dette partenaire valorisée.",
      }}
      buttons={[
        { label: "Mettre en analyse", run: (r) => actions.updateDispute(id, "in_review", "", r) },
        { label: "Demander des justificatifs", run: (r) => actions.updateDispute(id, "waiting_customer", "", r) },
        { label: "Rejeter", confirm: "Rejeter la réclamation ?", run: (r) => actions.rejectDispute(id, r) },
        { label: "Valider la restitution", tone: "primary", confirm: "Restituer les crédits au client ?", run: (r, x) => actions.refundDispute(id, Number(x || 0), r) },
      ]}
    />
  );
}

export function InlineAction({ label, run, confirm }: { label: string; run: (reason: string) => Promise<ActionResult>; confirm?: string }) {
  const [pending, start] = useTransition();
  const [error, setError] = useState<string>();
  return (
    <span>
      <button
        className="btn ghost"
        disabled={pending}
        onClick={() => {
          const reason = window.prompt(`${label} — motif (obligatoire) :`);
          if (!reason) return;
          if (confirm && !window.confirm(confirm)) return;
          start(async () => {
            const res = await run(reason);
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

export function PayoutActions({ id, status }: { id: string; status: string }) {
  return status === "failed" ? (
    <InlineAction label="Relancer le versement" run={(r) => actions.payoutAction(id, "retry", r)} />
  ) : (
    <InlineAction
      label="Clore l’écart"
      confirm="Accepter le montant confirmé par le prestataire et clore l’écart ?"
      run={(r) => actions.payoutAction(id, "close", r)}
    />
  );
}

export function EventActions({ id }: { id: string }) {
  return (
    <>
      <InlineAction label="Retraiter" run={(r) => actions.eventAction(id, "retry", r)} />
      <InlineAction label="Classer" confirm="Classer cet événement sans l’appliquer ?" run={(r) => actions.eventAction(id, "dismiss", r)} />
    </>
  );
}

export function ConfirmInvoice({ id, label }: { id: string; label: string }) {
  const [pending, start] = useTransition();
  const [error, setError] = useState<string>();
  return (
    <span>
      <button
        className="btn outline"
        disabled={pending}
        onClick={() => {
          if (!window.confirm(`Confirmer la réception du virement pour ${label} ? Les crédits des salariés seront alloués.`)) return;
          start(async () => {
            const res = await actions.confirmEmployerInvoice(id);
            setError(res.ok ? undefined : res.error);
          });
        }}
      >
        Virement reçu
      </button>
      {error && <span className="error"> {error}</span>}
    </span>
  );
}

export function SupportReply({ id }: { id: string }) {
  const [reply, setReply] = useState("");
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const send = (close: boolean) =>
    start(async () => {
      const res = await actions.replySupport(id, reply, close);
      setMsg(res.ok ? { ok: true, text: "Réponse envoyée au client." } : { ok: false, text: res.error });
      if (res.ok) setReply("");
    });
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <label className="field">
        <span>Réponse au client</span>
        <textarea value={reply} onChange={(e) => setReply(e.target.value)} />
      </label>
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button className="btn outline" disabled={pending} onClick={() => send(false)}>Répondre</button>
        <button className="btn primary" disabled={pending} onClick={() => send(true)}>Répondre et clore</button>
      </div>
    </div>
  );
}
