"use client";

/**
 * Agent UI — Week 7
 * Casey Romero: 7 states, each with distinct visual treatment.
 * The user should never see a blank screen during a multi-step agent task.
 *
 * States: planning → tool_call → tool_result → synthesizing → complete
 *         loop_limit (early termination)
 *         error (unexpected failure)
 */

import { useState } from "react";
import { AgentStep, AgentResult } from "@/lib/agent";

// ---------------------------------------------------------------------------
// Step renderer — maps AgentStepType to visual treatment
// ---------------------------------------------------------------------------
function StepCard({ step }: { step: AgentStep }) {
  switch (step.type) {
    case "planning":
      return (
        <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-50 border border-blue-200">
          <span className="text-blue-500 text-lg">🧠</span>
          <div>
            <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide">
              Planning
            </p>
            <p className="text-sm text-blue-900 mt-0.5">{step.text}</p>
          </div>
        </div>
      );

    case "tool_call":
      return (
        <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-50 border border-amber-200">
          <span className="text-amber-500 text-lg">🔧</span>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-amber-600 uppercase tracking-wide">
              Calling tool · loop {step.loopIndex}
            </p>
            <p className="text-sm font-mono font-bold text-amber-900 mt-0.5">
              {step.toolName}
            </p>
            <pre className="text-xs text-amber-700 mt-1 overflow-x-auto whitespace-pre-wrap break-all">
              {JSON.stringify(step.toolInput, null, 2)}
            </pre>
          </div>
        </div>
      );

    case "tool_result":
      const isError = step.toolResult?.error === true;
      return (
        <div
          className={`flex items-start gap-3 p-3 rounded-lg border ${
            isError
              ? "bg-red-50 border-red-200"
              : "bg-green-50 border-green-200"
          }`}
        >
          <span className="text-lg">{isError ? "❌" : "✅"}</span>
          <div className="flex-1 min-w-0">
            <p
              className={`text-xs font-semibold uppercase tracking-wide ${
                isError ? "text-red-600" : "text-green-600"
              }`}
            >
              {step.toolName} result · {step.durationMs}ms
            </p>
            {isError ? (
              <p className="text-sm text-red-800 mt-0.5">
                {step.toolResult?.message ?? "Tool failed"}
              </p>
            ) : (
              <pre className="text-xs text-green-800 mt-1 overflow-x-auto whitespace-pre-wrap break-all max-h-32">
                {JSON.stringify(step.toolResult, null, 2)}
              </pre>
            )}
          </div>
        </div>
      );

    case "synthesizing":
      return (
        <div className="flex items-start gap-3 p-3 rounded-lg bg-purple-50 border border-purple-200">
          <span className="text-purple-500 text-lg animate-pulse">✍️</span>
          <div>
            <p className="text-xs font-semibold text-purple-600 uppercase tracking-wide">
              Synthesizing · loop {step.loopIndex} of {step.maxLoops}
            </p>
            <p className="text-sm text-purple-800 mt-0.5">
              Writing response from gathered information…
            </p>
          </div>
        </div>
      );

    case "complete":
      return (
        <div className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 border border-gray-200">
          <span className="text-gray-500 text-lg">💬</span>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Complete · {step.durationMs}ms
            </p>
          </div>
        </div>
      );

    case "loop_limit":
      return (
        <div className="flex items-start gap-3 p-3 rounded-lg bg-orange-50 border border-orange-200">
          <span className="text-orange-500 text-lg">⚠️</span>
          <div>
            <p className="text-xs font-semibold text-orange-600 uppercase tracking-wide">
              Loop limit reached · {step.loopIndex} of {step.maxLoops} loops used
            </p>
            <p className="text-sm text-orange-800 mt-0.5">
              Task terminated early. Partial results shown below.
            </p>
          </div>
        </div>
      );

    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function AgentPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!query.trim() || loading) return;

    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const res = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim() }),
      });

      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.error ?? `HTTP ${res.status}`);
      }

      const data: AgentResult = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-10">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Research Agent</h1>
          <p className="text-sm text-gray-500 mt-1">
            Ask a question. The agent will plan, use tools, and synthesize a response.
          </p>
          <a href="/" className="text-xs text-blue-500 hover:underline mt-1 inline-block">Back to writing assistant</a>
        </div>

        {/* Input */}
        <div className="flex gap-2 mb-8">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            placeholder="What is the refund policy?"
            disabled={loading}
            className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-sm
                       focus:outline-none focus:ring-2 focus:ring-blue-500
                       disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            onClick={handleSubmit}
            disabled={loading || !query.trim()}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium
                       hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors"
          >
            {loading ? "Running…" : "Run"}
          </button>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
            <div className="w-3 h-3 rounded-full bg-blue-400 animate-pulse" />
            Agent is working…
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="p-4 rounded-lg bg-red-50 border border-red-200 mb-6">
            <p className="text-sm font-semibold text-red-700">Error</p>
            <p className="text-sm text-red-600 mt-1">{error}</p>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-6">

            {/* Loop stats */}
            <div className="flex gap-4 text-xs text-gray-500">
              <span>
                Loops: <strong>{result.loopsUsed}</strong> / {result.maxLoops}
              </span>
              <span>
                Steps: <strong>{result.steps.length}</strong>
              </span>
              {result.terminatedEarly && (
                <span className="text-orange-600 font-semibold">
                  ⚠ Terminated early
                </span>
              )}
            </div>

            {/* Step trace */}
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                Agent trace
              </p>
              <div className="space-y-2">
                {result.steps
                  .filter((s) => s.type !== "complete")
                  .map((step, i) => (
                    <StepCard key={i} step={step} />
                  ))}
              </div>
            </div>

            {/* Final response */}
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                Response
              </p>
              <div className="p-4 rounded-lg bg-white border border-gray-200 text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
                {result.finalResponse}
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
