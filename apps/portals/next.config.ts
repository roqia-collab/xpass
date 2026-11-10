import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Image Docker de production légère (serveur Node autonome).
  output: "standalone",
  // Racine du projet = ce dossier (un package-lock.json parent ne doit pas être pris pour la racine).
  outputFileTracingRoot: process.cwd(),
  // Le badge de développement Next.js recouvrait la barre du bas sur téléphone.
  devIndicators: false,
  experimental: { serverActions: { bodySizeLimit: "9mb" } },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
};

export default config;
