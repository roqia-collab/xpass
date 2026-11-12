import { MerchantSite } from "@/components/merchant-site";
import { getMe } from "@/lib/session";

export const metadata = { title: "Tableau de bord" };

/** Tableau de bord commerçant visible, après la présentation du site. */
export default async function PublicDashboard() {
  let me = null;
  try {
    me = await getMe();
  } catch {
    me = null;
  }
  return <MerchantSite signedIn={Boolean(me)} />;
}
