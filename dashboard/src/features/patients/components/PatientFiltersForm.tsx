import { useState, type FormEvent } from "react";

import { Button } from "@/components/Button";
import { Input } from "@/components/Input";

import type { PatientFilters } from "../types";

export function PatientFiltersForm({
  initial,
  onApply,
}: {
  initial: PatientFilters;
  onApply: (filters: PatientFilters) => void;
}) {
  const [draft, setDraft] = useState(initial);

  function submit(event: FormEvent) {
    event.preventDefault();
    onApply(draft);
  }

  function reset() {
    setDraft({});
    onApply({});
  }

  return (
    <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
      <Input
        className="w-full sm:w-48"
        label="Last name"
        value={draft.last_name ?? ""}
        onChange={(e) => setDraft({ ...draft, last_name: e.target.value })}
        placeholder="Doe"
      />
      <Input
        className="w-full sm:w-48"
        label="Date of birth"
        value={draft.date_of_birth ?? ""}
        onChange={(e) => setDraft({ ...draft, date_of_birth: e.target.value })}
        placeholder="MM/DD/YYYY"
      />
      <Input
        className="w-full sm:w-48"
        label="Phone number"
        value={draft.phone_number ?? ""}
        onChange={(e) => setDraft({ ...draft, phone_number: e.target.value })}
        placeholder="(512) 555-0123"
      />
      <label className="flex items-center gap-2 pb-2 text-sm text-slate-600">
        <input
          type="checkbox"
          checked={draft.include_deleted ?? false}
          onChange={(e) => setDraft({ ...draft, include_deleted: e.target.checked })}
          className="size-4 rounded border-slate-300 accent-brand-600"
        />
        Include deleted
      </label>
      <label className="flex items-center gap-2 pb-2 text-sm text-slate-600">
        <input
          type="checkbox"
          checked={draft.possible_duplicates ?? false}
          onChange={(e) => setDraft({ ...draft, possible_duplicates: e.target.checked })}
          className="size-4 rounded border-slate-300 accent-brand-600"
        />
        Possible duplicates only
      </label>
      <div className="flex gap-2">
        <Button type="submit">Search</Button>
        <Button variant="ghost" onClick={reset}>
          Clear
        </Button>
      </div>
    </form>
  );
}
