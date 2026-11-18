import type { ReactNode } from "react";

import { type Inline, parseMarkdown } from "@/lib/markdown";

/** Rendu nettoyé du rapport : uniquement des éléments React construits à partir de texte (aucun HTML injecté). */
function inline(parts: Inline[]): ReactNode[] {
  return parts.map((p, i) => {
    if (p.t === "strong") return <strong key={i}>{p.v}</strong>;
    if (p.t === "em") return <em key={i}>{p.v}</em>;
    if (p.t === "code") return <code key={i}>{p.v}</code>;
    if (p.t === "link")
      return (
        <a key={i} href={p.href} target="_blank" rel="noopener noreferrer nofollow">
          {p.v}
        </a>
      );
    return <span key={i}>{p.v}</span>;
  });
}

export function SafeMarkdown({ source }: { source: string }) {
  const blocks = parseMarkdown(source);
  if (blocks.length === 0) return <p className="muted">Rapport Markdown vide.</p>;
  return (
    <div className="seo-markdown">
      {blocks.map((b, i) => {
        switch (b.t) {
          case "h": {
            const Tag = (["h2", "h3", "h4", "h5"] as const)[b.level - 1];
            return <Tag key={i}>{inline(b.c)}</Tag>;
          }
          case "p":
            return <p key={i}>{inline(b.c)}</p>;
          case "ul":
            return <ul key={i}>{b.items.map((it, j) => <li key={j}>{inline(it)}</li>)}</ul>;
          case "ol":
            return <ol key={i}>{b.items.map((it, j) => <li key={j}>{inline(it)}</li>)}</ol>;
          case "quote":
            return <blockquote key={i}>{inline(b.c)}</blockquote>;
          case "code":
            return <pre key={i}><code>{b.v}</code></pre>;
          case "hr":
            return <hr key={i} />;
          case "table":
            return (
              <div key={i} style={{ overflowX: "auto" }}>
                <table className="table">
                  <thead><tr>{b.head.map((c, j) => <th key={j}>{inline(c)}</th>)}</tr></thead>
                  <tbody>{b.rows.map((r, j) => <tr key={j}>{r.map((c, k) => <td key={k}>{inline(c)}</td>)}</tr>)}</tbody>
                </table>
              </div>
            );
        }
      })}
    </div>
  );
}
