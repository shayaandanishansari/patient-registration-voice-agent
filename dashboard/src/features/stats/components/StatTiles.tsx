import type { ReactNode } from "react";
import { Link } from "react-router";

import { ErrorMessage } from "@/components/QueryState";
import { formatDuration } from "@/lib/format";

import { useStats } from "../api/queries";

function StatTile({
  to,
  label,
  value,
  hint,
  tone = "neutral",
  indicator,
}: {
  to: string;
  label: string;
  value: number | undefined;
  hint?: ReactNode;
  tone?: "neutral" | "danger";
  indicator?: ReactNode;
}) {
  return (
    <Link
      to={to}
      className="group rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-colors hover:border-brand-100 hover:bg-brand-50/40"
    >
      <p className="flex items-center gap-2 text-sm font-medium text-slate-500">
        {indicator}
        {label}
      </p>
      <p
        className={`mt-2 text-3xl font-semibold tabular-nums ${
          tone === "danger" ? "text-rose-600" : "text-slate-900"
        }`}
      >
        {value ?? "—"}
      </p>
      <p className="mt-1 min-h-4 text-xs text-slate-500">{hint}</p>
    </Link>
  );
}

function LiveDot({ active }: { active: boolean }) {
  return (
    <span className="relative flex size-2">
      {active && (
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-brand-500 opacity-75" />
      )}
      <span
        className={`relative inline-flex size-2 rounded-full ${active ? "bg-brand-500" : "bg-slate-300"}`}
      />
    </span>
  );
}

/** The homepage's headline numbers, each linking to the page behind it. */
export function StatTiles() {
  const { data: stats, error } = useStats();
  const live = stats?.live_calls ?? 0;
  const problems = (stats?.errors_24h ?? 0) + (stats?.warnings_24h ?? 0);

  return (
    <div className="space-y-3">
      {error && <ErrorMessage error={error} />}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatTile
          to="/calls"
          label="Live calls"
          value={stats?.live_calls}
          indicator={<LiveDot active={live > 0} />}
          hint={stats && (live > 0 ? "On the line now" : "No one on the line")}
        />
        <StatTile
          to="/calls"
          label="Calls · last 24h"
          value={stats?.calls_24h}
          hint={
            stats &&
            (stats.avg_call_duration_ms_24h
              ? `Avg ${formatDuration(stats.avg_call_duration_ms_24h)} · ${stats.calls_total} all time`
              : `${stats.calls_total} all time`)
          }
        />
        <StatTile
          to="/patients"
          label="Patients"
          value={stats?.patients_total}
          hint={stats && `${stats.patients_24h} new in the last 24h`}
        />
        <StatTile
          to="/patients?possible_duplicates=true"
          label="Possible duplicates"
          value={stats?.possible_duplicates}
          hint={stats && "Same name, DOB & phone · merge in person"}
        />
        <StatTile
          to={problems > 0 ? "/logs?last=24h&level=WARNING" : "/logs?last=24h"}
          label="Errors · last 24h"
          value={stats?.errors_24h}
          tone={stats?.errors_24h ? "danger" : "neutral"}
          hint={stats && `${stats.warnings_24h} warning${stats.warnings_24h === 1 ? "" : "s"}`}
        />
      </div>
    </div>
  );
}
