import { Marked } from "marked";

import { findDocByFile } from "./catalog";

const REPO = "https://github.com/shayaandanishansari/patient-registration-voice-agent";

export interface ResolvedLink {
  href: string;
  /** Opens in a new tab: another site, or a file the dashboard can't render. */
  external: boolean;
}

/**
 * Links in the markdown are written relative to docs/ so they work on GitHub.
 * Here, a link to another document on the Docs page opens that document, and
 * any other repo path opens on GitHub.
 */
export function resolveLink(href: string, base: string): ResolvedLink {
  if (href.startsWith("#")) return { href, external: false };
  if (/^[a-z][a-z0-9+.-]*:/i.test(href)) return { href, external: true };

  const url = new URL(href, "https://repo.invalid/docs/");
  const repoPath = decodeURIComponent(url.pathname).replace(/^\//, "");
  const doc = repoPath.startsWith("docs/") ? findDocByFile(repoPath.slice("docs/".length)) : undefined;
  if (doc?.kind === "document") return { href: `${base}/docs/${doc.slug}${url.hash}`, external: false };
  if (doc && "url" in doc) return { href: doc.url, external: true };
  return { href: `${REPO}/blob/main/${repoPath}${url.hash}`, external: true };
}

const escapeAttr = (value: string) => value.replace(/&/g, "&amp;").replace(/"/g, "&quot;");

/**
 * Renders our own markdown (docs/ files, the agent's prompts). Not for
 * untrusted input. `breaks` keeps single line breaks, as prompts are written.
 */
export function renderMarkdown(markdown: string, base: string, { breaks = false } = {}): string {
  const marked = new Marked({
    gfm: true,
    breaks,
    renderer: {
      link({ href, title, tokens }) {
        const link = resolveLink(href, base);
        const attrs = [
          `href="${escapeAttr(link.href)}"`,
          title ? `title="${escapeAttr(title)}"` : "",
          link.external ? 'target="_blank" rel="noreferrer"' : "",
        ].filter(Boolean);
        return `<a ${attrs.join(" ")}>${this.parser.parseInline(tokens)}</a>`;
      },
    },
  });
  return marked.parse(markdown, { async: false });
}
