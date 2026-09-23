import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "./api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      // Don't hammer the API on auth or not-found errors; they won't fix themselves.
      retry: (failureCount, error) =>
        !(error instanceof ApiError && [401, 404].includes(error.status)) && failureCount < 2,
    },
  },
});
