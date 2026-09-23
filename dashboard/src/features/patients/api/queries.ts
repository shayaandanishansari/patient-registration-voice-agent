import { keepPreviousData, useInfiniteQuery, useQuery } from "@tanstack/react-query";

import { getOne, getPage } from "@/lib/api";

import type { Patient, PatientFilters } from "../types";

const PAGE_SIZE = 25;

export function usePatients(filters: PatientFilters) {
  return useInfiniteQuery({
    queryKey: ["patients", filters],
    queryFn: ({ pageParam }) =>
      getPage<Patient>("/patients", { ...filters, limit: PAGE_SIZE, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    // Keep showing the current rows while a new filter loads.
    placeholderData: keepPreviousData,
  });
}

export function usePatient(patientId: string) {
  return useQuery({
    queryKey: ["patient", patientId],
    queryFn: () => getOne<Patient>(`/patients/${patientId}`),
  });
}
