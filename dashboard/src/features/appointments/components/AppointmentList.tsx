import { Badge } from "@/components/Badge";
import { Empty, ErrorMessage, Loading } from "@/components/QueryState";

import { useAppointments } from "../api/queries";

export function AppointmentList({ patientId }: { patientId: string }) {
  const query = useAppointments(patientId);

  if (query.isPending) return <Loading />;
  if (query.isError) return <ErrorMessage error={query.error} />;
  if (query.data.length === 0) return <Empty>No appointments booked.</Empty>;

  return (
    <ul className="divide-y divide-slate-100">
      {query.data.map((appt) => (
        <li key={appt.appointment_id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm">
          <div>
            <p className="font-medium">{appt.spoken}</p>
            <p className="text-slate-500">
              {appt.visit_type} with {appt.provider}
            </p>
          </div>
          <Badge tone="brand">{appt.status}</Badge>
        </li>
      ))}
    </ul>
  );
}
