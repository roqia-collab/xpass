import { NextResponse } from "next/server";

import { ApiError, apiFetchRaw } from "@/lib/session";

/** Relevé CSV d'un versement, téléchargé via le serveur (le jeton ne quitte jamais le serveur). */
export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) return NextResponse.json({ detail: { message: "Introuvable." } }, { status: 404 });
  try {
    const res = await apiFetchRaw(`/partner/settlements/${id}/statement.csv`);
    if (!res.ok) return NextResponse.json({ detail: { message: "Relevé indisponible." } }, { status: res.status });
    return new NextResponse(res.body, {
      headers: {
        "Content-Type": res.headers.get("content-type") ?? "text/csv; charset=utf-8",
        "Content-Disposition": res.headers.get("content-disposition") ?? "attachment",
        "Cache-Control": "no-store",
      },
    });
  } catch (e) {
    return NextResponse.json({ detail: { message: e instanceof Error ? e.message : "Erreur." } }, { status: e instanceof ApiError ? e.status : 500 });
  }
}
