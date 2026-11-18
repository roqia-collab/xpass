import { NextResponse, type NextRequest } from "next/server";

import { ApiError, apiFetchRaw } from "@/lib/session";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Téléchargement du rapport Markdown (rapport-seo-xpass-AAAA-MM-JJ.md). Droits vérifiés par l’API. */
export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!UUID.test(id)) return NextResponse.json({ detail: { message: "Rapport introuvable." } }, { status: 404 });
  try {
    const res = await apiFetchRaw(`/admin/seo/reports/${id}/markdown`);
    if (!res.ok) return NextResponse.json({ detail: { message: "Rapport indisponible." } }, { status: res.status });
    const disposition = res.headers.get("content-disposition") ?? "";
    const name = /filename="(rapport-seo-xpass-\d{4}-\d{2}-\d{2}\.md)"/.exec(disposition)?.[1] ?? "rapport-seo-xpass.md";
    return new NextResponse(res.body, {
      headers: {
        "Content-Type": "text/markdown; charset=utf-8",
        "Content-Disposition": `attachment; filename="${name}"`,
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch (e) {
    const status = e instanceof ApiError ? e.status : 500;
    return NextResponse.json({ detail: { message: "Rapport indisponible." } }, { status });
  }
}
