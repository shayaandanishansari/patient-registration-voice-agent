// Route-level pages. Composing features lives here (not inside a feature),
// so e.g. features/patients never imports from features/calls.
import { Link, useParams } from "react-router";

import { Card } from "@/components/Card";
import { ErrorMessage, Loading } from "@/components/QueryState";
import { AppointmentList } from "@/features/appointments";
import { CallDetail, CallList, useCall } from "@/features/calls";
import { PatientProfile, usePatient } from "@/features/patients";

export function PatientRoute() {
  const { patientId = "" } = useParams();
  const query = usePatient(patientId);

  return (
    <div className="space-y-6">
      <Link to="/patients" className="text-sm text-slate-500 hover:text-slate-800">
        ← All patients
      </Link>
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorMessage error={query.error} />
      ) : (
        <>
          <PatientProfile patient={query.data} />
          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="Appointments">
              <AppointmentList patientId={patientId} />
            </Card>
            <Card title="Calls">
              <CallList patientId={patientId} />
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

export function CallsRoute() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Calls</h1>
        <p className="text-sm text-slate-500">Every call to the voice agent, newest first.</p>
      </div>
      <Card>
        <CallList />
      </Card>
    </div>
  );
}

export function CallRoute() {
  const { callId = "" } = useParams();
  const query = useCall(callId);

  return (
    <div className="space-y-6">
      <Link to="/calls" className="text-sm text-slate-500 hover:text-slate-800">
        ← All calls
      </Link>
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorMessage error={query.error} />
      ) : (
        <CallDetail call={query.data} />
      )}
    </div>
  );
}
