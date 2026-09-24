import type { components } from "@/types/api";

export type Patient = components["schemas"]["PatientOut"];
export type UpdateHistoryEntry = components["schemas"]["UpdateHistoryEntry"];

export type PatientFilters = {
  last_name?: string;
  date_of_birth?: string;
  phone_number?: string;
  include_deleted?: boolean;
  /** Only records that share name, DOB and phone with another record. */
  possible_duplicates?: boolean;
};
