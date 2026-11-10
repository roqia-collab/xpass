import type { Metadata } from "next";
import { Manrope, Syne } from "next/font/google";
import Script from "next/script";
import type { ReactNode } from "react";

import "./globals.css";
import { Providers } from "./providers";

const display = Syne({ subsets: ["latin"], variable: "--font-display", weight: ["700", "800"] });
const body = Manrope({ subsets: ["latin"], variable: "--font-body" });

export const metadata: Metadata = {
  title: { default: "XPASS", template: "%s · XPASS" },
  description: "Le pass crédits du sport, de la culture, de la beauté et des sorties.",
  robots: { index: false },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr" className={`${display.variable} ${body.variable}`}>
      <body>
        <Script id="clear-stale-client" strategy="beforeInteractive">
          {`(function(){function wipe(){if(navigator.serviceWorker){navigator.serviceWorker.getRegistrations().then(function(regs){regs.forEach(function(r){r.unregister();});});}if(window.caches){caches.keys().then(function(keys){keys.forEach(function(k){caches.delete(k);});});}}wipe();})();`}
        </Script>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
