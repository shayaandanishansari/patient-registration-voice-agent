import { NavLink, Outlet } from "react-router";

import { Button } from "@/components/Button";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-1.5 text-sm font-medium ${
    isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
  }`;

export function Layout({ onSignOut }: { onSignOut?: () => void }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <span className="font-semibold text-slate-900">
              Hospital <span className="text-brand-600">Registrations</span>
            </span>
            <nav className="flex gap-1">
              <NavLink to="/" end className={navLinkClass}>
                Overview
              </NavLink>
              <NavLink to="/patients" className={navLinkClass}>
                Patients
              </NavLink>
              <NavLink to="/calls" className={navLinkClass}>
                Calls
              </NavLink>
              <NavLink to="/logs" className={navLinkClass}>
                Logs
              </NavLink>
            </nav>
          </div>
          {onSignOut && (
            <Button variant="ghost" onClick={onSignOut}>
              Sign out
            </Button>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
