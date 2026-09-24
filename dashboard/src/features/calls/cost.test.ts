import { describe, expect, it } from "vitest";

import { callCost } from "./cost";
import type { Call } from "./types";

const base: Call = { call_id: "c", verification_attempts: 0, patients_created: [] };

describe("callCost", () => {
  it("is null until Retell sends the cost", () => {
    expect(callCost(base)).toBeNull();
  });

  it("labels products and sorts the biggest first", () => {
    const cost = callCost({
      ...base,
      call_cost: {
        combined_cost: 10.28,
        product_costs: [
          { product: "platform_tts", cost: 0.83 },
          { product: "claude_5_sonnet", cost: 3.52 },
          { product: "retell_voice_engine", cost: 3.03 },
        ],
      },
    });
    expect(cost?.totalCents).toBe(10.28);
    expect(cost?.parts.map((p) => p.label)).toEqual(["LLM", "Voice engine", "Text to speech"]);
  });
});
