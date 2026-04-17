// lab5/src/lib/tools.ts
/**
 * Tool definitions and executors for the Week 7 agent loop.
 *
 * Two responsibilities:
 *   1. Tool schemas — what Claude sees when deciding which tool to call.
 *      Same logical tools as the MCP server, defined inline for the SDK.
 *   2. Tool executors — HTTP calls to the Python Cloud Run backend.
 *      The backend owns the implementation; this layer owns the transport.
 *
 * Architecture note (Alex):
 *   Claude Desktop path: Claude Desktop → MCP → mcp_server.py → tool fn
 *   Next.js agent path:  agent.ts → Claude API → tools.ts → Python HTTP
 *   Same tool implementations, different transport layer. This is correct.
 */

import { Tool } from "@anthropic-ai/sdk/resources/messages";

// ---------------------------------------------------------------------------
// Backend URL — Python Cloud Run in production, localhost in dev
// ---------------------------------------------------------------------------
const BACKEND_URL = process.env.PYTHON_BACKEND_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Tool schemas — Claude reads these to decide which tool to call.
// Descriptions must be specific enough to trigger without explicit instruction.
// ---------------------------------------------------------------------------
export const AGENT_TOOLS: Tool[] = [
  {
    name: "search_documents",
    description: [
      "Search the company knowledge base using semantic similarity.",
      "The knowledge base contains company documents including refund policies,",
      "terms of service, shipping information, and customer support documentation.",
      "Use this tool when the user asks any question that could be answered by",
      "company documentation. Do NOT use for weather or reminder requests.",
    ].join(" "),
    input_schema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "The search query — a natural language question or keyword phrase",
        },
      },
      required: ["query"],
    },
  },
  {
    name: "get_current_weather",
    description: [
      "Get the current weather conditions for a city or region.",
      "Use this tool when the user asks about weather, temperature, or conditions",
      "in a specific location. Do NOT use for document retrieval or reminders.",
    ].join(" "),
    input_schema: {
      type: "object",
      properties: {
        location: {
          type: "string",
          description: "City name or region, e.g. 'Denver, CO' or 'London'",
        },
      },
      required: ["location"],
    },
  },
  {
    name: "save_reminder",
    description: [
      "Save a reminder with a description and time for the user.",
      "Use this tool when the user asks to be reminded of something at a specific time.",
      "Do NOT use for document retrieval or weather queries.",
    ].join(" "),
    input_schema: {
      type: "object",
      properties: {
        text: {
          type: "string",
          description: "What to remind the user about",
        },
        time: {
          type: "string",
          description: "When to remind the user — natural language or ISO 8601",
        },
      },
      required: ["text", "time"],
    },
  },
];

// ---------------------------------------------------------------------------
// Tool result type — matches what the Python backend returns
// ---------------------------------------------------------------------------
export interface ToolResult {
  error: boolean;
  message?: string;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Tool executors — HTTP calls to Python backend
// Each function maps 1:1 to a tool schema above.
// Never raises — always returns a ToolResult (error or success).
// Morgan: same never-raises contract as the Python tool implementations.
// ---------------------------------------------------------------------------

async function callSearchDocuments(query: string): Promise<ToolResult> {
  try {
    const res = await fetch(`${BACKEND_URL}/tools/search_docs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
      signal: AbortSignal.timeout(10_000), // 10s timeout
    });
    if (!res.ok) {
      return { error: true, message: `Backend returned ${res.status}` };
    }
    return await res.json();
  } catch (err) {
    return {
      error: true,
      message: err instanceof Error ? err.message : "search_documents failed",
    };
  }
}

async function callGetWeather(location: string): Promise<ToolResult> {
  try {
    const res = await fetch(`${BACKEND_URL}/tools/get_weather`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ location }),
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) {
      return { error: true, message: `Backend returned ${res.status}` };
    }
    return await res.json();
  } catch (err) {
    return {
      error: true,
      message: err instanceof Error ? err.message : "get_weather failed",
    };
  }
}

async function callSaveReminder(
  text: string,
  time: string
): Promise<ToolResult> {
  try {
    const res = await fetch(`${BACKEND_URL}/tools/create_reminder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, time }),
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) {
      return { error: true, message: `Backend returned ${res.status}` };
    }
    return await res.json();
  } catch (err) {
    return {
      error: true,
      message: err instanceof Error ? err.message : "save_reminder failed",
    };
  }
}

// ---------------------------------------------------------------------------
// Dispatch — routes tool name to executor.
// Called by the agent loop with the name + input Claude generated.
// Returns a ToolResult always — never throws.
// ---------------------------------------------------------------------------
export async function executeTool(
  name: string,
  input: Record<string, unknown>
): Promise<ToolResult> {
  switch (name) {
    case "search_documents":
      return callSearchDocuments(input.query as string);
    case "get_current_weather":
      return callGetWeather(input.location as string);
    case "save_reminder":
      return callSaveReminder(input.text as string, input.time as string);
    default:
      // Allowlist — unknown tool names rejected, never executed
      return {
        error: true,
        message: `Unknown tool: ${name}. Valid tools: search_documents, get_current_weather, save_reminder`,
      };
  }
}