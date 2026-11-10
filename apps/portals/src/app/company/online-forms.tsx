"use client";

import { CreditCard, KeyRound } from "lucide-react";
import { useState, useTransition } from "react";

import { Badge } from "@/components/ui";

import { createApiKey, payInvoice, revokeApiKey } from "./online-actions";

/** Bouton « Payer en ligne » d'une facture en attente : redirection vers la page sécurisée du prestataire. */
export function PayInvoiceButton({ invoiceId }: { invoiceId: string }) {
  const [pending, start] = useTransition();
  const [error, setError] = useState<string>();
  return (
    <span style={{ display: "inline-flex", flexDirection: "column", gap: 4 }}>
      <button
        className="btn outline"
        style={{ padding: "6px 12px", fontSize: 14 }}
        disabled={pending}
        onClick={() => start(async () => {
          const r = await payInvoice(invoiceId);
          if (r.ok) window.location.assign(r.url);
          else setError(r.error);
        })}
      >
        <CreditCard size={16} aria-hidden /> {pending ? "Ouverture…" : "Payer en ligne"}
      </button>
      {error && <span className="error" role="alert" style={{ fontSize: 13 }}>{error}</span>}
    </span>
  );
}

export interface ApiKeyRow { id: string; label: string; prefix: string; created_at: string; last_used_at: string | null; revoked_at: string | null }

const when = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });

/** Clés d'API du logiciel RH : la clé complète n'est affichée qu'une fois, à la création. */
export function ApiKeys({ rows, apiBase }: { rows: ApiKeyRow[]; apiBase: string }) {
  const [label, setLabel] = useState("Logiciel RH");
  const [created, setCreated] = useState<string>();
  const [pending, start] = useTransition();
  const [error, setError] = useState<string>();
  // Réponse immédiate : la clé s'affiche « Révoquée » au clic, et redevient active si l'API refuse.
  const [revoking, setRevoking] = useState<string[]>([]);
  return (
    <section className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <h3><KeyRound size={18} aria-hidden /> Import automatique depuis votre logiciel RH</h3>
      <p className="muted" style={{ fontSize: 14 }}>
        Votre logiciel RH (ou votre prestataire de paie) envoie la liste des salariés éligibles : les nouveaux sont invités, les noms
        mis à jour et, si vous le demandez, les absents retirés. Aucune donnée de visite ne remonte par cette voie.
      </p>
      {rows.map((k) => (
        <div key={k.id} className="list-row" style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <strong>{k.label}</strong> <code className="muted">{k.prefix}…</code>
            <div className="muted" style={{ fontSize: 13 }}>
              Créée le {when.format(new Date(k.created_at))} · {k.last_used_at ? `dernier envoi le ${when.format(new Date(k.last_used_at))}` : "jamais utilisée"}
            </div>
          </div>
          {k.revoked_at || revoking.includes(k.id) ? <Badge tone="grey">Révoquée</Badge> : (
            <button className="btn ghost" disabled={pending} onClick={() => {
              if (!window.confirm("Révoquer cette clé ? Le logiciel RH ne pourra plus envoyer de liste.")) return;
              setRevoking((ids) => [...ids, k.id]);
              start(async () => {
                const r = await revokeApiKey(k.id);
                if (!r.ok) {
                  setRevoking((ids) => ids.filter((x) => x !== k.id));
                  setError(r.error);
                }
              });
            }}>Révoquer</button>
          )}
        </div>
      ))}
      {created ? (
        <div className="notice mint" role="status" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <strong>Clé créée : copiez-la maintenant, elle ne sera plus affichée.</strong>
          <code style={{ wordBreak: "break-all", userSelect: "all" }}>{created}</code>
        </div>
      ) : (
        <form style={{ display: "flex", gap: 10, alignItems: "end", flexWrap: "wrap" }} onSubmit={(e) => {
          e.preventDefault();
          setError(undefined);
          start(async () => { const r = await createApiKey(label); if (r.ok) setCreated(r.key); else setError(r.error); });
        }}>
          <label className="field" style={{ flex: 1, minWidth: 200 }}>
            <span>Nom de la clé</span>
            <input value={label} onChange={(e) => setLabel(e.target.value)} maxLength={80} />
          </label>
          <button className="btn primary" type="submit" disabled={pending}>Créer une clé</button>
        </form>
      )}
      <details>
        <summary className="muted" style={{ cursor: "pointer" }}>Format de l’envoi (pour votre prestataire)</summary>
        <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, background: "var(--cream-dark)", padding: 12, borderRadius: 12 }}>{`PUT ${apiBase}/api/v1/hr-sync/employees   (ajouter ?dry_run=true pour simuler)
Authorization: Bearer <clé>
Content-Type: application/json

{ "employees": [ { "email": "prenom.nom@entreprise.fr", "first_name": "Prénom", "last_name": "Nom" } ],
  "remove_missing": false }`}</pre>
      </details>
      {error && <p className="error" role="alert">{error}</p>}
    </section>
  );
}
