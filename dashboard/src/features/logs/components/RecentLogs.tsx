import { useNavigate } from "react-router";

import { Empty, ErrorMessage, Loading } from "@/components/QueryState";

import { useRecentLogs } from "../api/queries";
import { LogRow } from "./LogRow";

/** The newest log records, expandable like on the Logs page. */
export function RecentLogs({ limit = 8 }: { limit?: number }) {
  const query = useRecentLogs(limit);
  const navigate = useNavigate();

  if (query.isPending) return <Loading />;
  if (query.isError) return <ErrorMessage error={query.error} />;
  if (query.data.items.length === 0) return <Empty>No log records yet.</Empty>;

  return (
    <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
      {query.data.items.map((entry) => (
        <LogRow
          key={entry.id}
          entry={entry}
          onShowRequest={(requestId) =>
            navigate(`/logs?last=24h&request_id=${encodeURIComponent(requestId)}`)
          }
        />
      ))}
    </ul>
  );
}
