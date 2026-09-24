import { Link } from "react-router";

import { Badge } from "@/components/Badge";
import { Empty, ErrorMessage, Loading } from "@/components/QueryState";
import { formatAgo, formatDob } from "@/lib/format";

import { useRecentPatients } from "../api/queries";

/** Compact list of the newest registrations. */
export function RecentPatients({ limit = 5 }: { limit?: number }) {
  const query = useRecentPatients(limit);

  if (query.isPending) return <Loading />;
  if (query.isError) return <ErrorMessage error={query.error} />;
  if (query.data.items.length === 0) return <Empty>No patients yet.</Empty>;

  return (
    <ul className="-my-2 divide-y divide-slate-100">
      {query.data.items.map((p) => (
        <li key={p.patient_id}>
          <Link
            to={`/patients/${p.patient_id}`}
            className="-mx-2 flex items-center justify-between gap-3 rounded-lg px-2 py-2.5 hover:bg-slate-50"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-slate-800">
                {p.last_name}, {p.first_name}
              </p>
              <p className="text-xs text-slate-500">
                DOB {formatDob(p.date_of_birth)} · {formatAgo(p.created_at)}
              </p>
            </div>
            <Badge tone={p.created_via === "voice" ? "brand" : "neutral"}>
              {p.created_via ?? "unknown"}
            </Badge>
          </Link>
        </li>
      ))}
    </ul>
  );
}
