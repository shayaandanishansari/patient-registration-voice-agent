// The documents shown on the Docs page. They're read from the repo's docs/
// folder at build time, so the page and the files can't drift apart. Only the
// files named in these globs are bundled: never widen them to docs/** (that
// would pull in docs/CONFIDENTIAL and docs/archive).

const MARKDOWN = import.meta.glob<string>(
  "../../../../docs/{approach,design-decisions,api-routes,costs,security}.md",
  { query: "?raw", import: "default", eager: true },
);
const FILES = import.meta.glob<string>(
  [
    "../../../../docs/identity-voiceagent.html",
    "../../../../docs/System Architecture.svg",
    "../../../../docs/patient_field_spec.xlsx",
  ],
  { query: "?url", import: "default", eager: true },
);

const inDocs = (file: string) => `../../../../docs/${file}`;

export type DocKind = "document" | "page" | "diagram" | "spreadsheet" | "agent";

interface DocBase {
  slug: string;
  /** The file's name in docs/, so links between documents can find it. */
  file?: string;
  title: string;
  description: string;
  kind: DocKind;
}

/** Rendered inside the dashboard at /docs/:slug. */
export interface MarkdownDoc extends DocBase {
  kind: "document";
  markdown: string;
}

/** Opened as-is in a new tab (HTML page, image) or downloaded. */
export interface FileDoc extends DocBase {
  kind: "page" | "diagram" | "spreadsheet";
  url: string;
}

/** The Retell agent, rendered from agent.json at /docs/agent. */
export interface AgentDoc extends DocBase {
  kind: "agent";
}

export type Doc = MarkdownDoc | FileDoc | AgentDoc;

type Entry = Omit<MarkdownDoc, "markdown"> | Omit<FileDoc, "url"> | AgentDoc;

// Display order. An entry whose file doesn't exist yet is left out.
const ENTRIES: Entry[] = [
  {
    slug: "approach",
    file: "approach.md",
    kind: "document",
    title: "My approach",
    description: "How I went about building this, in my own words.",
  },
  {
    slug: "design-decisions",
    file: "design-decisions.md",
    kind: "document",
    title: "Design decisions",
    description:
      "The forks in the road: where the brief left a choice open or would have caused a problem, what was chosen, and what it costs.",
  },
  {
    slug: "identity",
    file: "identity-voiceagent.html",
    kind: "page",
    title: "Identity of the voice agent (cultural context)",
    description:
      "Research memo on how U.S. hospitals split their phone lines, and why this one is a pre-registration and patient-access line. It drives the prompt's scope, identity checks and privacy rules.",
  },
  {
    slug: "architecture",
    file: "System Architecture.svg",
    kind: "diagram",
    title: "System architecture",
    description: "The caller, Retell, the backend, MongoDB and the dashboard, and how they talk.",
  },
  {
    slug: "agent",
    kind: "agent",
    title: "Voice agent prompt and flow",
    description:
      "The global prompt, every node's instructions, where each one branches, and the four tools, read from the Retell agent export.",
  },
  {
    slug: "api-routes",
    file: "api-routes.md",
    kind: "document",
    title: "API routes",
    description: "Every route the backend serves, grouped by who calls it, with the auth each one needs.",
  },
  {
    slug: "costs",
    file: "costs.md",
    kind: "document",
    title: "Costs",
    description:
      "What a call costs per minute and where the money goes (LLM, voice, telephony), the fixed costs, and where to see live spend.",
  },
  {
    slug: "security",
    file: "security.md",
    kind: "document",
    title: "Security review",
    description:
      "How only Retell and key holders reach the backend: signed requests, the API key, the browser login, and the checks behind them.",
  },
  {
    slug: "field-spec",
    file: "patient_field_spec.xlsx",
    kind: "spreadsheet",
    title: "Patient field spec",
    description: "The patient and call data model, field by field: type, validation rule, required. Downloads as .xlsx.",
  },
];

function resolve(entry: Entry): Doc | null {
  if (entry.kind === "agent") return entry;
  const path = inDocs(entry.file!);
  if (entry.kind === "document") {
    const markdown = MARKDOWN[path];
    return markdown === undefined ? null : { ...entry, markdown };
  }
  const url = FILES[path];
  return url === undefined ? null : { ...entry, url };
}

export const DOCS: Doc[] = ENTRIES.map(resolve).filter((d): d is Doc => d !== null);

export function findDoc(slug: string): Doc | undefined {
  return DOCS.find((d) => d.slug === slug);
}

export function findDocByFile(file: string): Doc | undefined {
  return DOCS.find((d) => d.file === file);
}
