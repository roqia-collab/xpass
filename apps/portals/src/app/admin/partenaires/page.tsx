import { PageHead } from "@/components/ui";

import { MerchantsTable } from "./merchants-table";

export const metadata = { title: "Partenaires" };

export default function PartenairesPage() {
  return (
    <>
      <PageHead title="Partenaires" subtitle="Statut commercial et statut PSP de chaque marchand." />
      <MerchantsTable />
    </>
  );
}
