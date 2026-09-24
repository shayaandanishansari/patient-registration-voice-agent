import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router";

import { LogsPage } from "@/features/logs";
import { PatientsPage } from "@/features/patients";
import { clearApiKey, COOKIE_AUTH, ENV_API_KEY, getApiKey, setApiKey } from "@/lib/apiKey";
import { queryClient } from "@/lib/queryClient";

import { Layout } from "./Layout";
import { CallRoute, CallsRoute, PatientRoute } from "./routes";
import { SignIn } from "./SignIn";

function createRouter(onSignOut?: () => void) {
  return createBrowserRouter([
    {
      element: <Layout onSignOut={onSignOut} />,
      children: [
        { index: true, element: <Navigate to="/patients" replace /> },
        { path: "patients", element: <PatientsPage /> },
        { path: "patients/:patientId", element: <PatientRoute /> },
        { path: "calls", element: <CallsRoute /> },
        { path: "calls/:callId", element: <CallRoute /> },
        { path: "logs", element: <LogsPage /> },
        { path: "*", element: <Navigate to="/patients" replace /> },
      ],
    },
    // "/dashboard/" in the build the backend serves, "/" standalone.
  ], { basename: import.meta.env.BASE_URL.replace(/\/$/, "") || "/" });
}

export function App() {
  const [signedIn, setSignedIn] = useState(() => COOKIE_AUTH || Boolean(getApiKey()));
  const [router] = useState(() =>
    // With a key from .env.local, or the backend's login (which the browser
    // keeps until it closes), there's nothing to sign out of.
    createRouter(
      COOKIE_AUTH || ENV_API_KEY
        ? undefined
        : () => {
            clearApiKey();
            queryClient.clear();
            setSignedIn(false);
          },
    ),
  );

  if (!signedIn) {
    return (
      <SignIn
        onSignIn={(key) => {
          setApiKey(key);
          setSignedIn(true);
        }}
      />
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
