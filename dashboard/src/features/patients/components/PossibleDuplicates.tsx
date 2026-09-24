import { Link } from "react-router";

import { Badge } from "@/components/Badge";
import { Card } from "@/components/Card";
import { ErrorMessage } from "@/components/QueryState";
import { formatDateTime } from "@/lib/format";

import { usePatientDuplicates } from "../api/queries";

/**
 * Other records with the same name, DOB and phone as this patient.
 *
 * The voice agent registers a returning caller who has no member ID as a new
 * patient and never says a record already exists: name, DOB and phone aren't
 * proof of identity, so saying so would confirm someone's record to an
 * unverified caller. Staff see the pair here and merge it in person with a
 * photo ID. Renders nothing when there are no duplicates.
 */
export function PossibleDuplicates({ patientId }: { patientId: string }) {
  const query = usePatientDuplicates(patientId);

  if (query.isError) return <ErrorMessage error={query.error} />;
  if (!query.data || query.data.length === 0) return null;

  return (
    <Card title="Possible duplicates">
      <p className="mb-4 text-sm text-slate-600">
        Same name, date of birth and phone number as this record. The phone line registers
        callers without a member ID as new patients and never tells them a record exists, so
        merge these in person after checking a photo ID.
      </p>
      <ul className="divide-y divide-slate-100 text-sm">
        {query.data.map((p) => (
          <li key={p.patient_id} className="flex flex-wrap items-center gap-3 py-2.5">
            <Link
              to={`/patients/${p.patient_id}`}
              className="font-medium text-brand-700 hover:underline"
            >
              {p.first_name} {p.last_name}
            </Link>
            <span className="font-mono text-xs text-slate-600">{p.member_id}</span>
            <Badge tone={p.created_via === "voice" ? "brand" : "neutral"}>
              {p.created_via ?? "unknown"}
            </Badge>
            <span className="text-slate-500">Created {formatDateTime(p.created_at)}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
