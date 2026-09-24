import type { Call } from "./types";

export interface CallCost {
  totalCents: number;
  parts: { label: string; cents: number }[];
}

const PRODUCT_LABELS: Record<string, string> = {
  retell_voice_engine: "Voice engine",
  platform_tts: "Text to speech",
  us_twilio_telephony: "Telephony",
};

function productLabel(product: string): string {
  if (PRODUCT_LABELS[product]) return PRODUCT_LABELS[product];
  if (product.startsWith("claude_")) return "LLM";
  // The conversation runs on Claude; a GPT line is the post-call analysis
  // model (the summary), charged once per call.
  if (product.startsWith("gpt_")) return "Post-call analysis";
  return product.replaceAll("_", " ");
}

/**
 * Retell's call_cost (cents), or null before it arrives with the
 * call_analyzed webhook. Unknown products keep their Retell name.
 */
export function callCost(call: Call): CallCost | null {
  const raw = call.call_cost as
    | { combined_cost?: unknown; product_costs?: { product?: unknown; cost?: unknown }[] }
    | null
    | undefined;
  if (typeof raw?.combined_cost !== "number") return null;
  const parts = (raw.product_costs ?? [])
    .filter((p) => typeof p.product === "string" && typeof p.cost === "number")
    .map((p) => ({ label: productLabel(p.product as string), cents: p.cost as number }))
    .sort((a, b) => b.cents - a.cents);
  return { totalCents: raw.combined_cost, parts };
}
