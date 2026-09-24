import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { LogEntry } from "../types";
import { LogRow } from "./LogRow";

const toolCall: LogEntry = {
  id: "1",
  ts: "2026-09-24T15:00:00+00:00",
  level: "INFO",
  logger: "app.routers.retell_tools",
  event: "retell_tool",
  request_id: "req-1",
  func: "logged_handler",
  line: 40,
  fields: {
    tool: "verify_patient",
    call_id: "call-1",
    args: { member_id: "12345678" },
    response: { verification_result: "verified" },
  },
};

describe("LogRow", () => {
  it("summarizes a tool call and expands to show what Retell sent", async () => {
    const onShowRequest = vi.fn();
    render(<LogRow entry={toolCall} onShowRequest={onShowRequest} />);

    expect(screen.getByText("verify_patient → verified · call-1")).toBeInTheDocument();
    expect(screen.queryByText(/12345678/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { expanded: false }));
    expect(screen.getByText(/"member_id": "12345678"/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "req-1" }));
    expect(onShowRequest).toHaveBeenCalledWith("req-1");
  });

  it("shows plain log messages and scalar fields", () => {
    render(
      <LogRow
        entry={{ ...toolCall, event: "patient_deleted", fields: { patient_id: "p-1" } }}
        onShowRequest={() => {}}
      />,
    );
    expect(screen.getByText("patient_id=p-1")).toBeInTheDocument();
  });
});
