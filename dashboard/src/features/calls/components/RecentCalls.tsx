import { Link } from "react-router";

import { Badge } from "@/components/Badge";
import { Empty, ErrorMessage, Loading } from "@/components/QueryState";
import { formatAgo, formatDuration } from "@/lib/format";

import { useRecentCalls } from "../api/queries";
import type { Call } from "../types";
import { outcome } from "./CallTable";

// Web calls have no phone number. A call with no started_at never got its
// Retell webhook, so the ID is all there is to show.
function caller(call: Call): string {
  if (call.from_number) return call.from_number;
  return call.started_at ? "Web call" : call.call_id;
}

/** Compact list of the newest calls, live ones flagged. */
export function RecentCalls({ limit = 5 }: { limit?: number }) {
  const query = useRecentCalls(limit);

  if (query.isPending) return <Loading />;
  if (query.isError) return <ErrorMessage error={query.error} />;
  if (query.data.items.length === 0) return <Empty>No calls yet.</Empty>;

  return (
    <ul className="-my-2 divide-y divide-slate-100">
      {query.data.items.map((call) => (
        <li key={call.call_id}>
          <Link
            to={`/calls/${encodeURIComponent(call.call_id)}`}
            className="-mx-2 flex items-center justify-between gap-3 rounded-lg px-2 py-2.5 hover:bg-slate-50"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-slate-800">{caller(call)}</p>
              <p className="text-xs text-slate-500">
                {formatAgo(call.started_at)}
                {call.status !== "ongoing" && call.duration_ms ? ` · ${formatDuration(call.duration_ms)}` : ""}
              </p>
            </div>
            {call.status === "ongoing" ? <Badge tone="brand">Live</Badge> : outcome(call)}
          </Link>
        </li>
      ))}
    </ul>
  );
}
