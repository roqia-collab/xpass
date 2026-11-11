import { PageHead } from "@/components/ui";

import { MerchantsTable } from "./merchants-table";

export const metadata = { title: "Commerçants" };

export default function PartenairesPage() {
  return (
    <>
      <PageHead title="Commerçants" subtitle="Chaque commerçant publié apparaît dans l’application client." />
      <MerchantsTable />
    </>
  );
}
