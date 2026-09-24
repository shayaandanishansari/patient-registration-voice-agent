import { useState, type FormEvent } from "react";

import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { Select } from "@/components/Select";

import { useLogEvents } from "../api/queries";
import { LEVELS, type Level, type LogFilters } from "../types";

/** Dropdowns and the checkbox apply at once; the ID boxes on Enter or Filter. */
export function LogFiltersForm({
  initial,
  onApply,
}: {
  initial: LogFilters;
  onApply: (filters: LogFilters) => void;
}) {
  const [draft, setDraft] = useState(initial);
  const events = useLogEvents();

  function update(next: LogFilters, applyNow: boolean) {
    setDraft(next);
    if (applyNow) onApply(next);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    onApply(draft);
  }

  return (
    <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
      <Select
        className="w-full sm:w-40"
        label="Level"
        value={draft.level ?? ""}
        onChange={(e) => update({ ...draft, level: (e.target.value || undefined) as Level | undefined }, true)}
      >
        <option value="">All levels</option>
        {LEVELS.slice(1, 4).map((level) => (
          <option key={level} value={level}>
            {level} and above
          </option>
        ))}
      </Select>
      <Select
        className="w-full sm:w-56"
        label="Event"
        value={draft.event ?? ""}
        onChange={(e) => update({ ...draft, event: e.target.value || undefined }, true)}
      >
        <option value="">All events</option>
        {(events.data ?? []).map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </Select>
      <Input
        className="w-full sm:w-56"
        label="Call ID"
        value={draft.call_id ?? ""}
        onChange={(e) => update({ ...draft, call_id: e.target.value || undefined }, false)}
        placeholder="call_…"
      />
      <Input
        className="w-full sm:w-56"
        label="Request ID"
        value={draft.request_id ?? ""}
        onChange={(e) => update({ ...draft, request_id: e.target.value || undefined }, false)}
      />
      <label className="flex items-center gap-2 pb-2 text-sm text-slate-600">
        <input
          type="checkbox"
          checked={draft.hide_http ?? false}
          onChange={(e) => update({ ...draft, hide_http: e.target.checked || undefined }, true)}
          className="size-4 rounded border-slate-300 accent-brand-600"
        />
        Hide HTTP requests
      </label>
      <div className="flex gap-2">
        <Button type="submit">Filter</Button>
        <Button variant="ghost" onClick={() => update({}, true)}>
          Clear
        </Button>
      </div>
    </form>
  );
}
