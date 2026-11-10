import { Notice, PageHead } from "@/components/ui";
import { apiFetch } from "@/lib/session";

import { ReviewModeration, type AdminReview } from "../review-moderation";

export const metadata = { title: "Avis" };

export default async function AdminReviewsPage() {
  const rows = await apiFetch<AdminReview[]>("/admin/reviews");
  return (
    <>
      <PageHead title="Avis clients" subtitle="Derniers avis laissés après une prestation. Masquez un avis inapproprié avec un motif (journal d’audit)." />
      {rows.length === 0 ? <Notice>Aucun avis pour le moment.</Notice> : <ReviewModeration rows={rows} />}
    </>
  );
}
