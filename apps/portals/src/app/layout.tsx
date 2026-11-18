import "@fontsource/syne/700.css";
import "@fontsource/syne/800.css";
import "@fontsource/manrope/400.css";
import "@fontsource/manrope/500.css";
import "@fontsource/manrope/600.css";
import "@fontsource/manrope/700.css";
import type { Metadata, Viewport } from "next";
import Script from "next/script";
import type { ReactNode } from "react";

import "./globals.css";
import { Providers } from "./providers";
import { MotionLayer } from "@/components/motion-layer";
import { SITE_URL } from "@/lib/seo";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "XPASS", template: "%s · XPASS" },
  description: "Le pass crédits du sport, de la culture, de la beauté et des sorties.",
  // Par défaut rien n'est indexé (admin, RH, espace commerçant, connexion).
  // Les pages publiques de xpass.fr l'autorisent elles-mêmes : voir publicPageDefaults (lib/seo.ts).
  robots: { index: false },
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "48x48" },
      { url: "/icon-192.png", type: "image/png", sizes: "192x192" },
      { url: "/icon-512.png", type: "image/png", sizes: "512x512" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
  manifest: "/site.webmanifest",
  applicationName: "XPASS",
  openGraph: {
    siteName: "XPASS",
    locale: "fr_FR",
    type: "website",
    images: [{ url: "/video/xpass-pub-poster.jpg", width: 1920, height: 1080, alt: "XPASS" }],
  },
  twitter: { card: "summary_large_image" },
};

export const viewport: Viewport = { themeColor: "#0a0f1c" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <Script id="clear-stale-client" strategy="beforeInteractive">
          {`(function(){function wipe(){if(navigator.serviceWorker){navigator.serviceWorker.getRegistrations().then(function(regs){regs.forEach(function(r){r.unregister();});});}if(window.caches){caches.keys().then(function(keys){keys.forEach(function(k){caches.delete(k);});});}}wipe();})();`}
        </Script>
        <Providers>{children}</Providers>
        <MotionLayer />
      </body>
    </html>
  );
}
