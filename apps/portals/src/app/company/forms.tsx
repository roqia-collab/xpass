"use client";

import { FileUp, MoreHorizontal, UserPlus } from "lucide-react";
import { useState, useTransition } from "react";

import { Badge } from "@/components/ui";
import { money } from "@/lib/money";
import type { CompanyEmployee, CompanyOverview, CsvPreview } from "@/lib/types";

import * as actions from "./actions";

type Feedback = { tone: "ok" | "error"; text: string } | undefined;

function Message({ value }: { value: Feedback }) {
  if (!value) return null;
  return (
    <p role={value.tone === "error" ? "alert" : "status"} className={value.tone === "error" ? "error" : "notice mint"}>
      {value.text}
    </p>
  );
}

const nextMonths = (from: string, count: number) =>
  Array.from({ length: count }, (_, i) => {
    const d = new Date(`${from}T12:00:00Z`);
    d.setUTCMonth(d.getUTCMonth() + i, 1);
    return d.toISOString().slice(0, 10);
  });

const monthLabel = (iso: string) =>
  new Intl.DateTimeFormat("fr-FR", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${iso}T12:00:00Z`));

// ---------------------------------------------------------------- politique de budget

export function PolicyEditor({ overview }: { overview: CompanyOverview }) {
  const base = overview.next_policy ?? overview.policy;
  const [open, setOpen] = useState(false);
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<Feedback>();
  const months = nextMonths(overview.report.period, 4);
  const [form, setForm] = useState({
    credits_per_month: String(base?.credits_per_month ?? 100),
    all: base?.eligible_categories == null,
    categories: base?.eligible_categories ?? overview.categories.map((c) => c.slug),
    credit_validity_days: String(base?.credit_validity_days ?? 60),
    effective_from: months[1],
  });
  if (!overview.can_edit) return null;
  if (!open) return <button className="btn outline" onClick={() => setOpen(true)}>Modifier</button>;
  const price = overview.contract?.credit_price_minor ?? 0;
  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 12 }}
      onSubmit={(e) => {
        e.preventDefault();
        setMsg(undefined);
        start(async () => {
          const res = await actions.savePolicy({
            credits_per_month: form.credits_per_month,
            eligible_categories: form.all ? null : form.categories,
            credit_validity_days: form.credit_validity_days,
            effective_from: form.effective_from,
          });
          setMsg(res.ok ? { tone: "ok", text: `Politique enregistrée à partir de ${monthLabel(form.effective_from)}.` } : { tone: "error", text: res.error });
        });
      }}
    >
      <div className="form-grid">
        <label className="field">
          <span>Crédits par salarié et par mois</span>
          <input type="number" min={1} value={form.credits_per_month} onChange={(e) => setForm({ ...form, credits_per_month: e.target.value })} />
        </label>
        <label className="field">
          <span>Validité des crédits (jours)</span>
          <input type="number" min={7} max={366} value={form.credit_validity_days} onChange={(e) => setForm({ ...form, credit_validity_days: e.target.value })} />
        </label>
        <label className="field">
          <span>À partir de</span>
          <select value={form.effective_from} onChange={(e) => setForm({ ...form, effective_from: e.target.value })}>
            {months.map((m) => (
              <option key={m} value={m}>{monthLabel(m)}</option>
            ))}
          </select>
        </label>
      </div>
      {price > 0 && (
        <p className="muted" style={{ fontSize: 13 }}>
          Coût par salarié : {money(Number(form.credits_per_month || 0) * price, overview.contract!.currency)} / mois.
        </p>
      )}
      <label className="check-row">
        <input type="checkbox" checked={form.all} onChange={(e) => setForm({ ...form, all: e.target.checked })} />
        <span>Tous les univers</span>
      </label>
      {!form.all && (
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
          {overview.categories.map((c) => (
            <label key={c.slug} className="check-row">
              <input
                type="checkbox"
                checked={form.categories.includes(c.slug)}
                onChange={(e) => setForm({ ...form, categories: e.target.checked ? [...form.categories, c.slug] : form.categories.filter((x) => x !== c.slug) })}
              />
              <span>{c.name}</span>
            </label>
          ))}
        </div>
      )}
      <p className="muted" style={{ fontSize: 13 }}>
        Le mois en cours ne peut plus changer une fois les crédits attribués : la nouvelle politique s’applique au mois choisi.
      </p>
      <Message value={msg} />
      <div style={{ display: "flex", gap: 10 }}>
        <button type="button" className="btn ghost" onClick={() => setOpen(false)}>Fermer</button>
        <button className="btn primary" disabled={pending}>{pending ? "Enregistrement…" : "Enregistrer"}</button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------- invitations

export function InviteForm() {
  const [pending, start] = useTransition();
  const [msg, setMsg] = useState<Feedback>();
  const [form, setForm] = useState({ email: "", first_name: "", last_name: "" });
  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
      onSubmit={(e) => {
        e.preventDefault();
        setMsg(undefined);
        start(async () => {
          const res = await actions.inviteEmployee(form);
          if (res.ok) {
            setMsg({ tone: "ok", text: `${form.email} est invité(e). Il ou elle rejoint l’équipe en acceptant dans l’application XPASS.` });
            setForm({ email: "", first_name: "", last_name: "" });
          } else setMsg({ tone: "error", text: res.error });
        });
      }}
    >
      <h3><UserPlus size={18} aria-hidden /> Inviter un salarié individuellement</h3>
      <div className="form-grid">
        <label className="field">
          <span>E-mail professionnel</span>
          <input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </label>
        <label className="field">
          <span>Prénom</span>
          <input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
        </label>
        <label className="field">
          <span>Nom</span>
          <input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
        </label>
      </div>
      <Message value={msg} />
      <button className="btn primary" disabled={pending} style={{ alignSelf: "flex-start" }}>{pending ? "Invitation…" : "Inviter"}</button>
    </form>
  );
}

const PROBLEM: Record<string, { label: string; tone: "coral" | "lavender" }> = {
  duplicate: { label: "Doublon", tone: "lavender" },
  invalid_email: { label: "E-mail invalide", tone: "coral" },
};

export function CsvImport() {
  const [pending, start] = useTransition();
  const [file, setFile] = useState<{ name: string; content: string }>();
  const [preview, setPreview] = useState<CsvPreview>();
  const [map, setMap] = useState<Record<string, string> | null>(null);
  const [msg, setMsg] = useState<Feedback>();

  const runPreview = (content: string, mapping: Record<string, string> | null) =>
    start(async () => {
      setMsg(undefined);
      const res = await actions.previewCsv(content, mapping);
      if (res.ok) {
        setPreview(res.data);
        setMap(res.data.mapping);
      } else {
        setPreview(undefined);
        setMsg({ tone: "error", text: res.error });
      }
    });

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <h3><FileUp size={18} aria-hidden /> Importer un CSV</h3>
      <p className="muted" style={{ fontSize: 13 }}>Colonnes attendues : e-mail, nom, prénom (séparateur virgule ou point-virgule). Un aperçu s’affiche avant toute invitation.</p>
      <input
        type="file"
        accept=".csv,text/csv"
        aria-label="Fichier CSV des salariés"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (!f) return;
          if (f.size > 200_000) {
            setMsg({ tone: "error", text: "Fichier trop volumineux (200 Ko maximum)." });
            return;
          }
          f.text().then((content) => {
            setFile({ name: f.name, content });
            runPreview(content, null);
          });
        }}
      />
      {preview && file && (
        <>
          <div className="grid grid-3">
            <div className="notice mint"><strong>{preview.valid_count}</strong>&nbsp;ligne(s) valide(s), prêtes à être invitées</div>
            <div className="notice"><strong>{preview.duplicate_count}</strong>&nbsp;doublon(s) ignoré(s)</div>
            <div className="notice" style={{ background: "#ffe7e2" }}><strong>{preview.invalid_count}</strong>&nbsp;e-mail(s) invalide(s) ignoré(s)</div>
          </div>
          <div className="form-grid">
            {(["email", "last_name", "first_name"] as const).map((k) => (
              <label key={k} className="field">
                <span>Colonne {k === "email" ? "e-mail" : k === "last_name" ? "nom" : "prénom"}</span>
                <select
                  value={map?.[k] ?? ""}
                  onChange={(e) => {
                    const next = { ...(map ?? {}), [k]: e.target.value };
                    if (!e.target.value) delete next[k];
                    runPreview(file.content, next);
                  }}
                >
                  <option value="">—</option>
                  {preview.headers.map((h) => (
                    <option key={h} value={h}>{h}</option>
                  ))}
                </select>
              </label>
            ))}
          </div>
          {preview.errors.length > 0 && (
            <table className="table">
              <thead>
                <tr><th>Ligne</th><th>E-mail</th><th>Nom</th><th>Prénom</th><th>Problème</th></tr>
              </thead>
              <tbody>
                {preview.errors.map((r) => (
                  <tr key={r.line}>
                    <td>{r.line}</td>
                    <td>{r.email}</td>
                    <td>{r.last_name}</td>
                    <td>{r.first_name}</td>
                    <td><Badge tone={PROBLEM[r.problem]?.tone ?? "grey"}>{PROBLEM[r.problem]?.label ?? r.problem}</Badge> <span className="muted">{r.detail}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button className="btn ghost" onClick={() => { setPreview(undefined); setFile(undefined); }}>Annuler</button>
            <button
              className="btn primary"
              disabled={pending || preview.valid_count === 0}
              onClick={() =>
                start(async () => {
                  const res = await actions.importCsv(file.content, map);
                  if (res.ok) {
                    setMsg({ tone: "ok", text: `${res.data.created} salarié(s) invité(s).` });
                    setPreview(undefined);
                    setFile(undefined);
                  } else setMsg({ tone: "error", text: res.error });
                })
              }
            >
              Confirmer l’import des {preview.valid_count} ligne(s) valide(s)
            </button>
          </div>
        </>
      )}
      <Message value={msg} />
    </div>
  );
}

// ---------------------------------------------------------------- actions sur un salarié

export function EmployeeMenu({ employee }: { employee: CompanyEmployee }) {
  const [pending, start] = useTransition();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string>();
  const act = (action: "suspend" | "reactivate" | "remove", confirmText?: string) => {
    if (confirmText && !window.confirm(confirmText)) return;
    start(async () => {
      const res = await actions.employeeAction(employee.id, action);
      setError(res.ok ? undefined : res.error);
      setOpen(false);
    });
  };
  if (employee.status === "removed") return null;
  return (
    <div style={{ position: "relative" }}>
      <button className="btn ghost" aria-label={`Actions pour ${employee.email}`} aria-expanded={open} onClick={() => setOpen(!open)} disabled={pending}>
        <MoreHorizontal size={18} />
      </button>
      {open && (
        <div className="card" role="menu" style={{ position: "absolute", right: 0, zIndex: 5, minWidth: 260, display: "flex", flexDirection: "column", gap: 4, padding: 10 }}>
          {employee.status === "suspended" ? (
            <button role="menuitem" className="btn ghost" onClick={() => act("reactivate")}>Réactiver les allocations</button>
          ) : (
            <button role="menuitem" className="btn ghost" style={{ color: "#b42318" }} onClick={() => act("suspend", "Arrêter les allocations futures ? Les crédits déjà attribués restent acquis.")}>
              Arrêter les allocations futures
            </button>
          )}
          <button role="menuitem" className="btn ghost" onClick={() => act("remove", "Retirer ce salarié de l’équipe ? Ses crédits déjà attribués restent acquis.")}>
            Retirer de l’équipe
          </button>
          <span className="muted" style={{ fontSize: 12, padding: "0 12px" }}>Les droits déjà acquis sont préservés.</span>
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}

// ---------------------------------------------------------------- financement

export function FundingForm({ creditPriceMinor, currency }: { creditPriceMinor: number; currency: string }) {
  const [pending, start] = useTransition();
  const [credits, setCredits] = useState("1000");
  const [msg, setMsg] = useState<Feedback>();
  const amount = Number(credits || 0) * creditPriceMinor;
  return (
    <form
      className="card"
      style={{ display: "flex", flexDirection: "column", gap: 10 }}
      onSubmit={(e) => {
        e.preventDefault();
        start(async () => {
          const res = await actions.requestFunding(amount);
          setMsg(res.ok ? { tone: "ok", text: "Facture émise. Le financement sera disponible dès réception du virement." } : { tone: "error", text: res.error });
        });
      }}
    >
      <h3>Demander un financement</h3>
      <label className="field">
        <span>Nombre de crédits à financer</span>
        <input type="number" min={1} step={1} value={credits} onChange={(e) => setCredits(e.target.value)} />
      </label>
      <p className="muted">Montant de la facture : <strong>{money(amount, currency)}</strong></p>
      <Message value={msg} />
      <button className="btn primary" disabled={pending || amount < 100} style={{ alignSelf: "flex-start" }}>
        {pending ? "Émission…" : "Émettre la facture"}
      </button>
    </form>
  );
}
