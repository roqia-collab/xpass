import { ScannerClient } from "./scanner-client";

export const metadata = { title: "Scanner" };

/** Maquettes 19 et 20 — scan ou code manuel, aperçu, puis confirmation explicite de la consommation. */
export default function ScannerPage() {
  return <ScannerClient mediaBase={process.env.NEXT_PUBLIC_MEDIA_BASE_URL ?? "http://localhost:8333/xpass-public"} />;
}
