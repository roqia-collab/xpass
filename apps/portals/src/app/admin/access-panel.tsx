"use client";

import { KeyRound, UserMinus } from "lucide-react";
import { useOptimistic, useState, useTransition } from "react";

import { Badge } from "@/components/ui";
import type { AccessRow } from "@/lib/admin-types";

import { grantAccess, revokeAccess } from "./actions";

const ROLES = {
  merchant: [
    { value: "merchant_owner", label: "Responsable" },
    { value: "merchant_staff", label: "Équipe" },
  ],
  organization: [
    { value: "hr_admin", label: "Administrateur RH" },
    { value: "hr_viewer", label: "RH en lecture seule" },
  ],
} as const;

const ROLE_LABEL: Record<string, string> = {
  merchant_owner: "Responsable",
  merchant_staff: "Équipe",
  hr_admin: "Administrateur RH",
  hr_viewer: "RH en lecture seule",
};

const dateFmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" });

/**
 * Accès au portail d'un commerçant ou d'une entreprise : liste, attribution par e-mail, retrait.
 * La personne crée ou utilise son compte XPASS avec cette adresse ; aucun mot de passe ne passe par ici.
 */
export function AccessPanel({
  scopeType,
  scopeId,
  rows,
  canEdit,
}: {
  scopeType: "merchant" | "organization";
  scopeId: string;
  rows: AccessRow[];
  canEdit: boolean;
}) {
  const roles = ROLES[scopeType];
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<string>(roles[0].value);
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();

  // Réponse immédiate : la ligne retirée disparaît, la ligne ajoutée apparaît « en cours », avant la réponse de l'API.
  type Change = { kind: "remove"; id: string } | { kind: "add"; row: AccessRow };
  const [shown, change] = useOptimistic(rows, (state: AccessRow[], c: Change) =>
    c.kind === "remove" ? state.filter((r) => r.id !== c.id) : [...state, c.row],
  );
  const run = (fn: () => Promise<{ ok: boolean; error?: string }>, success: string, optimistic?: Change) => {
    setMsg(undefined);
    start(async () => {
      if (optimistic) change(optimistic);
      const res = await fn();
      setMsg(res.ok ? { ok: true, text: success } : { ok: false, text: res.error ?? "Erreur inattendue." });
      if (res.ok) setEmail("");
    });
  };

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <h3><KeyRound size={18} aria-hidden /> Accès au portail</h3>
      <p className="muted" style={{ fontSize: 14 }}>
        {scopeType === "merchant" ? "Personnes qui gèrent cet établissement dans l’espace commerçant." : "Personnes qui gèrent l’avantage salarié dans l’espace entreprise."}{" "}
        Elles se connectent avec leur compte XPASS (ou le créent) en utilisant l’adresse indiquée.
      </p>
      {rows.length === 0 && <p className="muted">Aucun accès pour le moment.</p>}
      {shown.map((r) => (
        <div key={r.id} style={{ opacity: r.id.startsWith("en-cours-") ? 0.6 : 1 }}>
        <div key={r.id} className="list-row" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 180 }}>
            <strong>{r.email}</strong>
            <div className="muted" style={{ fontSize: 13 }}>{ROLE_LABEL[r.role] ?? r.role} · depuis le {dateFmt.format(new Date(r.created_at))}</div>
          </div>
          <Badge tone={r.linked ? "mint" : "lavender"}>{r.linked ? "Compte relié" : "En attente de connexion"}</Badge>
          {canEdit && (
            <button
              className="btn ghost"
              disabled={pending}
              aria-label={`Retirer l’accès de ${r.email}`}
              onClick={() => {
                if (!window.confirm(`Retirer l’accès de ${r.email} ?`)) return;
                run(() => revokeAccess(r.id), "Accès retiré (tracé dans le journal d’audit).", { kind: "remove", id: r.id });
              }}
            >
              <UserMinus size={18} aria-hidden /> Retirer
            </button>
          )}
        </div>
        </div>
      ))}
      {canEdit ? (
        <form
          style={{ display: "grid", gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1fr) auto", gap: 10, alignItems: "end", marginTop: 6 }}
          className="access-form"
          onSubmit={(e) => {
            e.preventDefault();
            run(() => grantAccess(scopeType, scopeId, email, role), "Accès donné : un e-mail d’information a été mis en file d’envoi.",
                { kind: "add", row: { id: `en-cours-${Date.now()}`, email: email.trim().toLowerCase(), role, linked: false, created_at: new Date().toISOString() } as AccessRow });
          }}
        >
          <label className="field">
            <span>Adresse e-mail</span>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="prenom.nom@exemple.fr" autoComplete="off" />
          </label>
          <label className="field">
            <span>Rôle</span>
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              {roles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </label>
          <button className="btn primary" type="submit" disabled={pending}>Donner l’accès</button>
        </form>
      ) : (
        <p className="muted" style={{ fontSize: 13 }}>Seul un administrateur peut donner ou retirer un accès.</p>
      )}
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
    </div>
  );
}
