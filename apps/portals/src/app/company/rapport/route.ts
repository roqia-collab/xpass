import { NextResponse, type NextRequest } from "next/server";

import { apiFetchRaw } from "@/lib/session";

/** Export CSV du rapport agrégé (le jeton reste côté serveur). */
export async function GET(req: NextRequest) {
  const period = req.nextUrl.searchParams.get("period");
  const qs = period && /^\d{4}-\d{2}$/.test(period) ? `?period=${period}` : "";
  const res = await apiFetchRaw(`/company/report.csv${qs}`);
  if (!res.ok) return NextResponse.json({ detail: { message: "Rapport indisponible." } }, { status: res.status });
  return new NextResponse(res.body, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": res.headers.get("content-disposition") ?? "attachment",
      "Cache-Control": "no-store",
    },
  });
}
