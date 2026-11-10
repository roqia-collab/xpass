"use client";

import { KeyRound, UserMinus, UserPlus } from "lucide-react";
import { useOptimistic, useState, useTransition } from "react";

import { Badge } from "@/components/ui";

import { inviteTeamMember, removeTeamMember } from "./team-actions";

export interface TeamAccessRow {
  id: string;
  email: string;
  display_name: string;
  role: "merchant_owner" | "merchant_staff";
  linked: boolean;
  is_you: boolean;
  created_at: string;
}

const ROLE = { merchant_owner: "Responsable", merchant_staff: "Équipe" } as const;
const dateFmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" });

/**
 * Comptes de connexion de l'équipe. « Équipe » : planning, scanner et règlements en lecture ;
 * « Responsable » : tout, y compris le catalogue et l'équipe. La personne invitée reçoit un e-mail (sans lien).
 */
export function TeamAccess({ locationId, rows }: { locationId: string; rows: TeamAccessRow[] }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"merchant_staff" | "merchant_owner">("merchant_staff");
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();

  // Réponse immédiate : la ligne retirée disparaît, la ligne ajoutée apparaît « en cours », avant la réponse de l'API.
  type Change = { kind: "remove"; id: string } | { kind: "add"; row: TeamAccessRow };
  const [shown, change] = useOptimistic(rows, (state: TeamAccessRow[], c: Change) =>
    c.kind === "remove" ? state.filter((r) => r.id !== c.id) : [...state, c.row],
  );
  const run = (fn: () => Promise<{ ok: boolean; error?: string }>, success: string, optimistic?: Change) => {
    setMsg(undefined);
    start(async () => {
      if (optimistic) change(optimistic);
      const r = await fn();
      setMsg(r.ok ? { ok: true, text: success } : { ok: false, text: r.error ?? "Erreur inattendue." });
      if (r.ok) setEmail("");
    });
  };

  return (
    <section className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <h3><KeyRound size={18} aria-hidden /> Accès au portail</h3>
      <p className="muted" style={{ fontSize: 14 }}>
        Invitez vos collaborateurs avec leur adresse e-mail. <strong>Équipe</strong> : planning, scanner des clients et
        consultation. <strong>Responsable</strong> : tout, y compris prestations, horaires et équipe.
      </p>
      {shown.map((r) => (
        <div key={r.id} style={{ opacity: r.id.startsWith("en-cours-") ? 0.6 : 1 }}>
        <div key={r.id} className="list-row" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 180 }}>
            <strong>{r.email}</strong>{r.is_you && <span className="muted"> (vous)</span>}
            <div className="muted" style={{ fontSize: 13 }}>{ROLE[r.role]} · depuis le {dateFmt.format(new Date(r.created_at))}</div>
          </div>
          <Badge tone={r.linked ? "mint" : "lavender"}>{r.linked ? "Compte relié" : "En attente de connexion"}</Badge>
          {!r.is_you && (
            <button
              className="btn ghost"
              disabled={pending}
              aria-label={`Retirer l’accès de ${r.email}`}
              onClick={() => {
                if (!window.confirm(`Retirer l’accès de ${r.email} au portail ?`)) return;
                run(() => removeTeamMember(locationId, r.id), "Accès retiré.", { kind: "remove", id: r.id });
              }}
            >
              <UserMinus size={18} aria-hidden /> Retirer
            </button>
          )}
        </div>
        </div>
      ))}
      <form
        className="access-form"
        style={{ display: "grid", gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1fr) auto", gap: 10, alignItems: "end", marginTop: 6 }}
        onSubmit={(e) => {
          e.preventDefault();
          run(() => inviteTeamMember(locationId, email, role), "Invitation envoyée : la personne se connecte (ou crée son compte) avec cette adresse.",
            { kind: "add", row: { id: `en-cours-${Date.now()}`, email: email.trim().toLowerCase(), role, linked: false, is_you: false, created_at: new Date().toISOString() } as TeamAccessRow });
        }}
      >
        <label className="field">
          <span>Adresse e-mail du collaborateur</span>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="prenom@exemple.fr" autoComplete="off" />
        </label>
        <label className="field">
          <span>Rôle</span>
          <select value={role} onChange={(e) => setRole(e.target.value as typeof role)}>
            <option value="merchant_staff">Équipe</option>
            <option value="merchant_owner">Responsable</option>
          </select>
        </label>
        <button className="btn primary" type="submit" disabled={pending}><UserPlus size={18} aria-hidden /> Inviter</button>
      </form>
      {msg && <p role={msg.ok ? "status" : "alert"} className={msg.ok ? "notice mint" : "error"}>{msg.text}</p>}
    </section>
  );
}
