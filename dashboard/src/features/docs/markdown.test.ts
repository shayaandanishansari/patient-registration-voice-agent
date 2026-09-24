import { describe, expect, it } from "vitest";

import { AGENT, describeCondition, nodeName } from "./agentFlow";
import { DOCS, findDoc } from "./catalog";
import { renderMarkdown, resolveLink } from "./markdown";

describe("catalog", () => {
  it("loads the documents that exist in docs/", () => {
    for (const slug of ["design-decisions", "identity", "architecture", "agent", "api-routes", "security"]) {
      expect(findDoc(slug), slug).toBeDefined();
    }
    expect(new Set(DOCS.map((d) => d.slug)).size).toBe(DOCS.length);
  });
});

describe("resolveLink", () => {
  it("opens another markdown doc inside the dashboard", () => {
    expect(resolveLink("security.md", "/dashboard")).toEqual({
      href: "/dashboard/docs/security",
      external: false,
    });
  });

  it("opens a file doc in a new tab", () => {
    const link = resolveLink("identity-voiceagent.html", "");
    expect(link.external).toBe(true);
    expect(link.href).toContain("identity-voiceagent");
  });

  it("sends any other repo path to GitHub, keeping the anchor", () => {
    expect(resolveLink("../backend/README.md#architecture-decisions", "")).toEqual({
      href: "https://github.com/shayaandanishansari/patient-registration-voice-agent/blob/main/backend/README.md#architecture-decisions",
      external: true,
    });
  });

  it("leaves in-page anchors and full URLs alone", () => {
    expect(resolveLink("#top", "")).toEqual({ href: "#top", external: false });
    expect(resolveLink("https://example.com", "").external).toBe(true);
  });
});

describe("renderMarkdown", () => {
  it("renders tables and rewrites links", () => {
    const html = renderMarkdown("| a |\n|---|\n| [x](api-routes.md) |", "/dashboard");
    expect(html).toContain("<table>");
    expect(html).toContain('href="/dashboard/docs/api-routes"');
  });
});

describe("agent flow", () => {
  it("reads the agent export", () => {
    expect(AGENT.globalPrompt.length).toBeGreaterThan(0);
    expect(nodeName(AGENT.startNodeId)).not.toBe(AGENT.startNodeId);
    expect(AGENT.tools.map((t) => t.name)).toContain("create_patient");
  });

  it("describes equation edges as readable conditions", () => {
    const save = AGENT.nodes.find((n) => n.id === "reg_create")!;
    expect(save.edges!.map(describeCondition)).toContain("create_status == created");
  });
});
