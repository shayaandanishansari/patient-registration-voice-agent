import type { ReactNode } from "react";
import { Link } from "react-router";

import { Badge } from "@/components/Badge";

import { DOCS, type Doc, type DocKind } from "../catalog";

const KIND_LABELS: Record<DocKind, string> = {
  document: "Document",
  page: "Web page",
  diagram: "Diagram",
  spreadsheet: "Spreadsheet",
  agent: "Retell agent",
};

const cardClass =
  "group flex h-full flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-colors hover:border-brand-100 hover:bg-brand-50/40";

function DocLink({ doc, className, children }: { doc: Doc; className: string; children: ReactNode }) {
  if (doc.kind === "document" || doc.kind === "agent" || doc.kind === "diagram") {
    return (
      <Link to={`/docs/${doc.slug}`} className={className}>
        {children}
      </Link>
    );
  }
  if (doc.kind === "spreadsheet") {
    return (
      <a href={doc.url} download={doc.file} className={className}>
        {children}
      </a>
    );
  }
  return (
    <a href={doc.url} target="_blank" rel="noreferrer" className={className}>
      {children}
    </a>
  );
}

const ACTION: Record<DocKind, string> = {
  document: "Read →",
  agent: "Read →",
  page: "Open in new tab ↗",
  diagram: "View →",
  spreadsheet: "Download ↓",
};

export function DocsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Docs</h1>
        <p className="text-sm text-slate-500">
          How the system was designed and why, written alongside the code.
        </p>
      </div>
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {DOCS.map((doc) => (
          <li key={doc.slug}>
            <DocLink doc={doc} className={cardClass}>
              <Badge tone={doc.kind === "document" ? "brand" : "neutral"}>{KIND_LABELS[doc.kind]}</Badge>
              <h2 className="mt-3 font-semibold text-slate-900">{doc.title}</h2>
              <p className="mt-1 flex-1 text-sm text-slate-600">{doc.description}</p>
              <p className="mt-4 text-xs font-medium text-brand-700 group-hover:underline">{ACTION[doc.kind]}</p>
            </DocLink>
          </li>
        ))}
      </ul>
    </div>
  );
}
