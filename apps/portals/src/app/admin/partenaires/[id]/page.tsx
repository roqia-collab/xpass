import { CheckCircle2, CircleDashed, Lock } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Badge, Notice, PageHead } from "@/components/ui";
import { ACTOR_LABEL, type AccessRow, type MerchantDetail } from "@/lib/admin-types";
import { COMMERCIAL_LABEL, PSP_LABEL } from "@/lib/roles";
import { ApiError, apiFetch, getMe, mediaUrl } from "@/lib/session";

import { AccessPanel } from "../../access-panel";
import { MerchantDecision, ModerationButtons } from "../../forms";

export const metadata = { title: "Validation d’un partenaire" };

const timeFmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" });

/** Maquette 27 — validation commerciale (motivée, tracée) distincte de la vérification PSP. */
export default async function MerchantPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  let m: MerchantDetail;
  try {
    m = await apiFetch<MerchantDetail>(`/admin/merchants/${id}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
  const [me, access] = await Promise.all([getMe(), apiFetch<AccessRow[]>(`/admin/access?scope_type=merchant&scope_id=${id}`)]);
  const isAdmin = Boolean(me?.memberships.some((x) => x.role === "platform_admin"));
  const ok = m.checks.filter((c) => c.ok).length;
  const cover = mediaUrl(m.locations[0]?.cover_image_key ?? null);

  return (
    <>
      <p className="muted"><Link href="/admin/partenaires">Partenaires</Link> › {m.display_name} › Vérification</p>
      <PageHead
        title="Validation d’un partenaire"
        subtitle={`Dossier créé le ${new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" }).format(new Date(m.created_at))}`}
        action={<Badge tone={COMMERCIAL_LABEL[m.commercial_status].tone}>{COMMERCIAL_LABEL[m.commercial_status].label}</Badge>}
      />
      <div className="card" style={{ display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap" }}>
        {cover && <img src={cover} alt="" style={{ width: 240, height: 140, objectFit: "cover", borderRadius: 16 }} />}
        <div>
          <h2>{m.display_name}</h2>
          <p className="muted">{m.legal_name} · {m.city_label} · marché {m.market_code}{m.is_demo ? " · démo" : ""}</p>
          {(m.siret || m.contact_phone) && (
            <p className="muted" style={{ fontSize: 14 }}>
              {m.siret && <>SIRET {m.siret.replace(/(\d{3})(\d{3})(\d{3})(\d{5})/, "$1 $2 $3 $4")}</>}
              {m.siret && m.contact_phone && " · "}
              {m.contact_phone && <>Téléphone {m.contact_phone}</>}
            </p>
          )}
        </div>
      </div>
      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <h3>Vérification commerciale</h3>
            <Badge tone={ok === m.checks.length ? "mint" : "lavender"}>{ok} / {m.checks.length} vérifiés</Badge>
          </div>
          {m.checks.map((c) => (
            <div key={c.label} className="list-row" style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <div style={{ flex: 1 }}>
                <strong>{c.label}</strong>
                <div className="muted" style={{ fontSize: 13 }}>{c.detail}</div>
              </div>
              {c.ok ? <span style={{ color: "#2f7a45" }}><CheckCircle2 size={18} aria-hidden /> Vérifié</span> : <span className="muted"><CircleDashed size={18} aria-hidden /> À vérifier</span>}
            </div>
          ))}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <h3><Lock size={18} aria-hidden /> Vérification KYC / KYB (PSP)</h3>
              <Badge tone={m.psp_status === "verified" ? "mint" : m.psp_status === "rejected" ? "coral" : "lavender"}>{PSP_LABEL[m.psp_status]}</Badge>
            </div>
            <p className="muted">Vérification effectuée par le prestataire de paiement, transmise par webhook signé.</p>
            {m.psp_status !== "verified" && <p className="error">Versements indisponibles tant que la vérification PSP est incomplète.</p>}
            <p className="muted" style={{ fontSize: 13 }}>La validation commerciale ne préjuge pas de la vérification PSP.</p>
          </div>
          {m.locations.map((l) => (
            <div key={l.id} className="card" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <strong>{l.name}</strong>
              <span className="muted">{l.kind_label} · {l.address}</span>
              <span>{l.published_offers} prestation(s) publiée(s) · statut {l.status}{l.review_url ? " · lien d’avis renseigné" : ""}</span>
              <ModerationButtons id={l.id} status={l.status} />
            </div>
          ))}
        </div>
      </div>
      <Notice>Le téléversement et l’examen des justificatifs (Kbis, pièce d’identité) ne sont pas encore disponibles : la vérification d’identité relève du prestataire de paiement.</Notice>
      <AccessPanel scopeType="merchant" scopeId={m.id} rows={access} canEdit={isAdmin} />
      <MerchantDecision id={m.id} status={m.commercial_status} sandbox={m.sandbox} pspVerified={m.psp_status === "verified"} canDecide={isAdmin} />
      <div className="card" style={{ overflowX: "auto" }}>
        <h3>Historique d’audit</h3>
        <table className="table">
          <thead><tr><th>Date</th><th>Acteur</th><th>Action</th><th>Objet</th><th>Motif</th></tr></thead>
          <tbody>
            {m.audit.map((a, i) => (
              <tr key={i}>
                <td>{timeFmt.format(new Date(a.created_at))}</td>
                <td>{a.actor_name ?? ACTOR_LABEL[a.actor_kind]}</td>
                <td>{a.action}</td>
                <td>{a.object_label}</td>
                <td>{a.reason ?? "—"}</td>
              </tr>
            ))}
            {m.audit.length === 0 && <tr><td colSpan={5} className="muted">Aucune décision enregistrée.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
