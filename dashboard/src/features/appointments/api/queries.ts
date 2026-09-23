import { useQuery } from "@tanstack/react-query";

import { getPage } from "@/lib/api";

import type { Appointment } from "../types";

export function useAppointments(patientId: string) {
  return useQuery({
    queryKey: ["appointments", patientId],
    queryFn: async () =>
      (await getPage<Appointment>("/appointments", { patient_id: patientId, limit: 100 })).items,
  });
}
