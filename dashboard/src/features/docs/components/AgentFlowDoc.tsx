import { useMemo } from "react";

import { Badge } from "@/components/Badge";
import { Card } from "@/components/Card";

import { AGENT, describeCondition, findTool, nodeName, toolPath, type FlowNode } from "../agentFlow";
import { renderMarkdown } from "../markdown";

const NODE_TYPES: Record<string, string> = {
  conversation: "Conversation",
  function: "Tool call",
  subagent: "Subagent",
  end: "End call",
};

// Prompts are written in markdown (headings, bullet lists), so render them as such.
function Prompt({ text }: { text: string }) {
  const html = useMemo(() => renderMarkdown(text, "", { breaks: true }), [text]);
  return (
    <div
      className="prose prose-sm prose-slate max-w-none prose-headings:mb-1 prose-headings:mt-4 first:prose-headings:mt-0 prose-ul:my-1 prose-li:my-0"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function NodeCard({ node }: { node: FlowNode }) {
  const toolIds = node.tool_ids ?? (node.tool_id ? [node.tool_id] : []);
  const edges = [...(node.edges ?? []), ...(node.else_edge ? [node.else_edge] : [])];

  return (
    <section id={node.id} className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-5 py-3">
        <h3 className="text-sm font-semibold text-slate-800">{node.name}</h3>
        <Badge tone={node.type === "end" ? "neutral" : "brand"}>{NODE_TYPES[node.type] ?? node.type}</Badge>
        {node.id === AGENT.startNodeId && <Badge tone="warning">Start</Badge>}
        {toolIds.map((id) => (
          <code key={id} className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-700">
            {findTool(id)?.name ?? id}
          </code>
        ))}
      </header>
      <div className="space-y-4 p-5">
        {node.instruction?.text && <Prompt text={node.instruction.text} />}
        {edges.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Goes to</p>
            <ul className="mt-2 space-y-1.5 text-sm">
              {edges.map((edge) => (
                <li key={edge.id} className="flex flex-wrap gap-x-2">
                  <a href={`#${edge.destination_node_id}`} className="font-medium text-brand-700 hover:underline">
                    {nodeName(edge.destination_node_id)}
                  </a>
                  <span className="text-slate-500">
                    {edge === node.else_edge ? "otherwise" : `when ${describeCondition(edge)}`}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

/** The Retell agent export, laid out to read: global prompt, then each node, then the tools. */
export function AgentFlowDoc() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Voice agent prompts</h1>
        <p className="text-sm text-slate-500">
          Read from <code>backend/assets/retell_agent_scripts/agent.json</code>, the Retell export
          the live agent is imported from.
        </p>
      </div>

      <Card title="Agent">
        <dl className="grid gap-4 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-slate-500">Name</dt>
            <dd className="font-medium text-slate-900">{AGENT.name}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Model</dt>
            <dd className="font-medium text-slate-900">{AGENT.model ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Languages</dt>
            <dd className="font-medium text-slate-900">{AGENT.languages.join(", ")}</dd>
          </div>
        </dl>
      </Card>

      <Card title="Global prompt (applies to every node)">
        <Prompt text={AGENT.globalPrompt} />
      </Card>

      <div className="space-y-4">
        <h2 className="text-sm font-semibold text-slate-700">Nodes</h2>
        {AGENT.nodes.map((node) => (
          <NodeCard key={node.id} node={node} />
        ))}
      </div>

      <Card title="Tools (each one calls the backend)">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="pb-2 pr-4 font-medium">Tool</th>
                <th className="pb-2 pr-4 font-medium">Endpoint</th>
                <th className="pb-2 pr-4 font-medium">Arguments</th>
                <th className="pb-2 font-medium">Flow reads back</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 align-top">
              {AGENT.tools.map((tool) => {
                const required = new Set(tool.parameters?.required ?? []);
                return (
                  <tr key={tool.tool_id}>
                    <td className="py-3 pr-4">
                      <code className="font-medium text-slate-900">{tool.name}</code>
                      <p className="mt-1 text-slate-500">{tool.description}</p>
                    </td>
                    <td className="py-3 pr-4">
                      <code className="text-xs">POST {toolPath(tool)}</code>
                    </td>
                    <td className="py-3 pr-4 text-xs text-slate-600">
                      {Object.keys(tool.parameters?.properties ?? {}).map((arg) => (
                        <span key={arg} className="mr-2 inline-block">
                          <code>{arg}</code>
                          {required.has(arg) && <span className="text-rose-600">*</span>}
                        </span>
                      ))}
                    </td>
                    <td className="py-3 text-xs text-slate-600">
                      {Object.keys(tool.response_variables ?? {}).map((v) => (
                        <code key={v} className="mr-2 inline-block">
                          {v}
                        </code>
                      ))}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-slate-500">
            <span className="text-rose-600">*</span> required
          </p>
        </div>
      </Card>
    </div>
  );
}
