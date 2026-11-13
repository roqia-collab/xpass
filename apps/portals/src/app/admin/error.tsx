"use client";

export default function AdminSectionError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="card" role="alert">
      <h1>Cette section n’a pas pu s’ouvrir</h1>
      <p>Les données n’ont pas pu être affichées. Les autres sections restent disponibles.</p>
      <button className="btn primary" type="button" onClick={reset}>Réessayer</button>
    </div>
  );
}
