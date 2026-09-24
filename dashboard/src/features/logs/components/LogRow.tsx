import { useState } from "react";

import { summarize } from "../summary";
import type { LogEntry } from "../types";

const LEVEL_STYLES: Record<string, string> = {
  DEBUG: "bg-slate-100 text-slate-600",
  INFO: "bg-brand-50 text-brand-700",
  WARNING: "bg-amber-50 text-amber-800",
  ERROR: "bg-rose-50 text-rose-700",
  CRITICAL: "bg-rose-600 text-white",
};

const ROW_ACCENT: Record<string, string> = {
  WARNING: "border-l-amber-400",
  ERROR: "border-l-rose-500",
  CRITICAL: "border-l-rose-600",
};

function formatTime(iso: string): string {
  const date = new Date(iso);
  const time = date.toLocaleTimeString(undefined, { hour12: false });
  return `${time}.${String(date.getMilliseconds()).padStart(3, "0")}`;
}

export function LogRow({
  entry,
  onShowRequest,
}: {
  entry: LogEntry;
  onShowRequest: (requestId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const hasFields = Object.keys(entry.fields ?? {}).length > 0;

  return (
    <li className={`border-l-2 ${ROW_ACCENT[entry.level] ?? "border-l-transparent"}`}>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="grid w-full grid-cols-[auto_auto_1fr] items-baseline gap-x-3 gap-y-0.5 px-3 py-2 text-left hover:bg-slate-50 sm:grid-cols-[1rem_7.5rem_5.5rem_minmax(8rem,14rem)_1fr]"
      >
        <span aria-hidden className={`hidden text-slate-400 transition-transform sm:block ${open ? "rotate-90" : ""}`}>
          ›
        </span>
        <time dateTime={entry.ts} className="font-mono text-xs tabular-nums text-slate-500">
          {formatTime(entry.ts)}
        </time>
        <span
          className={`w-fit rounded px-1.5 py-0.5 text-[11px] font-semibold tracking-wide ${
            LEVEL_STYLES[entry.level] ?? LEVEL_STYLES.DEBUG
          }`}
        >
          {entry.level}
        </span>
        <span className="col-span-3 truncate font-mono text-sm font-medium text-slate-800 sm:col-span-1">
          {entry.event ?? entry.logger}
        </span>
        <span className="col-span-3 truncate font-mono text-xs text-slate-500 sm:col-span-1">
          {summarize(entry)}
        </span>
      </button>

      {open && (
        <div className="space-y-3 border-t border-slate-100 bg-slate-50/70 px-4 py-3 sm:pl-10">
          <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500">
            <div>
              <dt className="inline font-medium">Time </dt>
              <dd className="inline font-mono">{new Date(entry.ts).toLocaleString()}</dd>
            </div>
            <div>
              <dt className="inline font-medium">Source </dt>
              <dd className="inline font-mono">
                {entry.logger}
                {entry.func && ` · ${entry.func}:${entry.line}`}
              </dd>
            </div>
            {entry.environment && (
              <div>
                <dt className="inline font-medium">Env </dt>
                <dd className="inline font-mono">{entry.environment}</dd>
              </div>
            )}
            {entry.request_id && (
              <div>
                <dt className="inline font-medium">Request </dt>
                <dd className="inline">
                  <button
                    type="button"
                    onClick={() => onShowRequest(entry.request_id!)}
                    className="font-mono text-brand-700 hover:underline"
                    title="Show every record from this request"
                  >
                    {entry.request_id}
                  </button>
                </dd>
              </div>
            )}
          </dl>

          {entry.message && (
            <pre className="whitespace-pre-wrap break-words font-mono text-xs text-slate-700">{entry.message}</pre>
          )}
          {hasFields && (
            <pre className="max-h-[28rem] overflow-auto rounded-lg border border-slate-200 bg-white p-3 font-mono text-xs leading-relaxed text-slate-700">
              {JSON.stringify(entry.fields, null, 2)}
            </pre>
          )}
          {entry.exception && (
            <pre className="max-h-80 overflow-auto rounded-lg bg-rose-50 p-3 font-mono text-xs text-rose-800">
              {entry.exception}
            </pre>
          )}
        </div>
      )}
    </li>
  );
}
