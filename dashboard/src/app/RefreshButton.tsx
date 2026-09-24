import { useIsFetching, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/Button";

/** Refetches whatever the current page is showing; the backend doesn't push updates. */
export function RefreshButton() {
  const queryClient = useQueryClient();
  const fetching = useIsFetching({ type: "active" }) > 0;

  return (
    <Button
      variant="secondary"
      onClick={() => queryClient.refetchQueries({ type: "active" })}
      disabled={fetching}
    >
      {fetching ? "Refreshing…" : "Refresh"}
    </Button>
  );
}
