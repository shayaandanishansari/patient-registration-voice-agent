import { useState, type FormEvent } from "react";

import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { Select } from "@/components/Select";

import { PRESETS, sameRange, UNITS, type TimeRange, type Unit } from "../timeRange";

const chipClass = (active: boolean) =>
  `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
    active ? "bg-white text-brand-700 shadow-sm ring-1 ring-slate-200" : "text-slate-600 hover:text-slate-900"
  }`;

export function TimeRangePicker({
  value,
  onChange,
}: {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}) {
  const isPreset = PRESETS.some((p) => sameRange(value, { kind: "last", ...p }));
  const [customOpen, setCustomOpen] = useState(!isPreset);
  const [amount, setAmount] = useState(value.kind === "last" ? String(value.amount) : "2");
  const [unit, setUnit] = useState<Unit>(value.kind === "last" ? value.unit : "d");
  const [from, setFrom] = useState(value.kind === "between" ? (value.from ?? "") : "");
  const [to, setTo] = useState(value.kind === "between" ? (value.to ?? "") : "");

  function applyLast(event: FormEvent) {
    event.preventDefault();
    const n = Number(amount);
    if (Number.isInteger(n) && n > 0) onChange({ kind: "last", amount: n, unit });
  }

  function applyBetween(event: FormEvent) {
    event.preventDefault();
    if (from || to) onChange({ kind: "between", from: from || undefined, to: to || undefined });
  }

  return (
    <div className="space-y-4">
      <div className="inline-flex flex-wrap gap-1 rounded-lg bg-slate-100 p-1" role="group" aria-label="Time range">
        {PRESETS.map((preset) => {
          const range: TimeRange = { kind: "last", amount: preset.amount, unit: preset.unit };
          const active = !customOpen && sameRange(value, range);
          return (
            <button
              key={preset.label}
              type="button"
              aria-pressed={active}
              className={chipClass(active)}
              onClick={() => {
                setCustomOpen(false);
                onChange(range);
              }}
            >
              {preset.label}
            </button>
          );
        })}
        <button
          type="button"
          aria-pressed={customOpen}
          className={chipClass(customOpen)}
          onClick={() => setCustomOpen(!customOpen)}
        >
          Custom…
        </button>
      </div>

      {customOpen && (
        <div className="grid gap-4 rounded-lg border border-slate-200 bg-slate-50/60 p-4 lg:grid-cols-2">
          <form onSubmit={applyLast} className="flex flex-wrap items-end gap-2">
            <Input
              className="w-24"
              label="Last"
              type="number"
              min={1}
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
            <Select className="w-32" label="Unit" value={unit} onChange={(e) => setUnit(e.target.value as Unit)}>
              {Object.entries(UNITS).map(([key, name]) => (
                <option key={key} value={key}>
                  {name}s
                </option>
              ))}
            </Select>
            <Button type="submit" variant="secondary">
              Apply
            </Button>
          </form>

          <form onSubmit={applyBetween} className="flex flex-wrap items-end gap-2">
            <Input
              className="w-full sm:w-auto"
              label="From"
              type="datetime-local"
              value={from}
              max={to || undefined}
              onChange={(e) => setFrom(e.target.value)}
            />
            <Input
              className="w-full sm:w-auto"
              label="To (blank = now)"
              type="datetime-local"
              value={to}
              min={from || undefined}
              onChange={(e) => setTo(e.target.value)}
            />
            <Button type="submit" variant="secondary" disabled={!from && !to}>
              Apply
            </Button>
          </form>
        </div>
      )}
    </div>
  );
}
