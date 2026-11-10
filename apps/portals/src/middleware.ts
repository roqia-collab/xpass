import { NextResponse, type NextRequest } from "next/server";

// Contrôle rapide de présence de session. Le rôle est vérifié dans chaque layout (requireSpace)
// et, surtout, par l'API pour chaque objet.
export function middleware(req: NextRequest) {
  if (!req.cookies.get("xpass_session")) {
    const url = req.nextUrl.clone();
    url.pathname = req.nextUrl.pathname === "/inscription-partenaire" ? "/devenir-partenaire" : "/login";
    url.search = "";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/partner/:path*", "/company/:path*", "/admin/:path*", "/inscription-partenaire"] };
