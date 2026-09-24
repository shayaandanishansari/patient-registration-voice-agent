// A read-only view of the Retell agent export (backend/assets/retell_agent_scripts/agent.json),
// the source of truth for the voice flow. Only the fields the Docs page shows are typed.
import agentJson from "../../../../backend/assets/retell_agent_scripts/agent.json";

interface Equation {
  left: string;
  operator: string;
  right: string;
}

interface Edge {
  id: string;
  destination_node_id?: string;
  transition_condition:
    | { type: "prompt"; prompt: string }
    | { type: "equation"; operator: string; equations: Equation[] };
}

export interface FlowNode {
  id: string;
  name: string;
  type: string;
  instruction?: { type: string; text: string };
  edges?: Edge[];
  else_edge?: Edge;
  tool_id?: string;
  tool_ids?: string[];
}

export interface FlowTool {
  tool_id: string;
  name: string;
  description: string;
  url: string;
  parameters?: { properties?: Record<string, { description?: string }>; required?: string[] };
  response_variables?: Record<string, string>;
}

interface AgentExport {
  agent_name: string;
  language: string | string[];
  conversationFlow: {
    global_prompt: string;
    start_node_id: string;
    model_choice?: { model?: string };
    nodes: FlowNode[];
    tools: FlowTool[];
  };
}

const agent = agentJson as unknown as AgentExport;
const flow = agent.conversationFlow;

export const AGENT = {
  name: agent.agent_name,
  model: flow.model_choice?.model,
  languages: ([] as string[]).concat(agent.language),
  globalPrompt: flow.global_prompt,
  startNodeId: flow.start_node_id,
  nodes: flow.nodes,
  tools: flow.tools,
};

const nodesById = new Map(flow.nodes.map((n) => [n.id, n]));
const toolsById = new Map(flow.tools.map((t) => [t.tool_id, t]));

export const nodeName = (id?: string) => (id ? (nodesById.get(id)?.name ?? id) : "—");
export const findTool = (id: string) => toolsById.get(id);

/** "create_status == created", or the prompt the model judges the transition by. */
export function describeCondition(edge: Edge): string {
  const c = edge.transition_condition;
  if (c.type === "prompt") return c.prompt;
  return c.equations
    .map((e) => `${e.left.replace(/[{}]/g, "")} ${e.operator} ${e.right}`)
    .join(` ${c.operator} `);
}

/** The path a tool calls on the backend, without the deployment's host. */
export function toolPath(tool: FlowTool): string {
  try {
    return new URL(tool.url).pathname;
  } catch {
    return tool.url;
  }
}
