import { ArrowRight, Info } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

export function PageHead({
  eyebrow,
  title,
  subtitle,
  action,
  image,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: ReactNode;
  action?: ReactNode;
  /** Photo d'en-tête des maquettes (à droite, fondue côté texte). Décorative. */
  image?: string;
}) {
  if (image) {
    return (
      <div className="page-head with-image">
        <div>
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          <h1 style={{ marginTop: eyebrow ? 8 : 0 }}>{title}</h1>
          {subtitle && (
            <p className="muted" style={{ marginTop: 10, fontSize: 17 }}>
              {subtitle}
            </p>
          )}
          {action && <div style={{ marginTop: 16 }}>{action}</div>}
        </div>
        <img className="hero-img" src={image} alt="" />
      </div>
    );
  }
  return (
    <div className="page-head">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1 style={{ marginTop: eyebrow ? 8 : 0 }}>{title}</h1>
        {subtitle && (
          <p className="muted" style={{ marginTop: 10, fontSize: 17 }}>
            {subtitle}
          </p>
        )}
      </div>
      {action}
    </div>
  );
}

/** Indicateur : une valeur réelle OU la mention explicite du lot qui la fournira. Jamais de chiffre inventé. */
export function Kpi({
  icon,
  label,
  value,
  detail,
  pendingLot,
  tone,
  href,
}: {
  icon: ReactNode;
  label: string;
  value?: number | string;
  detail?: string;
  pendingLot?: string;
  tone?: "coral";
  href?: string;
}) {
  const body = (
    <>
      <div className={`icon ${tone ?? ""}`} aria-hidden>
        {icon}
      </div>
      <div style={{ flex: 1 }}>
        <p style={{ fontWeight: 600 }}>{label}</p>
        {value !== undefined ? (
          <p className="value" style={{ margin: "6px 0" }}>
            {value}
          </p>
        ) : (
          <p className="na" style={{ margin: "8px 0" }}>
            Disponible au {pendingLot}
          </p>
        )}
        {detail && <p className="muted">{detail}</p>}
      </div>
      {href && <ArrowRight aria-hidden />}
    </>
  );
  if (href) return <Link href={href} className="card kpi">{body}</Link>;
  return <div className="card kpi">{body}</div>;
}

export function Badge({ tone, children }: { tone: "lavender" | "coral" | "mint" | "grey"; children: ReactNode }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function Notice({ children, tone }: { children: ReactNode; tone?: "mint" }) {
  return (
    <div className={`notice ${tone ?? ""}`}>
      <Info size={18} aria-hidden style={{ flexShrink: 0, marginTop: 1 }} />
      <div>{children}</div>
    </div>
  );
}

export function ComingSoon({ title, lot, children }: { title: string; lot: string; children: ReactNode }) {
  return (
    <>
      <PageHead title={title} />
      <div className="card" style={{ maxWidth: 720 }}>
        <Badge tone="lavender">Bientôt disponible · {lot}</Badge>
        <div className="muted" style={{ marginTop: 14, fontSize: 16, lineHeight: 1.5 }}>
          {children}
        </div>
      </div>
    </>
  );
}

export function ErrorCard({ message }: { message: string }) {
  return (
    <div className="card" role="alert">
      <p className="error">{message}</p>
    </div>
  );
}
