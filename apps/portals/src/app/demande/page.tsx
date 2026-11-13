import type { Metadata } from "next";

import { AccessForm } from "./form";

export const metadata: Metadata = { title: "Demander un accès" };

export default function AccessRequestPage() {
  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "28px 20px 80px" }}>
      <a href="/" aria-label="XPASS">
        <img src="/logo.png" alt="XPASS" width={120} height={36} />
      </a>
      <p className="eyebrow" style={{ marginTop: 28 }}>Formulaire</p>
      <h1>Demander un accès</h1>
      <p className="muted">
        L’administrateur reçoit votre demande. S’il l’accepte, il crée votre identifiant — votre Gmail — et un mot de passe, puis il vous les donne.
        Un service RH remet ensuite l’identifiant de ses commerçants. Un commerçant publié apparaît dans l’application.
      </p>
      <AccessForm />
    </main>
  );
}
