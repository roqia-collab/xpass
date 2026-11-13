"use client";

import { useState, useTransition } from "react";

import { Badge } from "@/components/ui";

import { removeAdministrator, renameAdministrator } from "./actions";

type AdminRow = { email: string; display_name: string; original: boolean };

export function AdminRows({ rows }: { rows: AdminRow[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {rows.map((row) => (
        <AdminLine key={row.email} row={row} />
      ))}
    </div>
  );
}

function AdminLine({ row }: { row: AdminRow }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(row.display_name);
  const [pending, start] = useTransition();
  const [error, setError] = useState("");

  return (
    <div className="card" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
      <div style={{ flex: 1, minWidth: 180 }}>
        {editing ? (
          <label className="field">
            <span>Nom</span>
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </label>
        ) : (
          <strong>{row.display_name}</strong>
        )}
        <div className="muted" style={{ fontSize: 13 }}>{row.original ? "Identifiant admin" : row.email}</div>
      </div>
      {row.original && <Badge tone="coral">Origine</Badge>}
      {editing ? (
        <>
          <button
            className="btn primary"
            disabled={pending}
            onClick={() => {
              setError("");
              start(async () => {
                const res = await renameAdministrator(row.email, name);
                if (!res.ok) setError(res.error);
                else setEditing(false);
              });
            }}
          >
            Enregistrer
          </button>
          <button className="btn ghost" type="button" onClick={() => { setEditing(false); setName(row.display_name); }}>Annuler</button>
        </>
      ) : (
        <button className="btn outline" type="button" onClick={() => setEditing(true)}>Modifier</button>
      )}
      {!row.original && (
        <button
          className="btn ghost"
          type="button"
          disabled={pending}
          onClick={() => {
            if (!window.confirm(`Retirer l’admin ${row.email} ? Il ne pourra plus ouvrir l’administration.`)) return;
            setError("");
            start(async () => {
              const res = await removeAdministrator(row.email);
              if (!res.ok) setError(res.error);
            });
          }}
        >
          Supprimer
        </button>
      )}
      {error && <p className="error" style={{ flexBasis: "100%" }}>{error}</p>}
    </div>
  );
}
