import { PageHead } from "@/components/ui";
import { apiFetch, getMe } from "@/lib/session";

import { PlansManager, type AdminPlan } from "./plans";

export const metadata = { title: "Formules" };

/** Formules d'abonnement et règles d'utilisation des crédits (prix variable, report, pénalités). */
export default async function PlansPage() {
  const [plans, me] = await Promise.all([apiFetch<AdminPlan[]>("/admin/plans"), getMe()]);
  const canEdit = Boolean(me?.memberships.some((x) => x.role === "platform_admin"));
  return (
    <>
      <PageHead
        eyebrow="Administration"
        title="Formules d’abonnement"
        subtitle="Les salariés et les abonnés dépensent leurs crédits chez les commerçants."
      />
      <PlansManager plans={plans} canEdit={canEdit} />
      <section className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <h3>Règles appliquées aux crédits</h3>
        <ul style={{ margin: 0, paddingInlineStart: 20, display: "flex", flexDirection: "column", gap: 6 }}>
          <li><strong>Prix variable :</strong> le partenaire fixe un prix de base ; +20 % aux heures de pointe (18 h – 21 h en semaine, et le week-end), +20 % quand le créneau est occupé à 70 % ou plus, −20 % en dernière minute (moins de 6 h avant, créneau occupé à moins de 30 %). Le prix est figé à la réservation.</li>
          <li><strong>Report :</strong> à chaque renouvellement, les crédits d’abonnement non utilisés sont reportés jusqu’à un mois de formule ; au-delà, les plus anciens expirent. À l’arrêt de l’abonnement, ils expirent. Les crédits employeur ne sont pas concernés.</li>
          <li><strong>Changement de formule :</strong> appliqué au prochain renouvellement, sans prorata.</li>
          <li><strong>Annulation tardive :</strong> la moitié des crédits est rendue au client, l’autre moitié est versée au partenaire.</li>
          <li><strong>Absence :</strong> sans annulation ni passage, tous les crédits sont consommés et versés au partenaire (constaté 2 h après la fin du créneau).</li>
        </ul>
        {!canEdit && <p className="muted" style={{ fontSize: 13 }}>Modification réservée aux administrateurs.</p>}
      </section>
    </>
  );
}
