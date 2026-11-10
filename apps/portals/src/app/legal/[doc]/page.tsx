import { readFile } from "node:fs/promises";
import path from "node:path";

import type { Metadata } from "next";
import { notFound } from "next/navigation";

/** Documents légaux publics (clients, partenaires, confidentialité, mentions). Sans connexion. */
const DOCS: Record<string, { file: string; title: string }> = {
  cgu: { file: "cgu.md", title: "Conditions générales d’utilisation" },
  partenaires: { file: "conditions-partenaires.md", title: "Conditions partenaires" },
  confidentialite: { file: "confidentialite.md", title: "Politique de confidentialité" },
  "mentions-legales": { file: "mentions-legales.md", title: "Mentions légales" },
};

export async function generateMetadata({ params }: { params: Promise<{ doc: string }> }): Promise<Metadata> {
  const { doc } = await params;
  return { title: DOCS[doc]?.title ?? "Document" };
}

/** Rendu minimal et sûr du Markdown des documents (titres, paragraphes, listes, gras) : aucun HTML injecté. */
function render(md: string) {
  const blocks: React.ReactNode[] = [];
  let list: string[] = [];
  const inline = (t: string, k: string) =>
    t.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
      part.startsWith("**") ? <strong key={`${k}-${i}`}>{part.slice(2, -2)}</strong> : <span key={`${k}-${i}`}>{part}</span>,
    );
  const flush = () => {
    if (list.length) {
      const items = list;
      blocks.push(<ul key={`ul-${blocks.length}`}>{items.map((x, i) => <li key={i}>{inline(x, `li${i}`)}</li>)}</ul>);
      list = [];
    }
  };
  md.split("\n").forEach((line, i) => {
    const t = line.trim();
    if (t.startsWith("- ")) return void list.push(t.slice(2));
    flush();
    if (!t) return;
    if (t.startsWith("# ")) blocks.push(<h1 key={i}>{t.slice(2)}</h1>);
    else if (t.startsWith("## ")) blocks.push(<h2 key={i} style={{ marginTop: 24 }}>{t.slice(3)}</h2>);
    else blocks.push(<p key={i} style={{ marginTop: 8, lineHeight: 1.6 }}>{inline(t, `p${i}`)}</p>);
  });
  flush();
  return blocks;
}

export default async function LegalPage({ params }: { params: Promise<{ doc: string }> }) {
  const { doc } = await params;
  const entry = DOCS[doc];
  if (!entry) notFound();
  const md = await readFile(path.join(process.cwd(), "src", "legal", entry.file), "utf-8");
  const validated = process.env.LEGAL_VALIDATED === "true";
  return (
    <main className="partner-landing" style={{ maxWidth: 820 }}>
      <header className="landing-top">
        <a href="/login"><img src="/logo.png" alt="XPASS" style={{ height: 32 }} /></a>
        <nav style={{ display: "flex", gap: 14, flexWrap: "wrap", fontSize: 14 }}>
          {Object.entries(DOCS).map(([k, v]) => <a key={k} href={`/legal/${k}`} aria-current={k === doc ? "page" : undefined}>{v.title}</a>)}
        </nav>
      </header>
      {!validated && (
        <p className="notice" role="note">
          <strong>Modèle en cours de validation juridique.</strong>&nbsp;Les passages entre crochets restent à compléter ; ce document
          n’engage pas XPASS tant qu’il n’est pas publié dans sa version définitive.
        </p>
      )}
      <article className="card legal">{render(md)}</article>
    </main>
  );
}
