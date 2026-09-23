import { useSearchParams } from "react-router";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Empty, ErrorMessage, Loading } from "@/components/QueryState";

import { usePatients } from "../api/queries";
import type { PatientFilters } from "../types";
import { PatientFiltersForm } from "./PatientFiltersForm";
import { PatientTable } from "./PatientTable";

// Filters live in the URL so a search can be bookmarked or shared.
function filtersFromParams(params: URLSearchParams): PatientFilters {
  return {
    last_name: params.get("last_name") ?? undefined,
    date_of_birth: params.get("date_of_birth") ?? undefined,
    phone_number: params.get("phone_number") ?? undefined,
    include_deleted: params.get("include_deleted") === "true" || undefined,
  };
}

export function PatientsPage() {
  const [params, setParams] = useSearchParams();
  const filters = filtersFromParams(params);
  const query = usePatients(filters);
  const patients = query.data?.pages.flatMap((page) => page.items) ?? [];

  function applyFilters(next: PatientFilters) {
    const entries = Object.entries(next).filter(([, v]) => v !== undefined && v !== "" && v !== false);
    setParams(new URLSearchParams(entries.map(([k, v]) => [k, String(v)])));
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Patients</h1>
        <p className="text-sm text-slate-500">Registrations from the phone line and the API.</p>
      </div>

      <Card>
        <PatientFiltersForm key={params.toString()} initial={filters} onApply={applyFilters} />
      </Card>

      <Card title={query.isSuccess ? `${patients.length}${query.hasNextPage ? "+" : ""} patients` : "Patients"}>
        {query.isPending ? (
          <Loading />
        ) : query.isError ? (
          <ErrorMessage error={query.error} />
        ) : patients.length === 0 ? (
          <Empty>No patients match these filters.</Empty>
        ) : (
          <>
            <PatientTable patients={patients} />
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
        )}
      </Card>
    </div>
  );
}
