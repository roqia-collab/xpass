"use client";

import { ExternalLink, Landmark, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import { Badge } from "@/components/ui";

import { openPayoutDashboard, refreshPayoutStatus, startPayoutOnboarding } from "./payout-actions";

const STATUS: Record<string, { label: string; tone: "mint" | "lavender" | "coral" | "grey" }> = {
  not_started: { label: "À ouvrir", tone: "grey" },
  pending: { label: "Vérification en cours", tone: "lavender" },
  verified: { label: "Versements activés", tone: "mint" },
  rejected: { label: "Refusé par le prestataire", tone: "coral" },
};

/**
 * Compte de versement (Stripe Connect Express). Le commerçant saisit identité, entreprise et IBAN sur la page
 * sécurisée du prestataire ; XPASS ne conserve que le statut. Au retour, le statut est relu chez le prestataire.
 */
export function PayoutAccount({
  status,
  hasAccount,
  configured,
  isDemo,
  returning,
}: {
  status: string;
  hasAccount: boolean;
  configured: boolean;
  isDemo: boolean;
  returning?: "retour" | "relancer";
}) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const [error, setError] = useState<string>();
  const [info, setInfo] = useState<string>();

  useEffect(() => {
    if (returning !== "retour") return;
    start(async () => {
      const r = await refreshPayoutStatus();
      if (!r.ok) setError(r.error);
      else setInfo(r.status === "verified" ? "Votre compte de versement est vérifié." : "Informations transmises : le prestataire termine la vérification. Le statut se met à jour automatiquement.");
      router.replace("/partner/reglements");
    });
  }, [returning, router]);

  const go = (fn: () => Promise<{ ok: true; url: string } | { ok: false; error: string }>) => {
    setError(undefined);
    start(async () => {
      const r = await fn();
      if (r.ok) window.location.assign(r.url);
      else setError(r.error);
    });
  };

  const s = STATUS[status] ?? STATUS.not_started!;
  let text: string;
  if (!configured) text = "Les versements ne sont pas encore configurés sur la plateforme : l’équipe XPASS vous préviendra.";
  else if (status === "verified") text = "Vos versements sont actifs. Vos coordonnées bancaires sont gérées par le prestataire de paiement, jamais stockées par XPASS.";
  else if (status === "rejected") text = "Le prestataire de paiement a refusé ce compte. Contactez l’assistance XPASS.";
  else if (hasAccount) text = "Terminez la vérification chez le prestataire de paiement (identité, entreprise, IBAN). Les versements démarreront ensuite.";
  else text = "Pour recevoir vos règlements, ouvrez votre compte de versement : identité, entreprise et IBAN sont saisis sur la page sécurisée du prestataire de paiement (Stripe).";

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <Landmark aria-hidden />
        <div style={{ flex: 1, minWidth: 240 }}>
          <h3>Compte de versement</h3>
          <p className="muted">{text}</p>
          {isDemo && <p className="muted" style={{ fontSize: 13 }}>Établissement de démonstration : bac à sable uniquement, aucun virement réel.</p>}
        </div>
        <Badge tone={s.tone}>{s.label}</Badge>
      </div>
      {configured && status !== "rejected" && (
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {status !== "verified" && (
            <button className="btn primary" disabled={pending} onClick={() => go(startPayoutOnboarding)}>
              {pending ? "Ouverture…" : hasAccount ? "Continuer la vérification" : "Ouvrir mon compte de versement"} <ExternalLink size={16} aria-hidden />
            </button>
          )}
          {status === "verified" && (
            <button className="btn outline" disabled={pending} onClick={() => go(openPayoutDashboard)}>
              Accéder à mon espace prestataire <ExternalLink size={16} aria-hidden />
            </button>
          )}
          {hasAccount && status !== "verified" && (
            <button
              className="btn ghost"
              disabled={pending}
              onClick={() =>
                start(async () => {
                  const r = await refreshPayoutStatus();
                  if (r.ok) router.refresh();
                  else setError(r.error);
                })
              }
            >
              <RefreshCw size={16} aria-hidden /> Actualiser le statut
            </button>
          )}
        </div>
      )}
      {returning === "relancer" && !info && <p className="notice">Le lien a expiré : cliquez sur « Continuer la vérification » pour en obtenir un nouveau.</p>}
      {info && <p className="notice mint" role="status">{info}</p>}
      {error && <p className="error" role="alert">{error}</p>}
    </div>
  );
}
