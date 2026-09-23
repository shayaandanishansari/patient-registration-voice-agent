import { Link } from "react-router";

import { Badge } from "@/components/Badge";
import { formatDateTime, formatDob, formatPhone } from "@/lib/format";

import type { Patient } from "../types";

export function PatientTable({ patients }: { patients: Patient[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="py-2 pr-4 font-medium">Name</th>
            <th className="py-2 pr-4 font-medium">Member ID</th>
            <th className="py-2 pr-4 font-medium">Date of birth</th>
            <th className="py-2 pr-4 font-medium">Phone</th>
            <th className="py-2 pr-4 font-medium">City</th>
            <th className="py-2 pr-4 font-medium">Source</th>
            <th className="py-2 font-medium">Registered</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {patients.map((p) => (
            <tr key={p.patient_id} className="hover:bg-slate-50">
              <td className="py-2.5 pr-4">
                <Link
                  to={`/patients/${p.patient_id}`}
                  className="font-medium text-brand-700 hover:underline"
                >
                  {p.last_name}, {p.first_name}
                </Link>
                {p.deleted_at && (
                  <span className="ml-2">
                    <Badge tone="danger">Deleted</Badge>
                  </span>
                )}
              </td>
              <td className="py-2.5 pr-4 font-mono text-xs">{p.member_id}</td>
              <td className="py-2.5 pr-4">{formatDob(p.date_of_birth)}</td>
              <td className="py-2.5 pr-4 whitespace-nowrap">{formatPhone(p.phone_number)}</td>
              <td className="py-2.5 pr-4">
                {p.city}, {p.state}
              </td>
              <td className="py-2.5 pr-4">
                <Badge tone={p.created_via === "voice" ? "brand" : "neutral"}>
                  {p.created_via ?? "unknown"}
                </Badge>
              </td>
              <td className="py-2.5 whitespace-nowrap text-slate-500">
                {formatDateTime(p.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
