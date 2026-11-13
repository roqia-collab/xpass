"use client";

import { Building2, CheckCircle2, MapPin, TriangleAlert } from "lucide-react";
import { useState, useTransition } from "react";

import { checkSiret, submitApplication, type CompanyPreview } from "./actions";

export interface CategoryOption {
  name: string;
  subs: { slug: string; name: string }[];
}

/** Rue exploitable à partir du libellé SIRENE (enlève le bâtiment, part du numéro). */
function streetFromSirene(address: string, postalCode: string, city: string): string {
  let line = address;
  if (postalCode) line = line.replace(new RegExp(postalCode.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"), " ");
  if (city) line = line.replace(new RegExp(city.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"), " ");
  const numbered = line.match(/\d+\s+\S.*/);
  return (numbered?.[0] ?? line).replace(/\s+/g, " ").replace(/^[ ,]+|[ ,]+$/g, "");
}

/** Étape 1 : SIRET vérifié dans l'annuaire ; étape 2 : établissement (adresse géocodée par l'API). */
export function SignupForm({ categories }: { categories: CategoryOption[] }) {
  const [siret, setSiret] = useState("");
  const [company, setCompany] = useState<CompanyPreview>();
  const [error, setError] = useState<string>();
  const [done, setDone] = useState<{ address: string; check: string; activity: string }>();
  const [pending, start] = useTransition();
  const [form, setForm] = useState({
    display_name: "",
    contact_phone: "",
    location_name: "",
    subcategory_slug: "",
    kind_label: "",
    address_line: "",
    postal_code: "",
    city: "",
    description: "",
    accept: false,
  });
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.type === "checkbox" ? (e.target as HTMLInputElement).checked : e.target.value });

  if (done) {
    return (
      <div className="card" role="status" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <h2><CheckCircle2 aria-hidden color="#2f7a45" /> Candidature envoyée</h2>
        <p>Activité retenue : <strong>{done.activity}</strong></p>
        <p>Adresse retenue : <strong>{done.address}</strong></p>
        {done.check === "unavailable" && (
          <p className="notice">L’annuaire des entreprises ne répondait pas : l’équipe XPASS vérifiera votre SIRET à la main.</p>
        )}
        <p className="muted">
          Votre établissement reste invisible des clients jusqu’à la validation par XPASS. Complétez-le dès maintenant :
          photo, prestations, horaires et équipe. Un e-mail de confirmation vous a été envoyé.
        </p>
        <a className="btn primary" href="/partner" style={{ alignSelf: "flex-start" }}>Ouvrir mon portail commerçant</a>
      </div>
    );
  }

  return (
    <>
      <section className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <h2><Building2 aria-hidden /> 1. Votre entreprise</h2>
        <form
          style={{ display: "flex", gap: 10, alignItems: "end", flexWrap: "wrap" }}
          onSubmit={(e) => {
            e.preventDefault();
            setError(undefined);
            start(async () => {
              const r = await checkSiret(siret);
              if (r.ok) {
                setCompany(r.company);
                const street = streetFromSirene(r.company.address || "", r.company.postal_code || "", r.company.city || "");
                setForm((f) => ({
                  ...f,
                  display_name: f.display_name || r.company.trade_name || "",
                  location_name: f.location_name || r.company.trade_name || r.company.legal_name || "",
                  address_line: f.address_line || street,
                  postal_code: f.postal_code || r.company.postal_code || "",
                  city: f.city || r.company.city || "",
                }));
              } else {
                setCompany(undefined);
                setError(r.error);
              }
            });
          }}
        >
          <label className="field" style={{ flex: 1, minWidth: 220 }}>
            <span>Numéro SIRET (14 chiffres)</span>
            <input inputMode="numeric" autoComplete="off" value={siret} onChange={(e) => setSiret(e.target.value)} placeholder="123 456 789 00012" required />
          </label>
          <button className="btn outline" type="submit" disabled={pending}>Vérifier</button>
        </form>
        {company?.status === "verified" && (
          <p className="notice mint" role="status">
            <CheckCircle2 size={18} aria-hidden /> <strong>{company.legal_name}</strong>
            {company.trade_name ? ` (${company.trade_name})` : ""} · établissement actif · {company.address}
          </p>
        )}
        {company?.status === "unavailable" && (
          <p className="notice" role="status">
            <TriangleAlert size={18} aria-hidden /> L’annuaire des entreprises ne répond pas pour l’instant. Vous pouvez continuer :
            le SIRET sera vérifié à la main par l’équipe XPASS.
          </p>
        )}
      </section>

      {company && (
        <form
          className="card"
          style={{ display: "flex", flexDirection: "column", gap: 14 }}
          onSubmit={(e) => {
            e.preventDefault();
            setError(undefined);
            start(async () => {
              const chosen = categories.flatMap((c) => c.subs).find((s) => s.slug === form.subcategory_slug);
              if (!chosen) {
                setError("Choisissez une activité dans la liste.");
                return;
              }
              const r = await submitApplication({ ...form, siret });
              if (r.ok) setDone({ address: r.address, check: r.check, activity: chosen.name });
              else setError(r.error);
            });
          }}
        >
          <h2><MapPin aria-hidden /> 2. Votre établissement</h2>
          <div className="signup-grid">
            <label className="field">
              <span>Nom de l’établissement *</span>
              <input value={form.location_name} onChange={set("location_name")} required maxLength={120} />
            </label>
            <label className="field">
              <span>Nom commercial (marque)</span>
              <input value={form.display_name} onChange={set("display_name")} maxLength={120} placeholder="Si différent" />
            </label>
            <label className="field">
              <span>Activité *</span>
              <select value={form.subcategory_slug} onChange={set("subcategory_slug")} required>
                <option value="">Choisir…</option>
                {categories.map((c) => (
                  <optgroup key={c.name} label={c.name}>
                    {c.subs.map((s) => <option key={s.slug} value={s.slug}>{s.name}</option>)}
                  </optgroup>
                ))}
              </select>
              {form.subcategory_slug && (
                <small>Activité retenue : {categories.flatMap((c) => c.subs).find((s) => s.slug === form.subcategory_slug)?.name}</small>
              )}
            </label>
            <label className="field">
              <span>Type d’établissement</span>
              <input value={form.kind_label} onChange={set("kind_label")} maxLength={80} placeholder="Ex. : Salon de coiffure" />
            </label>
            <label className="field full">
              <span>Numéro et rue *</span>
              <input value={form.address_line} onChange={set("address_line")} required autoComplete="street-address" placeholder="5 rue de la Roquette" />
            </label>
            <label className="field">
              <span>Code postal *</span>
              <input value={form.postal_code} onChange={set("postal_code")} required inputMode="numeric" autoComplete="postal-code" maxLength={5} />
            </label>
            <label className="field">
              <span>Commune *</span>
              <input value={form.city} onChange={set("city")} required autoComplete="address-level2" />
            </label>
            <label className="field">
              <span>Téléphone de contact *</span>
              <input value={form.contact_phone} onChange={set("contact_phone")} required type="tel" autoComplete="tel" />
            </label>
            <label className="field full">
              <span>Présentation (visible des clients)</span>
              <textarea value={form.description} onChange={set("description")} maxLength={2000} placeholder="Votre lieu, votre savoir-faire, l’ambiance…" />
            </label>
          </div>
          <label style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
            <input type="checkbox" checked={form.accept} onChange={set("accept")} style={{ marginTop: 4 }} />
            <span>Je certifie être habilité(e) à représenter cette entreprise et que les informations sont exactes.</span>
          </label>
          <button className="btn primary" type="submit" disabled={pending} style={{ alignSelf: "flex-start" }}>
            {pending ? "Envoi…" : "Envoyer ma candidature"}
          </button>
          <p className="muted" style={{ fontSize: 13 }}>
            L’adresse est placée sur la carte par la Base Adresse Nationale ; elle doit être exacte pour que vos clients vous trouvent.
          </p>
        </form>
      )}
      {error && <p className="error" role="alert">{error}</p>}
    </>
  );
}
