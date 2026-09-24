import { useEffect } from "react";
import { Link } from "react-router";

import { Button } from "@/components/Button";
import { formatDateTime } from "@/lib/format";

import type { Call } from "../types";

// Retell transcripts are "Agent: ...\nUser: ..." lines; render them as a chat.
export function TranscriptLines({ transcript }: { transcript: string }) {
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

/** The transcript in a modal over the page; Escape or a click outside closes it. */
export function TranscriptDialog({ call, onClose }: { call: Call; onClose: () => void }) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="transcript-title"
        className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-xl bg-white shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-4 border-b border-slate-200 px-5 py-3">
          <div className="min-w-0">
            <h2 id="transcript-title" className="font-semibold text-slate-900">
              Transcript
            </h2>
            <p className="text-xs text-slate-500">
              {formatDateTime(call.started_at)} ·{" "}
              <Link
                to={`/calls/${encodeURIComponent(call.call_id)}`}
                className="text-brand-700 hover:underline"
              >
                Full call details
              </Link>
            </p>
          </div>
          <Button variant="ghost" onClick={onClose} autoFocus>
            Close
          </Button>
        </div>
        <div className="overflow-y-auto px-5 py-4">
          {call.transcript ? (
            <TranscriptLines transcript={call.transcript} />
          ) : (
            <p className="text-sm text-slate-500">No transcript yet — it arrives when the call ends.</p>
          )}
        </div>
      </div>
    </div>
  );
}
