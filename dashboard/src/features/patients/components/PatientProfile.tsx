import { Badge } from "@/components/Badge";
import { Card } from "@/components/Card";
import { DescriptionList } from "@/components/DescriptionList";
import { dash, formatDateTime, formatDob, formatPhone, optional } from "@/lib/format";

import type { Patient } from "../types";

export function PatientProfile({ patient: p }: { patient: Patient }) {
  const address = [p.address_line_1, p.address_line_2].filter(Boolean).join(", ");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold text-slate-900">
          {p.first_name} {p.last_name}
        </h1>
        <Badge tone="brand">Member ID {p.member_id}</Badge>
        {p.deleted_at && <Badge tone="danger">Deleted {formatDateTime(p.deleted_at)}</Badge>}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Demographics">
          <DescriptionList
            items={[
              ["Date of birth", formatDob(p.date_of_birth)],
              ["Sex", p.sex],
              ["Phone", formatPhone(p.phone_number)],
              ["Email", optional(p.email)],
              ["Preferred language", p.preferred_language ?? "English"],
              ["Address", `${address}, ${p.city}, ${p.state} ${p.zip_code}`],
            ]}
          />
        </Card>

        <Card title="Insurance & emergency contact">
          <DescriptionList
            items={[
              ["Insurance provider", optional(p.insurance_provider)],
              ["Insurance member ID", optional(p.insurance_member_id)],
              ["Emergency contact", optional(p.emergency_contact_name)],
              [
                "Emergency contact phone",
                p.emergency_contact_phone ? formatPhone(p.emergency_contact_phone) : "Not provided",
              ],
            ]}
          />
        </Card>
      </div>

      <Card title="Record history">
        <DescriptionList
          items={[
            ["Patient ID", <span className="font-mono text-xs">{p.patient_id}</span>],
            ["Created via", dash(p.created_via)],
            ["Created", formatDateTime(p.created_at)],
            ["Last updated", formatDateTime(p.updated_at)],
          ]}
        />
        {(p.update_history ?? []).length > 0 && (
          <ul className="mt-5 space-y-2 border-t border-slate-100 pt-4 text-sm">
            {[...(p.update_history ?? [])].reverse().map((entry, i) => (
              <li key={i} className="flex flex-wrap items-center gap-2">
                <span className="text-slate-500">{formatDateTime(entry.at)}</span>
                <Badge>{entry.source}</Badge>
                <span>changed {entry.fields_changed.join(", ").replaceAll("_", " ")}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
