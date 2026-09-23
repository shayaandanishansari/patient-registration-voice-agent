import { Button } from "@/components/Button";
import { Empty, ErrorMessage, Loading } from "@/components/QueryState";

import { useCalls } from "../api/queries";
import { CallTable } from "./CallTable";

/** Paginated call table; pass patientId to show only that patient's calls. */
export function CallList({ patientId }: { patientId?: string }) {
  const query = useCalls(patientId);
  const calls = query.data?.pages.flatMap((page) => page.items) ?? [];

  if (query.isPending) return <Loading />;
  if (query.isError) return <ErrorMessage error={query.error} />;
  if (calls.length === 0) return <Empty>No calls yet.</Empty>;

  return (
    <>
      <CallTable calls={calls} />
      {query.hasNextPage && (
        <div className="mt-4 flex justify-center">
          <Button
            variant="secondary"
            onClick={() => query.fetchNextPage()}
            disabled={query.isFetchingNextPage}
          >
            {query.isFetchingNextPage ? "Loading…" : "Load more"}
          </Button>
        </div>
      )}
    </>
  );
}
