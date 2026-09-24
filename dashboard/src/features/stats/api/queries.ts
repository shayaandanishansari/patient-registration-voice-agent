import { useQuery } from "@tanstack/react-query";

import { getOne } from "@/lib/api";

import type { Stats } from "../types";

export function useStats() {
  return useQuery({
    queryKey: ["stats"],
    queryFn: () => getOne<Stats>("/stats"),
    // Live calls should feel live. Paused while the tab is in the background.
    refetchInterval: 10_000,
  });
}
