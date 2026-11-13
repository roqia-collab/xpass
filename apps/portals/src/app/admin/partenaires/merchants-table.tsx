"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState, useTransition } from "react";

import { merchantDecision } from "../actions";

import { Badge } from "@/components/ui";
import { COMMERCIAL_LABEL, PSP_LABEL } from "@/lib/roles";
import type { AdminMerchants, CommercialStatus } from "@/lib/types";

const FILTERS: (CommercialStatus | "all")[] = ["all", "pending_review", "documents_missing", "approved", "suspended"];

async function fetchMerchants(status: string): Promise<AdminMerchants> {
  const qs = status === "all" ? "" : `?status=${status}`;
  const res = await fetch(`/api/bff/admin/merchants${qs}`, { credentials: "same-origin" });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: { message?: string } } | null;
    throw new Error(body?.detail?.message ?? `Erreur ${res.status}`);
  }
  return res.json();
}

function RemoveMerchant({ id, name }: { id: string; name: string }) {
  const [pending, start] = useTransition();
  const [error, setError] = useState("");
  const client = useQueryClient();
  return (
    <span>
      <button
        className="btn ghost"
        disabled={pending}
        onClick={() => {
          const why = window.prompt(`Motif pour retirer ${name} (5 caractères minimum)`);
          if (!why) return;
          if (!window.confirm(`Suspendre ${name} ? Il disparaît de l’application.`)) return;
          setError("");
          start(async () => {
            const res = await merchantDecision(id, "suspend", why);
            if (!res.ok) setError(res.error);
            else await client.invalidateQueries({ queryKey: ["admin-merchants"] });
          });
        }}
      >
        Supprimer
      </button>
      {error && <span className="error"> {error}</span>}
    </span>
  );
}

export function MerchantsTable() {
  const [status, setStatus] = useState<(typeof FILTERS)[number]>("all");
  const query = useQuery({ queryKey: ["admin-merchants", status], queryFn: () => fetchMerchants(status) });

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <Link className="btn primary" href="/admin/demandes">Ajouter</Link>
      </div>
      <div className="chip-tabs" role="tablist" aria-label="Filtrer par statut commercial" style={{ flexWrap: "wrap" }}>
        {FILTERS.map((f) => (
          <button key={f} role="tab" aria-selected={f === status} className={f === status ? "on" : ""} onClick={() => setStatus(f)}>
            {f === "all" ? "Tous" : COMMERCIAL_LABEL[f].label}
            {query.data && f !== "all" ? ` (${query.data.by_commercial_status[f]})` : ""}
          </button>
        ))}
      </div>
      {query.isPending && <p className="muted">Chargement…</p>}
      {query.isError && (
        <p className="error" role="alert">
          {query.error.message}
        </p>
      )}
      {query.data && (
        <table className="table">
          <thead>
            <tr>
              <th>Commerçant</th>
              <th>Ville</th>
              <th>Activité</th>
              <th>Établissements</th>
              <th>Statut commercial</th>
              <th>Statut PSP</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {query.data.items.map((m) => (
              <tr key={m.id}>
                <td>
                  <Link href={`/admin/partenaires/${m.id}`}><strong>{m.display_name}</strong></Link>
                  <div className="muted" style={{ fontSize: 13 }}>{m.legal_name}</div>
                </td>
                <td>{m.city_label}</td>
                <td>{m.activities?.length ? m.activities.join(", ") : "—"}</td>
                <td>{m.location_count}</td>
                <td><Badge tone={COMMERCIAL_LABEL[m.commercial_status].tone}>{COMMERCIAL_LABEL[m.commercial_status].label}</Badge></td>
                <td><Badge tone={m.psp_status === "verified" ? "mint" : "grey"}>{PSP_LABEL[m.psp_status]}</Badge></td>
                <td style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <Link className="btn outline" href={`/admin/partenaires/${m.id}`}>Modifier</Link>
                  {m.commercial_status !== "suspended" && <RemoveMerchant id={m.id} name={m.display_name} />}
                </td>
              </tr>
            ))}
            {query.data.items.length === 0 && (
              <tr>
                <td colSpan={7} className="muted">Aucun commerçant avec ce statut.</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
