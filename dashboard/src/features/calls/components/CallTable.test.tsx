import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import type { Call } from "../types";
import { CallTable } from "./CallTable";

const calls: Call[] = [
  {
    call_id: "call-1",
    started_at: "2026-09-24T15:00:00+00:00",
    transcript: "Agent: Hi, this is Sarah.\nUser: I'd like to register.",
    verification_attempts: 0,
  },
  { call_id: "call-2", started_at: "2026-09-24T16:00:00+00:00", verification_attempts: 0 },
];

describe("CallTable", () => {
  it("opens a call's transcript from its row and closes it again", async () => {
    render(
      <MemoryRouter>
        <CallTable calls={calls} />
      </MemoryRouter>,
    );

    const [withTranscript, without] = screen.getAllByRole("button", { name: "Transcript" });
    expect(without).toBeDisabled();

    await userEvent.click(withTranscript);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("I'd like to register.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Full call details" })).toHaveAttribute("href", "/calls/call-1");

    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
