import { NextResponse, type NextRequest } from "next/server";

/** Chaque nom public ne montre qu'un espace. En local, les trois restent sur le même site. */
const SITES: Record<string, { home: string; prefixes: string[] }> = {
  "admin.xpass.fr": { home: "/admin", prefixes: ["/admin", "/auth", "/login", "/legal", "/api", "/_next", "/favicon.ico", "/logo.png", "/visuels"] },
  "rh.xpass.fr": { home: "/company", prefixes: ["/company", "/auth", "/login", "/legal", "/api", "/_next", "/favicon.ico", "/logo.png", "/visuels"] },
  "xpass.fr": { home: "/partner", prefixes: ["/partner", "/devenir-partenaire", "/inscription-partenaire", "/auth", "/login", "/legal", "/api", "/_next", "/favicon.ico", "/logo.png", "/visuels"] },
  "www.xpass.fr": { home: "/partner", prefixes: ["/partner", "/devenir-partenaire", "/inscription-partenaire", "/auth", "/login", "/legal", "/api", "/_next", "/favicon.ico", "/logo.png", "/visuels"] },
};

const GUARDED = ["/partner", "/company", "/admin", "/inscription-partenaire"];

function hostOf(req: NextRequest): string {
  return (req.headers.get("x-forwarded-host") ?? req.headers.get("host") ?? "")
    .split(",")[0]
    .trim()
    .toLowerCase()
    .replace(/:\d+$/, "");
}

function allowed(path: string, prefixes: string[]): boolean {
  return prefixes.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}

export function middleware(req: NextRequest) {
  const site = SITES[hostOf(req)];
  const path = req.nextUrl.pathname;
  if (site) {
    if (path === "/") {
      const url = req.nextUrl.clone();
      url.pathname = site.home;
      return NextResponse.redirect(url);
    }
    if (!allowed(path, site.prefixes)) return new NextResponse("Introuvable", { status: 404 });
  }
  if (!req.cookies.get("xpass_session") && GUARDED.some((prefix) => path === prefix || path.startsWith(`${prefix}/`))) {
    const url = req.nextUrl.clone();
    url.pathname = path === "/inscription-partenaire" ? "/devenir-partenaire" : "/login";
    url.search = "";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/((?!_next/static|_next/image).*)"] };
