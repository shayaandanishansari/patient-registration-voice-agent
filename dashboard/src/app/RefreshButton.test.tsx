import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RefreshButton } from "./RefreshButton";

function Page({ load }: { load: () => Promise<string> }) {
  useQuery({ queryKey: ["page"], queryFn: load, staleTime: Infinity });
  return <RefreshButton />;
}

describe("RefreshButton", () => {
  it("refetches the page's data even when it isn't stale", async () => {
    const load = vi.fn().mockResolvedValue("data");
    render(
      <QueryClientProvider client={new QueryClient()}>
        <Page load={load} />
      </QueryClientProvider>,
    );
    await waitFor(() => expect(screen.getByRole("button", { name: "Refresh" })).toBeEnabled());
    expect(load).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
  });
});
