import { NextResponse, type NextRequest } from "next/server";

import { ApiError, apiFetch } from "@/lib/session";

/**
 * BFF en LECTURE pour les composants clients (TanStack Query).
 * Le cookie HttpOnly est converti en jeton Bearer côté serveur. Les mutations ne passent
 * pas par ici : elles utiliseront des Server Actions (vérification d'origine / CSRF).
 */
const ALLOWED_PREFIXES = ["partner/", "company/", "admin/", "catalog/", "me"];

export async function GET(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const path = (await params).path.join("/");
  if (!ALLOWED_PREFIXES.some((p) => path === p || path.startsWith(p))) {
    return NextResponse.json({ detail: { message: "Chemin non autorisé." } }, { status: 404 });
  }
  try {
    const data = await apiFetch<unknown>(`/${path}${req.nextUrl.search}`);
    return NextResponse.json(data, { headers: { "Cache-Control": "no-store" } });
  } catch (e) {
    const status = e instanceof ApiError ? e.status : 500;
    const message = e instanceof Error ? e.message : "Erreur inattendue.";
    return NextResponse.json({ detail: { message } }, { status });
  }
}
