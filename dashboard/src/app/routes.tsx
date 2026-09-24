// Route-level pages. Composing features lives here (not inside a feature),
// so e.g. features/patients never imports from features/calls.
import { Link, useParams } from "react-router";

import { Card } from "@/components/Card";
import { ErrorMessage, Loading } from "@/components/QueryState";
import { CallDetail, CallList, RecentCalls, useCall } from "@/features/calls";
import { RecentLogs } from "@/features/logs";
import { PatientProfile, RecentPatients, usePatient } from "@/features/patients";
import { StatTiles } from "@/features/stats";

function ViewAll({ to }: { to: string }) {
  return (
    <Link to={to} className="text-xs font-medium text-brand-700 hover:underline">
      View all →
    </Link>
  );
}

export function HomeRoute() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Overview</h1>
        <p className="text-sm text-slate-500">What the voice agent is doing, at a glance.</p>
      </div>
      <StatTiles />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Recent calls" actions={<ViewAll to="/calls" />}>
          <RecentCalls />
        </Card>
        <Card title="New patients" actions={<ViewAll to="/patients" />}>
          <RecentPatients />
        </Card>
      </div>
      <Card title="Recent activity" actions={<ViewAll to="/logs?hide_http=true" />}>
        <RecentLogs />
      </Card>
    </div>
  );
}

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
          <Card title="Calls">
            <CallList patientId={patientId} />
          </Card>
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
