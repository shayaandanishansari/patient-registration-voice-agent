import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "react-router";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Empty, ErrorMessage, Loading } from "@/components/QueryState";

import { useLogs } from "../api/queries";
import { describeRange, rangeFromParams, rangeToParams, resolveRange, type TimeRange } from "../timeRange";
import { LEVELS, type Level, type LogFilters } from "../types";
import { LogFiltersForm } from "./LogFiltersForm";
import { LogList } from "./LogList";
import { TimeRangePicker } from "./TimeRangePicker";

// Time range and filters live in the URL so a view can be bookmarked or shared.
function filtersFromParams(params: URLSearchParams): LogFilters {
  const level = params.get("level");
  return {
    level: LEVELS.includes(level as Level) ? (level as Level) : undefined,
    event: params.get("event") || undefined,
    hide_http: params.get("hide_http") === "true" || undefined,
    call_id: params.get("call_id") || undefined,
    request_id: params.get("request_id") || undefined,
  };
}

function toParams(range: TimeRange, filters: LogFilters): URLSearchParams {
  const entries = Object.entries(filters)
    .filter(([, v]) => v)
    .map(([k, v]) => [k, String(v)] as [string, string]);
  return new URLSearchParams([...rangeToParams(range), ...entries]);
}

export function LogsPage() {
  const [params, setParams] = useSearchParams();
  const range = rangeFromParams(params);
  const filters = filtersFromParams(params);

  // A relative range ("last 1h") is pinned to timestamps when it's chosen, so
  // every page of one listing covers the same window. Refresh re-pins it.
  const [refreshedAt, setRefreshedAt] = useState(() => Date.now());
  const rangeKey = new URLSearchParams(rangeToParams(range)).toString();
  const bounds = useMemo(
    () => resolveRange(rangeFromParams(new URLSearchParams(rangeKey)), new Date(refreshedAt)),
    [rangeKey, refreshedAt],
  );

  const query = useLogs(bounds, filters);
  const entries = query.data?.pages.flatMap((page) => page.items) ?? [];
  const { fetchNextPage } = query;
  const loadMore = useCallback(() => void fetchNextPage(), [fetchNextPage]);

  function apply(nextRange: TimeRange, nextFilters: LogFilters) {
    setRefreshedAt(Date.now());
    setParams(toParams(nextRange, nextFilters));
  }

  const count = `${entries.length}${query.hasNextPage ? "+" : ""} records`;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Logs</h1>
          <p className="text-sm text-slate-500">
            Everything Retell sent and everything the backend did, newest first. Kept for 90 days.
          </p>
        </div>
        <Button variant="secondary" onClick={() => setRefreshedAt(Date.now())} disabled={query.isFetching}>
          {query.isFetching && !query.isFetchingNextPage ? "Refreshing…" : "Refresh"}
        </Button>
      </div>

      <Card>
        <div className="space-y-5">
          <TimeRangePicker key={rangeKey} value={range} onChange={(next) => apply(next, filters)} />
          <div className="border-t border-slate-100 pt-5">
            <LogFiltersForm
              key={params.toString()}
              initial={filters}
              onApply={(next) => apply(range, next)}
            />
          </div>
        </div>
      </Card>

      <Card title={`${describeRange(range)}${query.isSuccess ? ` · ${count}` : ""}`}>
        {query.isPending ? (
          <Loading />
        ) : query.isError ? (
          <ErrorMessage error={query.error} />
        ) : entries.length === 0 ? (
          <Empty>No logs in this range. Try a wider time range or fewer filters.</Empty>
        ) : (
          <LogList
            entries={entries}
            hasMore={query.hasNextPage}
            loadingMore={query.isFetchingNextPage}
            onLoadMore={loadMore}
            onShowRequest={(requestId) => apply(range, { request_id: requestId })}
          />
        )}
      </Card>
    </div>
  );
}
