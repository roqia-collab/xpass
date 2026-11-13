import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Hostinger fournit les variables pendant la compilation, pas au processus qui sert le site.
 * Ce fichier est lu uniquement par le serveur Next (import "server-only").
 */
const secret = process.env.OIDC_PORTALS_CLIENT_SECRET ?? "";
const apiUrl = process.env.XPASS_API_URL || "https://api.xpass.fr";
const issuer = process.env.OIDC_ISSUER || "https://auth.xpass.fr/realms/xpass";
const issuerPublic = process.env.OIDC_ISSUER_PUBLIC || "";
const publicUrl = process.env.PORTALS_PUBLIC_URL || "https://xpass.fr";
const publicUrls = process.env.PORTALS_PUBLIC_URLS || "";

const body = `import "server-only";

/** Généré par scripts/bake-server-env.mjs au moment de la compilation. Ne pas y mettre de secret à la main. */
export const baked = {
  secret: ${JSON.stringify(secret)},
  apiUrl: ${JSON.stringify(apiUrl)},
  issuer: ${JSON.stringify(issuer)},
  issuerPublic: ${JSON.stringify(issuerPublic)},
  publicUrl: ${JSON.stringify(publicUrl)},
  publicUrls: ${JSON.stringify(publicUrls)},
};
`;

const target = join(dirname(fileURLToPath(import.meta.url)), "..", "src", "lib", "server-baked.ts");
writeFileSync(target, body);
console.log(`server-baked: secret ${secret ? "present" : "absent"}, api ${apiUrl}`);
