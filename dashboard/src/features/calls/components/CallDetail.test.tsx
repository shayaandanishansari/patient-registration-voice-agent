import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import type { Call } from "../types";
import { CallDetail } from "./CallDetail";

const call: Call = {
  call_id: "call-1",
  started_at: "2026-09-24T15:00:00+00:00",
  duration_ms: 95_000,
  transcript: "Agent: Hi, this is Sarah.\nUser: I'd like to register.",
  call_analysis: { call_summary: "Caller registered as a new patient." },
  patients_created: ["p-1"],
  verification_attempts: 0,
};

describe("CallDetail", () => {
  it("renders the transcript as speaker turns, the summary, and a patient link", () => {
    render(
      <MemoryRouter>
        <CallDetail call={call} />
      </MemoryRouter>,
    );

    expect(screen.getByText("Hi, this is Sarah.")).toBeInTheDocument();
    expect(screen.getByText("I'd like to register.")).toBeInTheDocument();
    expect(screen.getByText("Caller registered as a new patient.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View patient" })).toHaveAttribute("href", "/patients/p-1");
  });
});
