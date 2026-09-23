import { useState, type FormEvent } from "react";

import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { API_BASE_URL } from "@/lib/api";

export function SignIn({ onSignIn }: { onSignIn: (key: string) => void }) {
  const [key, setKey] = useState("");
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check the key against the API before accepting it, so a typo shows up
  // here rather than as an error on every page.
  async function submit(event: FormEvent) {
    event.preventDefault();
    setChecking(true);
    setError(null);
    try {
      const response = await fetch(new URL("/patients?limit=1", API_BASE_URL), {
        headers: { "x-api-key": key.trim() },
      });
      if (response.status === 401) setError("That API key was rejected.");
      else if (response.status === 404)
        setError(`${API_BASE_URL} has no /patients endpoint. Is the latest backend deployed there?`);
      else if (!response.ok) setError(`The API answered ${response.status}. Try again shortly.`);
      else onSignIn(key.trim());
    } catch {
      setError("Couldn't reach the API.");
    } finally {
      setChecking(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <form
        onSubmit={submit}
        className="w-full max-w-sm space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div>
          <h1 className="text-lg font-semibold text-slate-900">CareCloud Registrations</h1>
          <p className="mt-1 text-sm text-slate-500">
            Enter the backend's <code>API_KEY</code> to view patient records.
          </p>
        </div>
        <Input
          label="API key"
          type="password"
          autoComplete="off"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          required
        />
        {error && (
          <p role="alert" className="text-sm text-rose-700">
            {error}
          </p>
        )}
        <Button type="submit" className="w-full" disabled={!key.trim() || checking}>
          {checking ? "Checking…" : "Sign in"}
        </Button>
      </form>
    </main>
  );
}
