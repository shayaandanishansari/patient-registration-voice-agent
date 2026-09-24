import { Fragment, useEffect, useRef } from "react";

import { Button } from "@/components/Button";

import type { LogEntry } from "../types";
import { LogRow } from "./LogRow";

function dayLabel(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    weekday: "long",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** Loads the next page when the bottom of the list scrolls into view. */
function useLoadOnScroll(enabled: boolean, load: () => void) {
  const sentinel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = sentinel.current;
    if (!enabled || !node || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => entries[0]?.isIntersecting && load(),
      { rootMargin: "400px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [enabled, load]);
  return sentinel;
}

export function LogList({
  entries,
  hasMore,
  loadingMore,
  onLoadMore,
  onShowRequest,
}: {
  entries: LogEntry[];
  hasMore: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
  onShowRequest: (requestId: string) => void;
}) {
  const sentinel = useLoadOnScroll(hasMore && !loadingMore, onLoadMore);

  return (
    <>
      <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
        {entries.map((entry, i) => {
          const day = dayLabel(entry.ts);
          const newDay = i === 0 || day !== dayLabel(entries[i - 1].ts);
          return (
            <Fragment key={entry.id}>
              {newDay && (
                <li className="sticky top-0 z-10 bg-slate-100/95 px-3 py-1.5 text-xs font-semibold text-slate-600 backdrop-blur">
                  {day}
                </li>
              )}
              <LogRow entry={entry} onShowRequest={onShowRequest} />
            </Fragment>
          );
        })}
      </ul>
      <div ref={sentinel} className="mt-4 flex justify-center">
        {hasMore ? (
          <Button variant="secondary" onClick={onLoadMore} disabled={loadingMore}>
            {loadingMore ? "Loading…" : "Load more"}
          </Button>
        ) : (
          <p className="text-xs text-slate-400">End of logs for this range.</p>
        )}
      </div>
    </>
  );
}
