import "@fontsource/syne/700.css";
import "@fontsource/syne/800.css";
import "@fontsource/manrope/400.css";
import "@fontsource/manrope/500.css";
import "@fontsource/manrope/600.css";
import "@fontsource/manrope/700.css";
import type { Metadata } from "next";
import Script from "next/script";
import type { ReactNode } from "react";

import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: { default: "XPASS", template: "%s · XPASS" },
  description: "Le pass crédits du sport, de la culture, de la beauté et des sorties.",
  robots: { index: false },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <Script id="clear-stale-client" strategy="beforeInteractive">
          {`(function(){function wipe(){if(navigator.serviceWorker){navigator.serviceWorker.getRegistrations().then(function(regs){regs.forEach(function(r){r.unregister();});});}if(window.caches){caches.keys().then(function(keys){keys.forEach(function(k){caches.delete(k);});});}}wipe();})();`}
        </Script>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
