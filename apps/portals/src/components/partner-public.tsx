"use client";

import { useState, useTransition } from "react";

import { ACTIVITIES } from "@/lib/activities";
import { submitAccessRequest } from "@/app/demande/actions";

const euros = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });

export const PARTNER_FAQ = [
  {
    q: "XPASS prend-il les places de ma clientèle habituelle ?",
    a: "Vous publiez les créneaux que vous ouvrez. Vos clients habituels gardent leurs rendez-vous. Les membres XPASS remplissent seulement les places que vous mettez dans le planning.",
  },
  {
    q: "Combien me rapporte une visite ?",
    a: "Un crédit vaut 1,00 € brut. XPASS retient 10 %. Vous recevez 0,90 € par crédit, après le scan du QR code, au règlement de la semaine.",
  },
  {
    q: "Comment je gère mon planning ?",
    a: "Le tableau de bord réunit les horaires, les prestations, les événements et le nombre de places. Le scanner valide le passage au moment où le membre arrive.",
  },
  {
    q: "Qui réserve chez moi ?",
    a: "Des particuliers abonnés, et des salariés dont l’entreprise a ouvert un service RH. Ils paient en crédits dans l’application.",
  },
  {
    q: "Faut-il une adresse Gmail ?",
    a: "L’adresse de l’entreprise suffit, par exemple contact@votre-site.fr. Elle devient l’identifiant. Le mot de passe est envoyé sur cette boîte après validation.",
  },
  {
    q: "Combien coûte l’ouverture ?",
    a: "Le compte est gratuit. La commission de 10 % est prélevée sur les visites validées, pas à l’inscription.",
  },
] as const;

export function RevenueCalculator() {
  const [visits, setVisits] = useState(20);
  const [credits, setCredits] = useState(2);
  const gross = visits * credits * 4;
  const net = gross * 0.9;
  return (
    <form className="calc" onSubmit={(e) => e.preventDefault()}>
      <label>
        <span>Visites XPASS par semaine</span>
        <input type="number" min={1} max={400} value={visits} onChange={(e) => setVisits(Math.min(400, Math.max(1, Number(e.target.value) || 1)))} />
      </label>
      <label>
        <span>Crédits par visite</span>
        <input type="number" min={1} max={40} value={credits} onChange={(e) => setCredits(Math.min(40, Math.max(1, Number(e.target.value) || 1)))} />
      </label>
      <div className="calc-result">
        <p>Estimation sur 4 semaines</p>
        <strong>{euros.format(net)}</strong>
        <small>Net pour vous. Brut {euros.format(gross)}, commission 10 %. Sans garantie : seules les visites validées sont réglées.</small>
      </div>
    </form>
  );
}

export function PartnerFaq() {
  return (
    <div className="faq-list">
      {PARTNER_FAQ.map((item) => (
        <details key={item.q}>
          <summary>{item.q}</summary>
          <p>{item.a}</p>
        </details>
      ))}
    </div>
  );
}

export function PartnerStart({ defaultKind = "merchant" }: { defaultKind?: "merchant" | "rh" }) {
  const [kind, setKind] = useState<"merchant" | "rh">(defaultKind);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [place, setPlace] = useState("");
  const [activity, setActivity] = useState("");
  const [city, setCity] = useState("Paris");
  const [phone, setPhone] = useState("");
  const [site, setSite] = useState("");
  const [pending, start] = useTransition();
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  if (done) {
    return (
      <div className="partners-form done" role="status">
        <h2>Demande envoyée</h2>
        <p>L’administrateur la voit dans son espace. S’il la valide, l’identifiant et le mot de passe partent vers {email}.</p>
        <a className="btn primary" href="/tableau">Voir le tableau de bord</a>
      </div>
    );
  }

  return (
    <form
      className="partners-form"
      id="demarrer"
      onSubmit={(e) => {
        e.preventDefault();
        if (!activity) {
          setError("Choisissez une activité.");
          return;
        }
        setError("");
        const message = [
          `Activité : ${activity}`,
          phone.trim() ? `Téléphone : ${phone.trim()}` : "",
          site.trim() ? `Site : ${site.trim()}` : "",
        ].filter(Boolean).join("\n");
        start(async () => {
          const res = await submitAccessRequest({
            kind,
            gmail: email,
            full_name: fullName,
            place_name: place,
            city,
            message,
            website: "",
          });
          if (!res.ok) setError(res.error);
          else setDone(true);
        });
      }}
    >
      <h2>Vous souhaitez remplir vos créneaux ?</h2>
      <p>L’adresse de l’entreprise reçoit l’identifiant et le mot de passe.</p>
      <div className="kind-pills" role="group" aria-label="Type de demande">
        <button type="button" className={kind === "merchant" ? "on" : ""} onClick={() => setKind("merchant")}>Commerçant</button>
        <button type="button" className={kind === "rh" ? "on" : ""} onClick={() => setKind("rh")}>Service RH</button>
      </div>
      <label>
        <span>Adresse e-mail</span>
        <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="contact@entreprise.fr" />
      </label>
      <label>
        <span>Votre nom</span>
        <input required autoComplete="name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
      </label>
      <label>
        <span>{kind === "rh" ? "Nom du service RH" : "Nom de l’établissement"}</span>
        <input required value={place} onChange={(e) => setPlace(e.target.value)} />
      </label>
      <div className="form-split">
        <label>
          <span>Activité</span>
          <select required value={activity} onChange={(e) => setActivity(e.target.value)}>
            <option value="">Choisir</option>
            {ACTIVITIES.map((item) => <option key={item.slug} value={item.name}>{item.name}</option>)}
          </select>
        </label>
        <label>
          <span>Ville</span>
          <input required value={city} onChange={(e) => setCity(e.target.value)} />
        </label>
      </div>
      <div className="form-split">
        <label>
          <span>Téléphone</span>
          <input type="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="06 …" />
        </label>
        <label>
          <span>Site ou réseau</span>
          <input value={site} onChange={(e) => setSite(e.target.value)} placeholder="votre-site.fr" />
        </label>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="btn primary" disabled={pending}>{pending ? "Envoi…" : "Démarrer"}</button>
      <small>Ouverture gratuite. La commission de 10 % est prise sur les visites validées.</small>
    </form>
  );
}
