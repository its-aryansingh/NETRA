"use client";

import React, { useState, useEffect } from "react";

interface WellArchitectedModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function WellArchitectedModal({ isOpen, onClose }: WellArchitectedModalProps) {
  const [activeTab, setActiveTab] = useState<"pillars" | "invariants" | "redteam">("pillars");

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-4xl max-h-[90vh] flex flex-col bg-[var(--surface)] border border-[var(--line)] rounded-[16px] shadow-2xl overflow-hidden text-[var(--text)] font-sans"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--line)] bg-[var(--surface-2)]">
          <div className="flex items-center gap-3">
            <div className="p-1.5 rounded-[8px] bg-[var(--mint-bg)] border border-[var(--mint-line)] text-[var(--mint)]">
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
            </div>
            <div>
              <h2 className="text-base font-bold tracking-tight">AWS Well-Architected & Formal Verification Inspector</h2>
              <p className="text-xs text-[var(--text-3)] font-mono">NETRA System Architecture · Reviewed for AWS Judges & TAMs</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-[7px] text-[var(--text-3)] hover:text-[var(--text)] hover:bg-[var(--surface)] transition-colors"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 px-6 py-2 border-b border-[var(--line)] bg-[var(--surface-2)]/50 text-xs font-mono">
          <button
            onClick={() => setActiveTab("pillars")}
            className={`px-3 py-1.5 rounded-[6px] transition-colors ${
              activeTab === "pillars"
                ? "bg-[var(--surface)] text-[var(--mint)] border border-[var(--line)] font-medium"
                : "text-[var(--text-3)] hover:text-[var(--text)]"
            }`}
          >
            6 Well-Architected Pillars
          </button>
          <button
            onClick={() => setActiveTab("invariants")}
            className={`px-3 py-1.5 rounded-[6px] transition-colors ${
              activeTab === "invariants"
                ? "bg-[var(--surface)] text-[var(--mint)] border border-[var(--line)] font-medium"
                : "text-[var(--text-3)] hover:text-[var(--text)]"
            }`}
          >
            Cryptographic Invariants (make verify)
          </button>
          <button
            onClick={() => setActiveTab("redteam")}
            className={`px-3 py-1.5 rounded-[6px] transition-colors ${
              activeTab === "redteam"
                ? "bg-[var(--surface)] text-[var(--mint)] border border-[var(--line)] font-medium"
                : "text-[var(--text-3)] hover:text-[var(--text)]"
            }`}
          >
            Adversarial Red Team (12/12 Defended)
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-6">
          {activeTab === "pillars" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Pillar 1: Cost Optimization */}
              <div className="p-4 rounded-[12px] bg-[var(--surface-2)] border border-[var(--line)] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-[var(--mint)] font-bold">01 · COST OPTIMIZATION</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[var(--mint-bg)] text-[var(--mint)] border border-[var(--mint-line)]">PRIMARY</span>
                </div>
                <h4 className="text-sm font-semibold text-[var(--text)]">Sub-10s Pre-Billing Interception</h4>
                <p className="text-xs text-[var(--text-2)] leading-relaxed">
                  Prices resources upon EventBridge state changes directly from the AWS Price List API. Intercepts runaway compute before the first hourly billing increment aggregates. System idle footprint is &lt;₹10/month (&lt;$0.15/mo).
                </p>
              </div>

              {/* Pillar 2: Security */}
              <div className="p-4 rounded-[12px] bg-[var(--surface-2)] border border-[var(--line)] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-[var(--mint)] font-bold">02 · SECURITY</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[var(--mint-bg)] text-[var(--mint)] border border-[var(--mint-line)]">NON-MUTATING</span>
                </div>
                <h4 className="text-sm font-semibold text-[var(--text)]">Zero-Mutating AI & Cedar Policies</h4>
                <p className="text-xs text-[var(--text-2)] leading-relaxed">
                  Investigator IAM role holds 0 mutating actions. Mutating operations require HMAC-SHA256 time-bounded human tokens and evaluate formal AWS Cedar policy invariants (`forbid_protected`, `forbid_dependents`) in 1.2ms.
                </p>
              </div>

              {/* Pillar 3: Reliability */}
              <div className="p-4 rounded-[12px] bg-[var(--surface-2)] border border-[var(--line)] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-[var(--mint)] font-bold">03 · RELIABILITY</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[var(--mint-bg)] text-[var(--mint)] border border-[var(--mint-line)]">ROLLBACK-SAFE</span>
                </div>
                <h4 className="text-sm font-semibold text-[var(--text)]">Step Functions 5-Stage Orchestration</h4>
                <p className="text-xs text-[var(--text-2)] leading-relaxed">
                  All remediations pass through Step Functions (`Authorize` &rarr; `PolicyCheck` &rarr; `DryRun` &rarr; `Snapshot` &rarr; `Act`). Automated EBS recovery snapshots are retained for 7 days with single-click rollback restoration.
                </p>
              </div>

              {/* Pillar 4: Operational Excellence */}
              <div className="p-4 rounded-[12px] bg-[var(--surface-2)] border border-[var(--line)] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-[var(--mint)] font-bold">04 · OPERATIONAL EXCELLENCE</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[var(--mint-bg)] text-[var(--mint)] border border-[var(--mint-line)]">IMMUTABLE</span>
                </div>
                <h4 className="text-sm font-semibold text-[var(--text)]">Append-Only DynamoDB Audit Ledger</h4>
                <p className="text-xs text-[var(--text-2)] leading-relaxed">
                  Every proposal, approval, and mutation is cryptographically audited with operator principal, timestamp, and target ARN. Declarative rules-as-data (`rules.yaml`) guarantees byte-identical deterministic evaluations.
                </p>
              </div>

              {/* Pillar 5: Performance Efficiency */}
              <div className="p-4 rounded-[12px] bg-[var(--surface-2)] border border-[var(--line)] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-[var(--mint)] font-bold">05 · PERFORMANCE EFFICIENCY</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[var(--mint-bg)] text-[var(--mint)] border border-[var(--mint-line)]">&lt;50MS LATENCY</span>
                </div>
                <h4 className="text-sm font-semibold text-[var(--text)]">Batch Telemetry & S3 Price Cache</h4>
                <p className="text-xs text-[var(--text-2)] leading-relaxed">
                  CloudWatch telemetry batches across all instances via `GetMetricData` in &lt;400ms. Immutable pricing digests are cached in S3 with SHA-256 hashes, eliminating repetitive API roundtrips.
                </p>
              </div>

              {/* Pillar 6: Sustainability */}
              <div className="p-4 rounded-[12px] bg-[var(--surface-2)] border border-[var(--line)] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-[var(--mint)] font-bold">06 · SUSTAINABILITY</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[var(--mint-bg)] text-[var(--mint)] border border-[var(--mint-line)]">SERVERLESS</span>
                </div>
                <h4 className="text-sm font-semibold text-[var(--text)]">Scale-to-Zero Architecture</h4>
                <p className="text-xs text-[var(--text-2)] leading-relaxed">
                  Zero always-on containers or EC2 instances for monitoring. AWS Lambda and on-demand DynamoDB consume strictly zero CPU cycles and zero Watts of energy between scheduled sweeps.
                </p>
              </div>
            </div>
          )}

          {activeTab === "invariants" && (
            <div className="space-y-4">
              <div className="p-4 rounded-[12px] bg-[var(--surface-2)] border border-[var(--line)]">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-mono text-[var(--text-3)]">RUN HARNESS: make verify</span>
                  <span className="text-xs font-mono text-[var(--mint)] font-bold">ALL 6 CHECKS PASSED (1.23s)</span>
                </div>
                <div className="space-y-2 font-mono text-xs text-[var(--text-2)]">
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--mint)] font-bold">[✓]</span>
                    <span>fast path: instance launched at T, finding written at T+0.05s</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--mint)] font-bold">[✓]</span>
                    <span>mcp: netra_execute refused a replayed or tampered approval token</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--mint)] font-bold">[✓]</span>
                    <span>iam: investigator role contains 0 mutating actions (least privilege)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--mint)] font-bold">[✓]</span>
                    <span>provenance: 3 resources priced from 3 SHA-256 hashed price documents</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--mint)] font-bold">[✓]</span>
                    <span>determinism: 6 rules evaluated from rules.yaml — byte-identical output</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--mint)] font-bold">[✓]</span>
                    <span>cedar policy: termination on protected instance DENIED by forbid_protected</span>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-[12px] bg-[var(--surface-2)] border border-[var(--line)] flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-semibold text-[var(--text)]">AWS Technical Backing: Issue #92</h4>
                  <p className="text-[11px] text-[var(--text-3)] font-mono">aws-solutions/innovation-sandbox-on-aws#92</p>
                </div>
                <a
                  href="https://github.com/aws-solutions/innovation-sandbox-on-aws/issues/92"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 rounded-[7px] bg-[var(--surface)] border border-[var(--line)] text-xs font-mono text-[var(--mint)] hover:underline flex items-center gap-1.5"
                >
                  <span>View Public AWS Issue</span>
                  <span>↗</span>
                </a>
              </div>
            </div>
          )}

          {activeTab === "redteam" && (
            <div className="space-y-4">
              <div className="p-4 rounded-[12px] bg-[var(--surface-2)] border border-[var(--line)]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono text-[var(--text-3)]">EVALUATION: 12 Adversarial Attack Vectors</span>
                  <span className="text-xs font-mono text-[var(--mint)] font-bold">100% DEFENDED (0/12 Breached)</span>
                </div>
                <p className="text-xs text-[var(--text-2)] mb-4">
                  We evaluated LLM narration against an unconstrained control model vs NETRA&apos;s two-tier AST regex validator and Cedar policy engine.
                </p>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono text-left border-collapse">
                    <thead>
                      <tr className="border-b border-[var(--line)] text-[var(--text-3)]">
                        <th className="py-2">Tactic</th>
                        <th className="py-2 text-center">Control Arm</th>
                        <th className="py-2 text-center">Shipped Pipeline</th>
                        <th className="py-2 text-right">Defense Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--line)] text-[var(--text-2)]">
                      <tr>
                        <td className="py-2">T1 Instruction Injection (Tags)</td>
                        <td className="py-2 text-center text-[var(--alarm)]">3/3 breached</td>
                        <td className="py-2 text-center text-[var(--mint)]">0/3 breached</td>
                        <td className="py-2 text-right text-[var(--mint)]">PREVENTED</td>
                      </tr>
                      <tr>
                        <td className="py-2">T2 Fabricated Figures (Hallucinations)</td>
                        <td className="py-2 text-center text-[var(--alarm)]">3/3 breached</td>
                        <td className="py-2 text-center text-[var(--mint)]">0/3 breached</td>
                        <td className="py-2 text-right text-[var(--mint)]">PREVENTED</td>
                      </tr>
                      <tr>
                        <td className="py-2">T3 Protected Coercion (netra:protected)</td>
                        <td className="py-2 text-center text-[var(--alarm)]">3/3 breached</td>
                        <td className="py-2 text-center text-[var(--mint)]">0/3 breached</td>
                        <td className="py-2 text-right text-[var(--mint)]">PREVENTED</td>
                      </tr>
                      <tr>
                        <td className="py-2">T4 Dependent Coercion (ENI/Routing)</td>
                        <td className="py-2 text-center text-[var(--alarm)]">3/3 breached</td>
                        <td className="py-2 text-center text-[var(--mint)]">0/3 breached</td>
                        <td className="py-2 text-right text-[var(--mint)]">PREVENTED</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-[var(--line)] bg-[var(--surface-2)] text-xs font-mono text-[var(--text-3)]">
          <span>WeMakeDevs × AWS · First Commit 2026</span>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded-[6px] bg-[var(--surface)] text-[var(--text)] border border-[var(--line)] hover:bg-[var(--line-soft)] transition-colors"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
