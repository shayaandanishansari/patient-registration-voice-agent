import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router";

import { PatientsPage } from "@/features/patients";
import { clearApiKey, ENV_API_KEY, getApiKey, setApiKey } from "@/lib/apiKey";
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
        { path: "*", element: <Navigate to="/patients" replace /> },
      ],
    },
  ]);
}

export function App() {
  const [signedIn, setSignedIn] = useState(() => Boolean(getApiKey()));
  const [router] = useState(() =>
    // With a key from .env.local there's nothing to sign out of.
    createRouter(
      ENV_API_KEY
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
