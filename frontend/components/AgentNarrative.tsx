import React from "react";

interface AgentNarrativeProps {
  paragraphs: string[];
  narrativeSource?: "openai" | "bedrock" | "ollama" | "fallback";
}

function renderFormattedText(text: string): React.ReactNode[] {
  // Matches **bold** or `code`
  const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  const parts = text.split(regex);

  return parts.map((part, idx) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={idx} className="font-semibold text-[var(--text)]">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={idx}
          className="px-1.5 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--line)] font-mono text-[13px] text-[var(--text)]"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

export default function AgentNarrative({
  paragraphs,
  narrativeSource = "openai",
}: AgentNarrativeProps) {
  return (
    <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[14px] p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {/* Agent Eye Symbol */}
          <div className="w-6 h-6 rounded-full bg-[var(--ember-bg)] border border-[var(--ember-line)] flex items-center justify-center text-[var(--ember)]">
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-[var(--text)] font-display">
            Agent Root Cause Analysis
          </h3>
        </div>

        {/* Source Badge */}
        {narrativeSource === "fallback" ? (
          <span
            className="px-2 py-0.5 rounded-[5px] text-[10px] font-mono bg-[var(--surface-2)] text-[var(--text-3)] border border-[var(--line-soft)]"
            title="Deterministic arithmetic narrative (model bypassed or throttled)"
          >
            deterministic narrative
          </span>
        ) : narrativeSource === "bedrock" ? (
          <span
            className="px-2 py-0.5 rounded-[5px] text-[10px] font-mono bg-[var(--mint-bg)] text-[var(--mint)] border border-[var(--mint-line)]"
            title="Verified Anthropic Claude 3.7 Sonnet generation at temperature=0"
          >
            claude-3.7-sonnet · verified
          </span>
        ) : narrativeSource === "ollama" ? (
          <span
            className="px-2 py-0.5 rounded-[5px] text-[10px] font-mono bg-[var(--mint-bg)] text-[var(--mint)] border border-[var(--mint-line)]"
            title="Verified local Ollama generation at temperature=0"
          >
            llama3.2 · local
          </span>
        ) : (
          <span
            className="px-2 py-0.5 rounded-[5px] text-[10px] font-mono bg-[var(--mint-bg)] text-[var(--mint)] border border-[var(--mint-line)]"
            title="Verified OpenAI gpt-4o-mini generation at temperature=0"
          >
            gpt-4o-mini · verified
          </span>
        )}
      </div>

      <div className="space-y-4 text-[14.5px] leading-[1.68] text-[var(--text-2)] max-w-[68ch]">
        {paragraphs.map((para, i) => (
          <p key={i}>
            {renderFormattedText(para)}
          </p>
        ))}
      </div>
    </div>
  );
}
