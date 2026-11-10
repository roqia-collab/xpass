"use client";

import { Pencil, Plus } from "lucide-react";
import { useState, useTransition } from "react";

import { Badge } from "@/components/ui";

import { savePlan, type PlanForm } from "./actions";

export interface AdminPlan {
  id: string;
  code: string;
  name: string;
  price_minor: number;
  currency: string;
  credits_per_period: number;
  credit_validity_days: number | null;
  psp_price_id: string | null;
  is_active: boolean;
  is_demo: boolean;
  subscribers: number;
}

const money = (minor: number, currency: string) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency }).format(minor / 100);

const EMPTY: PlanForm = {
  code: "", name: "", price_euros: "", credits_per_period: "", credit_validity_days: "", psp_price_id: "", is_active: true,
};

function toForm(p: AdminPlan): PlanForm {
  return {
    code: p.code,
    name: p.name,
    price_euros: String(p.price_minor / 100),
    credits_per_period: String(p.credits_per_period),
    credit_validity_days: p.credit_validity_days === null ? "" : String(p.credit_validity_days),
    psp_price_id: p.psp_price_id ?? "",
    is_active: p.is_active,
  };
}

/** Formulaire de formule : création, ou modification (prix figé dès qu'un client y est abonné). */
function PlanEditor({ plan, onDone }: { plan: AdminPlan | null; onDone: () => void }) {
  const [form, setForm] = useState<PlanForm>(plan ? toForm(plan) : EMPTY);
  const [error, setError] = useState<string>();
  const [pending, start] = useTransition();
  const locked = Boolean(plan && plan.subscribers > 0);
  const set = (k: keyof PlanForm) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: k === "is_active" ? e.target.checked : e.target.value }));
  return (
    <form
      className="card"
      style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}
      onSubmit={(e) => {
        e.preventDefault();
        setError(undefined);
        start(async () => {
          const r = await savePlan(plan?.id ?? null, form);
          if (r.ok) onDone();
          else setError(r.error);
        });
      }}
    >
      <label className="field">
        <span>Nom affiché</span>
        <input value={String(form.name)} onChange={set("name")} required maxLength={80} />
      </label>
      <label className="field">
        <span>Code (identifiant)</span>
        <input value={String(form.code)} onChange={set("code")} required disabled={Boolean(plan)} placeholder="intense" />
      </label>
      <label className="field">
        <span>Prix mensuel (€)</span>
        <input type="number" min={1} step="0.01" value={String(form.price_euros)} onChange={set("price_euros")} required disabled={locked} />
      </label>
      <label className="field">
        <span>Crédits par mois</span>
        <input type="number" min={1} value={String(form.credits_per_period)} onChange={set("credits_per_period")} required />
      </label>
      <label className="field">
        <span>Validité des crédits (jours, vide = sans limite)</span>
        <input type="number" min={7} max={366} value={String(form.credit_validity_days)} onChange={set("credit_validity_days")} />
      </label>
      <label className="field">
        <span>Tarif Stripe (price_…)</span>
        <input value={String(form.psp_price_id)} onChange={set("psp_price_id")} disabled={locked} placeholder="price_…" />
      </label>
      <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input type="checkbox" checked={Boolean(form.is_active)} onChange={set("is_active")} /> Proposée aux clients
      </label>
      <div style={{ display: "flex", gap: 8, alignItems: "end", flexWrap: "wrap" }}>
        <button className="btn primary" type="submit" disabled={pending}>{pending ? "Enregistrement…" : "Enregistrer"}</button>
        <button className="btn ghost" type="button" onClick={onDone}>Annuler</button>
      </div>
      {locked && (
        <p className="muted" style={{ gridColumn: "1 / -1", fontSize: 13 }}>
          {plan!.subscribers} abonné(s) : le prix et le tarif Stripe sont figés. Pour un autre prix, créez une nouvelle formule.
        </p>
      )}
      {error && <p className="error" role="alert" style={{ gridColumn: "1 / -1" }}>{error}</p>}
    </form>
  );
}

export function PlansManager({ plans, canEdit }: { plans: AdminPlan[]; canEdit: boolean }) {
  const [editing, setEditing] = useState<string | "new" | null>(null);
  return (
    <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="card" style={{ padding: 0, overflowX: "auto" }}>
        <table className="table">
          <thead>
            <tr><th>Formule</th><th>Prix</th><th>Crédits / mois</th><th>Prix du crédit</th><th>Abonnés</th><th>État</th>{canEdit && <th />}</tr>
          </thead>
          <tbody>
            {plans.map((p) => (
              <tr key={p.id}>
                <td><strong>{p.name}</strong> <span className="muted">· {p.code}</span> {p.is_demo && <Badge tone="grey">Démo</Badge>}</td>
                <td>{money(p.price_minor, p.currency)}</td>
                <td>{p.credits_per_period}</td>
                <td className="muted">{money(Math.round(p.price_minor / p.credits_per_period), p.currency)}</td>
                <td>{p.subscribers}</td>
                <td><Badge tone={p.is_active ? "mint" : "grey"}>{p.is_active ? "Proposée" : "Retirée"}</Badge></td>
                {canEdit && (
                  <td>
                    <button className="btn ghost" onClick={() => setEditing(p.id)} aria-label={`Modifier ${p.name}`}>
                      <Pencil size={16} aria-hidden /> Modifier
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {plans.length === 0 && (
              <tr><td colSpan={7} className="muted">Aucune formule : créez la première.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {canEdit && editing === null && (
        <button className="btn primary" style={{ alignSelf: "flex-start" }} onClick={() => setEditing("new")}>
          <Plus size={18} aria-hidden /> Nouvelle formule
        </button>
      )}
      {canEdit && editing !== null && (
        <PlanEditor
          key={editing}
          plan={editing === "new" ? null : (plans.find((p) => p.id === editing) ?? null)}
          onDone={() => setEditing(null)}
        />
      )}
    </section>
  );
}
