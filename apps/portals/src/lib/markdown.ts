/**
 * Analyse minimale du Markdown des rapports SEO, en blocs de TEXTE.
 *
 * Aucun HTML n’est interprété : une balise <script> ou <img onerror> reste du texte, affiché échappé par React.
 * Les liens ne sont conservés que vers http(s) ; tout autre schéma (javascript:, data:…) devient du texte.
 */

export type Inline =
  | { t: "text"; v: string }
  | { t: "strong"; v: string }
  | { t: "em"; v: string }
  | { t: "code"; v: string }
  | { t: "link"; v: string; href: string };

export type Block =
  | { t: "h"; level: 1 | 2 | 3 | 4; c: Inline[] }
  | { t: "p"; c: Inline[] }
  | { t: "ul" | "ol"; items: Inline[][] }
  | { t: "quote"; c: Inline[] }
  | { t: "code"; v: string }
  | { t: "table"; head: Inline[][]; rows: Inline[][][] }
  | { t: "hr" };

const MAX_CHARS = 800_000;

export function safeHref(href: string): string | null {
  const value = href.trim();
  return /^https?:\/\/[^\s]+$/i.test(value) ? value : null;
}

export function parseInline(text: string): Inline[] {
  const out: Inline[] = [];
  const re = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*\s][^*]*\*)|(\[[^\]]+\]\([^)\s]+\))/g;
  let last = 0;
  for (const m of text.matchAll(re)) {
    const i = m.index ?? 0;
    if (i > last) out.push({ t: "text", v: text.slice(last, i) });
    const s = m[0];
    if (m[1]) out.push({ t: "code", v: s.slice(1, -1) });
    else if (m[2]) out.push({ t: "strong", v: s.slice(2, -2) });
    else if (m[3]) out.push({ t: "em", v: s.slice(1, -1) });
    else {
      const label = s.slice(1, s.indexOf("]("));
      const href = safeHref(s.slice(s.indexOf("](") + 2, -1));
      out.push(href ? { t: "link", v: label, href } : { t: "text", v: s });
    }
    last = i + s.length;
  }
  if (last < text.length) out.push({ t: "text", v: text.slice(last) });
  return out;
}

const cells = (line: string) =>
  line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((c) => parseInline(c.trim()));

export function parseMarkdown(md: string): Block[] {
  const lines = md.slice(0, MAX_CHARS).replace(/\r\n?/g, "\n").split("\n");
  const blocks: Block[] = [];
  let para: string[] = [];
  const flush = () => {
    if (para.length) blocks.push({ t: "p", c: parseInline(para.join(" ")) });
    para = [];
  };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const t = line.trim();
    if (t.startsWith("```")) {
      flush();
      const code: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) code.push(lines[i++]);
      blocks.push({ t: "code", v: code.join("\n") });
      continue;
    }
    if (!t) {
      flush();
      continue;
    }
    const h = /^(#{1,6})\s+(.*)$/.exec(t);
    if (h) {
      flush();
      blocks.push({ t: "h", level: Math.min(h[1].length, 4) as 1 | 2 | 3 | 4, c: parseInline(h[2]) });
      continue;
    }
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(t)) {
      flush();
      blocks.push({ t: "hr" });
      continue;
    }
    if (t.startsWith("|") && i + 1 < lines.length && /^\|?\s*:?-{2,}/.test(lines[i + 1].trim())) {
      flush();
      const head = cells(t);
      const rows: Inline[][][] = [];
      i += 2;
      while (i < lines.length && lines[i].trim().startsWith("|")) rows.push(cells(lines[i++]));
      i--;
      blocks.push({ t: "table", head, rows });
      continue;
    }
    const ul = /^[-*+]\s+(.*)$/.exec(t);
    const ol = /^\d+[.)]\s+(.*)$/.exec(t);
    if (ul || ol) {
      flush();
      const kind = ul ? "ul" : "ol";
      const items: Inline[][] = [];
      while (i < lines.length) {
        const m = kind === "ul" ? /^[-*+]\s+(.*)$/.exec(lines[i].trim()) : /^\d+[.)]\s+(.*)$/.exec(lines[i].trim());
        if (!m) break;
        items.push(parseInline(m[1]));
        i++;
      }
      i--;
      blocks.push({ t: kind, items });
      continue;
    }
    if (t.startsWith(">")) {
      flush();
      blocks.push({ t: "quote", c: parseInline(t.replace(/^>\s?/, "")) });
      continue;
    }
    para.push(t);
  }
  flush();
  return blocks;
}
