import { ArrowRight, Calculator, MessageCircle, Users } from "lucide-react";
import Link from "next/link";

import { Badge, ErrorCard, PageHead } from "@/components/ui";
import { VenuePhotos } from "@/components/venue-photos";

import { DemoLocationsPanel } from "./demo-locations";
import { ACTOR_LABEL, DISPUTE_LABEL, type AdminOverview, type LaunchStatus } from "@/lib/admin-types";
import { COMMERCIAL_LABEL, NETWORK_LINE } from "@/lib/roles";
import { OpenCityForm } from "./launch-city";
import { mediaUrl, tryApi } from "@/lib/session";
import type { CommercialStatus } from "@/lib/types";

export const metadata = { title: "Pilotage des opérations" };

const dateFmt = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", year: "numeric" });
const timeFmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" });

/** Maquette 26 — files réelles : vérifications partenaires, litiges, rapprochement, journal d'audit. */
export default async function AdminOverviewPage() {
  const loaded = await tryApi<AdminOverview>("/admin/overview");
  if (!loaded.data) {
    return (
      <>
        <PageHead eyebrow="Admin" title="Pilotage des opérations" subtitle="La vue d’ensemble n’a pas pu être chargée." />
        <ErrorCard message={loaded.error ?? "Les données n’ont pas pu être chargées."} />
      </>
    );
  }
  const o = {
    ...loaded.data,
    merchants: loaded.data.merchants ?? [],
    disputes: loaded.data.disputes ?? [],
    audit: loaded.data.audit ?? [],
    payouts: loaded.data.payouts ?? {},
    demo_locations: loaded.data.demo_locations ?? {},
  };
  const launch = await tryApi<LaunchStatus>("/admin/launch").then((r) => r.data);
  const p = o.payouts;
  return (
    <>
      <PageHead
        eyebrow="Admin"
        title="Pilotage des opérations"
        subtitle="Suivez et traitez les tâches opérationnelles : vérifications, litiges, paiements."
        image={`${process.env.NEXT_PUBLIC_MEDIA_BASE_URL ?? "http://localhost:3080/xpass-public"}/demo/heroes/culture.jpg`}
        action={<Link href="/admin/partenaires" className="btn primary">Examiner les demandes <ArrowRight size={16} /></Link>}
      />
      <div className="card" style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <div>
          <h3>Le réseau</h3>
          <p className="muted">{NETWORK_LINE}</p>
        </div>
        <Link href="/admin/entreprises" className="btn outline">Services RH <ArrowRight size={16} /></Link>
      </div>
      {launch && (
        <section className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <h3>Réseau {launch.city}</h3>
          <p>{launch.venues} / {launch.venues_target} établissements publiés avec une prestation active. {launch.demo_hidden ? "Le catalogue de démonstration est masqué dans l’application." : "La démonstration reste visible tant que ce seuil n’est pas atteint."}</p>
          <p>{launch.paid_companies} entreprise(s) ont payé une facture (objectif : {launch.companies_target} ou 3). Les crédits n’apparaissent qu’après ce paiement.</p>
          <p>Stripe : {launch.stripe_mode === "live" ? "mode réel" : "mode test, aucun argent ne circule"}. Comptes de versement vérifiés : {launch.payout_accounts}. La commission est déduite du virement.</p>
          <p className="muted">{launch.lawyer_validated ? "Contrat validé par un juriste." : "Un juriste doit encore valider les CGU, la confidentialité et les conditions commerçants avant l’ouverture au public."}</p>
          <OpenCityForm allowed={launch.second_city_allowed} />
        </section>
      )}
      <div className="grid grid-3">
        <Tile href="/admin/partenaires" icon={<Users />} label="Commerçants à vérifier" value={o.merchants_to_review} detail="Dossiers en attente de validation" />
        <Tile href="/admin/litiges" icon={<MessageCircle />} label="Litiges ouverts" value={o.open_disputes} detail="À examiner et traiter" />
        <Tile href="/admin/paiements" icon={<Calculator />} label="Écarts de rapprochement" value={o.reconciliation_issues} detail="Paiements et virements à investiguer" />
      </div>
      <VenuePhotos title="Établissements du catalogue" text="Photos des lieux publiés à Paris." />
      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <Queue title="Commerçants à vérifier" href="/admin/partenaires" empty="Aucun dossier en attente.">
          {o.merchants.map((m) => (
            <Row key={m.id} href={`/admin/partenaires/${m.id}`} title={m.title} subtitle={m.subtitle} at={m.at} image={mediaUrl(m.image_key)}>
              <Badge tone={(COMMERCIAL_LABEL[m.status as CommercialStatus] ?? { tone: "grey" as const, label: m.status }).tone}>{(COMMERCIAL_LABEL[m.status as CommercialStatus] ?? { label: m.status }).label}</Badge>
            </Row>
          ))}
        </Queue>
        <Queue title="File des litiges" href="/admin/litiges" empty="Aucun litige ouvert.">
          {o.disputes.map((d) => (
            <Row key={d.id} href={`/admin/litiges/${d.id}`} title={d.title} subtitle={d.subtitle} at={d.at} image={mediaUrl(d.image_key)}>
              <Badge tone={(DISPUTE_LABEL[d.status] ?? { tone: "grey" as const, label: d.status }).tone}>{(DISPUTE_LABEL[d.status] ?? { label: d.status }).label}</Badge>
            </Row>
          ))}
        </Queue>
      </div>
      <DemoLocationsPanel counts={o.demo_locations ?? {}} canEdit={o.is_admin} />
      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <div className="card">
          <h3>Versements aux commerçants</h3>
          <div className="grid grid-3" style={{ marginTop: 12 }}>
            <Stat label="En attente / en cours" value={(p.pending ?? 0) + (p.in_transit ?? 0)} />
            <Stat label="Effectués" value={p.paid ?? 0} tone="mint" />
            <Stat label="Écart ou échec" value={(p.to_reconcile ?? 0) + (p.failed ?? 0)} tone="coral" />
          </div>
        </div>
        <div className="card" style={{ overflowX: "auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <h3>Journal des opérations</h3>
            <Link href="/admin/audit">Voir tout le journal <ArrowRight size={14} /></Link>
          </div>
          <table className="table">
            <thead><tr><th>Date</th><th>Acteur</th><th>Action</th><th>Objet</th><th>Motif</th></tr></thead>
            <tbody>
              {o.audit.map((a, i) => (
                <tr key={i}>
                  <td>{timeFmt.format(new Date(a.created_at))}</td>
                  <td>{a.actor_name ?? ACTOR_LABEL[a.actor_kind] ?? a.actor_kind}</td>
                  <td>{a.action}</td>
                  <td>{a.object_label}</td>
                  <td>{a.reason ?? "—"}</td>
                </tr>
              ))}
              {o.audit.length === 0 && <tr><td colSpan={5} className="muted">Aucune opération enregistrée.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function Tile({ href, icon, label, value, detail }: { href: string; icon: React.ReactNode; label: string; value: number; detail: string }) {
  return (
    <Link href={href} className="card kpi" style={{ display: "flex", gap: 14, alignItems: "center" }}>
      <div className="icon" aria-hidden>{icon}</div>
      <div style={{ flex: 1 }}>
        <p style={{ fontWeight: 600 }}>{label}</p>
        <p className="value" style={{ margin: "6px 0" }}>{value}</p>
        <p className="muted">{detail}</p>
      </div>
      <ArrowRight aria-hidden />
    </Link>
  );
}

function Queue({ title, href, empty, children }: { title: string; href: string; empty: string; children: React.ReactNode[] }) {
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <h3>{title}</h3>
      {children.length ? children : <p className="muted">{empty}</p>}
      <Link href={href}>Tout voir <ArrowRight size={14} /></Link>
    </div>
  );
}

function Row({ href, title, subtitle, at, image, children }: { href: string; title: string; subtitle: string; at: string; image?: string | null; children: React.ReactNode }) {
  return (
    <Link href={href} className="list-row" style={{ display: "flex", gap: 12, alignItems: "center" }}>
      {image ? <img className="thumb" src={image} alt="" style={{ width: 56, height: 44 }} /> : <span className="thumb" style={{ width: 56, height: 44 }} />}
      <div style={{ flex: 1, minWidth: 0 }}>
        <strong>{title}</strong>
        <div className="muted" style={{ fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{subtitle}</div>
      </div>
      <div style={{ textAlign: "right" }}>
        <div className="muted" style={{ fontSize: 12 }}>{dateFmt.format(new Date(at))}</div>
        {children}
      </div>
    </Link>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: "mint" | "coral" }) {
  return (
    <div>
      <p className="serif" style={{ fontSize: 30, color: tone === "coral" ? "var(--coral)" : tone === "mint" ? "#2f7a45" : undefined }}>{value}</p>
      <p className="muted" style={{ fontSize: 13 }}>{label}</p>
    </div>
  );
}
