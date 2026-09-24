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

/** Other active records with the same name, DOB and phone. */
export function usePatientDuplicates(patientId: string) {
  return useQuery({
    queryKey: ["patient", patientId, "duplicates"],
    queryFn: () => getOne<Patient[]>(`/patients/${patientId}/duplicates`),
  });
}

/**
 * patient_ids that share name, DOB and phone with another active record, so
 * the table can mark them. The flag isn't stored (it's worked out on read),
 * so this reuses the list filter. Up to 100 IDs, far more than a demo has.
 */
export function useDuplicateIds() {
  return useQuery({
    queryKey: ["patients", "duplicate-ids"],
    queryFn: () => getPage<Patient>("/patients", { possible_duplicates: true, limit: 100 }),
    select: (page) => new Set(page.items.map((p) => p.patient_id)),
  });
}

/** The newest registrations (the homepage preview). */
export function useRecentPatients(limit: number) {
  return useQuery({
    queryKey: ["patients", "recent", limit],
    queryFn: () => getPage<Patient>("/patients", { limit }),
    refetchInterval: 15_000,
  });
}
