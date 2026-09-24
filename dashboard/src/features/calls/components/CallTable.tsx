import { Link } from "react-router";

import { Badge } from "@/components/Badge";
import { dash, formatDateTime, formatDuration } from "@/lib/format";

import type { Call } from "../types";

export function outcome(call: Call) {
  if (call.patients_created?.length) return <Badge tone="brand">Registered</Badge>;
  if (call.verified_patient_id) return <Badge tone="brand">Verified</Badge>;
  if (call.verification_attempts) return <Badge tone="warning">Verification failed</Badge>;
  return <Badge>No record change</Badge>;
}

export function CallTable({ calls }: { calls: Call[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="py-2 pr-4 font-medium">Started</th>
            <th className="py-2 pr-4 font-medium">From</th>
            <th className="py-2 pr-4 font-medium">Duration</th>
            <th className="py-2 pr-4 font-medium">Outcome</th>
            <th className="py-2 font-medium">Ended because</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {calls.map((call) => (
            <tr key={call.call_id} className="hover:bg-slate-50">
              <td className="py-2.5 pr-4 whitespace-nowrap">
                <Link
                  to={`/calls/${encodeURIComponent(call.call_id)}`}
                  className="font-medium text-brand-700 hover:underline"
                >
                  {formatDateTime(call.started_at)}
                </Link>
              </td>
              <td className="py-2.5 pr-4 whitespace-nowrap">{dash(call.from_number)}</td>
              <td className="py-2.5 pr-4">{formatDuration(call.duration_ms)}</td>
              <td className="py-2.5 pr-4">{outcome(call)}</td>
              <td className="py-2.5 text-slate-500">
                {dash(call.disconnection_reason?.replaceAll("_", " "))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
