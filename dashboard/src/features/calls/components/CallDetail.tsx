import { Link } from "react-router";

import { Card } from "@/components/Card";
import { DescriptionList } from "@/components/DescriptionList";
import { dash, formatCents, formatDateTime, formatDuration } from "@/lib/format";

import { callCost } from "../cost";
import type { Call } from "../types";

// Retell transcripts are "Agent: ...\nUser: ..." lines; render them as a chat.
function TranscriptLines({ transcript }: { transcript: string }) {
  const lines = transcript.split("\n").filter((line) => line.trim());
  return (
    <ol className="space-y-2 text-sm">
      {lines.map((line, i) => {
        const [speaker, ...rest] = line.split(":");
        const isAgent = speaker.trim().toLowerCase() === "agent";
        return (
          <li key={i} className={`flex ${isAgent ? "" : "justify-end"}`}>
            <p
              className={`max-w-[80%] rounded-2xl px-3.5 py-2 ${
                isAgent ? "bg-slate-100 text-slate-800" : "bg-brand-600 text-white"
              }`}
            >
              {rest.length ? rest.join(":").trim() : line}
            </p>
          </li>
        );
      })}
    </ol>
  );
}

export function CallDetail({ call }: { call: Call }) {
  const summary = call.call_analysis?.["call_summary"];
  const patientLinks = [...(call.patients_created ?? []), call.verified_patient_id]
    .filter((id): id is string => Boolean(id))
    .filter((id, i, all) => all.indexOf(id) === i);
  const cost = callCost(call);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900">Call {formatDateTime(call.started_at)}</h1>

      <Card title="Details">
        <DescriptionList
          items={[
            ["From", dash(call.from_number)],
            ["To", dash(call.to_number)],
            ["Duration", formatDuration(call.duration_ms)],
            [
              "Cost",
              cost ? (
                <span>
                  {formatCents(cost.totalCents)}
                  <span className="text-slate-500">
                    {" · "}
                    {cost.parts.map((p) => `${p.label} ${formatCents(p.cents)}`).join(" · ")}
                  </span>
                </span>
              ) : (
                "—"
              ),
            ],
            ["Ended because", dash(call.disconnection_reason?.replaceAll("_", " "))],
            ["Verification attempts", String(call.verification_attempts ?? 0)],
            [
              "Patients",
              patientLinks.length ? (
                <span className="flex flex-wrap gap-2">
                  {patientLinks.map((id) => (
                    <Link key={id} to={`/patients/${id}`} className="text-brand-700 hover:underline">
                      View patient
                    </Link>
                  ))}
                </span>
              ) : (
                "—"
              ),
            ],
          ]}
        />
        {call.recording_url && (
          <audio controls src={call.recording_url} className="mt-5 w-full">
            <a href={call.recording_url}>Download recording</a>
          </audio>
        )}
      </Card>

      {typeof summary === "string" && (
        <Card title="Summary">
          <p className="text-sm leading-relaxed">{summary}</p>
        </Card>
      )}

      <Card title="Transcript">
        {call.transcript ? (
          <TranscriptLines transcript={call.transcript} />
        ) : (
          <p className="text-sm text-slate-500">No transcript yet — it arrives when the call ends.</p>
        )}
      </Card>
    </div>
  );
}
