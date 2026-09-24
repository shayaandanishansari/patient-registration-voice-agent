import { useInfiniteQuery, useQuery } from "@tanstack/react-query";

import { getOne, getPage } from "@/lib/api";

import type { Call } from "../types";

export function useCalls(patientId?: string) {
  return useInfiniteQuery({
    queryKey: ["calls", patientId ?? null],
    queryFn: ({ pageParam }) =>
      getPage<Call>("/calls", { patient_id: patientId, limit: 25, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
  });
}

export function useCall(callId: string) {
  return useQuery({
    queryKey: ["call", callId],
    queryFn: () => getOne<Call>(`/calls/${encodeURIComponent(callId)}`),
  });
}

/** The newest calls, refreshed in the background (the homepage preview). */
export function useRecentCalls(limit: number) {
  return useQuery({
    queryKey: ["calls", "recent", limit],
    queryFn: () => getPage<Call>("/calls", { limit }),
    refetchInterval: 15_000,
  });
}
