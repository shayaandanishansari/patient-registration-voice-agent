import { useMemo, type MouseEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router";

import { Card } from "@/components/Card";

import { findDoc, type FileDoc, type MarkdownDoc } from "../catalog";
import { renderMarkdown } from "../markdown";
import { AgentFlowDoc } from "./AgentFlowDoc";

// "/dashboard" in the build the backend serves, "" standalone.
const BASE = import.meta.env.BASE_URL.replace(/\/$/, "");

function MarkdownView({ doc }: { doc: MarkdownDoc }) {
  const navigate = useNavigate();
  const html = useMemo(() => renderMarkdown(doc.markdown, BASE), [doc.markdown]);

  // Links to other docs are plain <a> tags in the rendered HTML; route them
  // through React Router instead of reloading the page.
  function onClick(event: MouseEvent<HTMLDivElement>) {
    const anchor = (event.target as HTMLElement).closest("a");
    const href = anchor?.getAttribute("href");
    if (!anchor || !href || anchor.target || !href.startsWith(`${BASE}/docs/`)) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    event.preventDefault();
    navigate(href.slice(BASE.length));
  }

  return (
    <Card>
      <div
        className="prose prose-slate max-w-none prose-h1:text-2xl prose-h1:font-semibold prose-h2:text-lg prose-a:text-brand-700 prose-code:before:content-none prose-code:after:content-none prose-table:text-sm"
        onClick={onClick}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </Card>
  );
}

// The diagram is far wider than a window; fit it to the page and link the full size.
function DiagramView({ doc }: { doc: FileDoc }) {
  return (
    <Card
      title={doc.title}
      actions={
        <a href={doc.url} target="_blank" rel="noreferrer" className="text-xs font-medium text-brand-700 hover:underline">
          Full size ↗
        </a>
      }
    >
      <img src={doc.url} alt={doc.title} className="w-full rounded-lg bg-[#121212]" />
    </Card>
  );
}

/** /docs/:slug — a markdown document, the diagram or the agent view. Other files open from the Docs page. */
export function DocRoute() {
  const { slug = "" } = useParams();
  const doc = findDoc(slug);
  if (!doc || doc.kind === "page" || doc.kind === "spreadsheet") return <Navigate to="/docs" replace />;

  return (
    <div className="space-y-6">
      <Link to="/docs" className="text-sm text-slate-500 hover:text-slate-800">
        ← All docs
      </Link>
      {doc.kind === "agent" ? (
        <AgentFlowDoc />
      ) : doc.kind === "document" ? (
        <MarkdownView doc={doc} />
      ) : (
        <DiagramView doc={doc} />
      )}
    </div>
  );
}
