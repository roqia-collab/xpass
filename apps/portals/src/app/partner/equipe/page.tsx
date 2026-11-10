import { ErrorCard, Notice, PageHead } from "@/components/ui";

import { apiFetch } from "@/lib/session";

import { getManagedLocation } from "../data";
import { TeamAccess, type TeamAccessRow } from "../team-access";
import { TeamManager } from "../manage-forms";

export const metadata = { title: "Équipe" };

export default async function EquipePage() {
  const location = await getManagedLocation();
  if (!location) return <ErrorCard message="Aucun établissement n’est rattaché à ce compte." />;
  // Liste réservée au responsable (l’API refuse aux collaborateurs).
  const access = location.can_edit ? await apiFetch<TeamAccessRow[]>(`/partner/locations/${location.id}/access`) : null;
  return (
    <>
      <PageHead title="Équipe" subtitle="Professionnels, salles et équipements réservables." />
      <TeamManager location={location} />
      {access ? (
        <TeamAccess locationId={location.id} rows={access} />
      ) : (
        <Notice>Les accès au portail de vos collaborateurs sont gérés par le responsable de l’établissement.</Notice>
      )}
      <Notice>
        Une ressource (personne, salle, équipement) sert au planning et aux réservations ; un accès au portail est un compte de
        connexion. Une ressource qui a des réservations à venir ne peut pas être désactivée.
      </Notice>
    </>
  );
}
