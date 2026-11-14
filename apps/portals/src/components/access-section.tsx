const COPY = {
  rh: {
    title: "Devenir un service RH",
    lead: "L’espace RH s’ouvre après le formulaire. L’adresse de l’entreprise devient l’identifiant.",
    steps: [
      "Remplissez le formulaire avec l’adresse de l’entreprise, le nom du service et la ville.",
      "Après acceptation, l’identifiant et le mot de passe sont envoyés à cette adresse.",
      "Ouvrez rh.xpass.fr et connectez-vous avec cette adresse et ce mot de passe.",
    ],
  },
  merchant: {
    title: "Devenir commerçant",
    lead: "L’espace commerçant s’ouvre après le formulaire, ou lorsqu’un service RH crée votre établissement.",
    steps: [
      "Remplissez le formulaire avec l’adresse de l’établissement, son nom et l’activité.",
      "Après acceptation, l’identifiant et le mot de passe sont envoyés à cette adresse.",
      "Ouvrez xpass.fr, espace commerçant, et connectez-vous avec cette adresse et ce mot de passe.",
    ],
  },
} as const;

/** Section d’accès. Sur la connexion, elle reste dans le panneau, sans seconde carte. */
export function AccessSection({ kind, tone = "page" }: { kind: keyof typeof COPY; tone?: "panel" | "page" }) {
  const copy = COPY[kind];
  if (tone === "panel") {
    return (
      <section className="login-access" aria-labelledby={`acces-${kind}`}>
        <h3 id={`acces-${kind}`}>{copy.title}</h3>
        <p>{copy.lead}</p>
        <p className="login-partner">
          <a href="/demande">Remplir le formulaire</a>
          <span aria-hidden> · </span>
          <a href="mailto:support@xpass.fr">support@xpass.fr</a>
        </p>
      </section>
    );
  }
  return (
    <section className="card access-card" aria-labelledby={`acces-${kind}`}>
      <p className="eyebrow">Accès</p>
      <h2 id={`acces-${kind}`} style={{ margin: 0 }}>{copy.title}</h2>
      <p style={{ margin: 0 }}>{copy.lead}</p>
      <ol style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 6 }}>
        {copy.steps.map((step) => <li key={step}>{step}</li>)}
      </ol>
      <div className="access-actions">
        <a className="btn primary" href="/demande">Remplir le formulaire</a>
        <a className="btn outline" href="mailto:support@xpass.fr">support@xpass.fr</a>
      </div>
      <p className="muted" style={{ margin: 0 }}>
        Un problème de connexion ou de mot de passe : écrivez à support@xpass.fr. Indiquez l’adresse utilisée dans le formulaire.
      </p>
    </section>
  );
}
