import type { ReactNode } from "react";
import { Link } from "react-router";

import { Badge } from "@/components/Badge";

import { DOCS, thumbnailFor, type Doc, type DocKind } from "../catalog";

const KIND_LABELS: Record<DocKind, string> = {
  document: "Document",
  page: "Web page",
  diagram: "Diagram",
  spreadsheet: "Spreadsheet",
  agent: "Retell agent",
};

const cardClass =
  "group flex h-full flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition-colors hover:border-brand-100 hover:bg-brand-50/40";

function DocLink({ doc, className, children }: { doc: Doc; className: string; children: ReactNode }) {
  // data-doc-* let `npm run thumbnails` find each card and what it opens.
  const data = { "data-doc-slug": doc.slug, "data-doc-kind": doc.kind };
  if (doc.kind === "document" || doc.kind === "agent" || doc.kind === "diagram") {
    return (
      <Link to={`/docs/${doc.slug}`} className={className} {...data}>
        {children}
      </Link>
    );
  }
  if (doc.kind === "spreadsheet") {
    return (
      <a href={doc.url} download={doc.file} className={className} {...data}>
        {children}
      </a>
    );
  }
  return (
    <a href={doc.url} target="_blank" rel="noreferrer" className={className} {...data}>
      {children}
    </a>
  );
}

function Preview({ doc }: { doc: Doc }) {
  const src = thumbnailFor(doc.slug);
  return (
    <div className="aspect-[16/10] overflow-hidden border-b border-slate-100 bg-slate-100">
      {src ? (
        <img
          src={src}
          alt=""
          loading="lazy"
          className="size-full object-cover object-top transition-transform duration-300 group-hover:scale-[1.02]"
        />
      ) : (
        <div className="flex size-full items-center justify-center text-sm font-medium text-slate-400">
          {KIND_LABELS[doc.kind]}
        </div>
      )}
    </div>
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
        <h1 className="text-xl font-semibold text-slate-900">Design docs</h1>
        <p className="text-sm text-slate-500">
          Why the system is built the way it is, and what another engineer needs to take it over.
        </p>
      </div>
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {DOCS.map((doc) => (
          <li key={doc.slug}>
            <DocLink doc={doc} className={cardClass}>
              <Preview doc={doc} />
              <div className="flex flex-1 flex-col p-5">
                <div>
                  <Badge tone={doc.kind === "document" ? "brand" : "neutral"}>{KIND_LABELS[doc.kind]}</Badge>
                </div>
                <h2 className="mt-3 font-semibold text-slate-900">{doc.title}</h2>
                <p className="mt-1 flex-1 text-sm text-slate-600">{doc.description}</p>
                <p className="mt-4 text-xs font-medium text-brand-700 group-hover:underline">{ACTION[doc.kind]}</p>
              </div>
            </DocLink>
          </li>
        ))}
      </ul>
    </div>
  );
}
