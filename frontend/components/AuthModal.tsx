"use client";

import React, { useState, useEffect } from "react";
import {
  getCurrentUser,
  login,
  logout,
  generateApiKey,
  UserProfile,
} from "@/lib/api";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthChange?: (user: UserProfile) => void;
}

export default function AuthModal({ isOpen, onClose, onAuthChange }: AuthModalProps) {
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [activeTab, setActiveTab] = useState<"roles" | "custom" | "keys">("roles");
  const [customEmail, setCustomEmail] = useState("");
  const [customKey, setCustomKey] = useState("");
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setCurrentUser(getCurrentUser());
    }
  }, [isOpen]);

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

  const handleRoleSelect = async (email: string, role: "admin" | "operator" | "viewer") => {
    setIsLoading(true);
    setFeedback(null);
    try {
      const user = await login(email, role);
      setCurrentUser(user);
      if (onAuthChange) onAuthChange(user);
      setFeedback(`Switched session to ${user.name} (${user.role.toUpperCase()})`);
    } catch (err: any) {
      setFeedback(`Authentication failed: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCustomLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customEmail.trim()) return;
    setIsLoading(true);
    setFeedback(null);
    try {
      const user = await login(customEmail.trim(), "operator", customKey.trim() || undefined);
      setCurrentUser(user);
      if (onAuthChange) onAuthChange(user);
      setFeedback(`Authenticated as ${user.name}`);
    } catch (err: any) {
      setFeedback(`Login error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateKey = async () => {
    setIsLoading(true);
    setFeedback(null);
    try {
      const res = await generateApiKey();
      setGeneratedKey(res.api_key);
      setFeedback("New programmatic API Key minted with SHA-256 digest!");
    } catch (err: any) {
      setFeedback(`Key generation denied: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    logout();
    const def = getCurrentUser();
    setCurrentUser(def);
    if (onAuthChange) onAuthChange(def);
    setFeedback("Reset session to default Demo Operator.");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="relative w-full max-w-2xl bg-[var(--surface)] border border-[var(--line)] rounded-[16px] shadow-2xl overflow-hidden text-[var(--text)] font-sans"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--line)] bg-[var(--surface-2)]">
          <div className="flex items-center gap-3">
            <div className="p-1.5 rounded-[8px] bg-[var(--mint-bg)] border border-[var(--mint-line)] text-[var(--mint)]">
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>
            <div>
              <h2 className="text-base font-bold tracking-tight">Enterprise Access & RBAC Identity (eauth)</h2>
              <p className="text-xs text-[var(--text-3)] font-mono">HMAC-SHA256 Token Engine · AWS Cedar Guardrail Alignment</p>
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

        {/* Current Identity Bar */}
        <div className="px-6 py-3 bg-[var(--ground)] border-b border-[var(--line-soft)] flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="text-[var(--text-3)]">ACTIVE IDENTITY:</span>
            <span className="text-[var(--text)] font-semibold">{currentUser?.name}</span>
            <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${
              currentUser?.role === "admin"
                ? "bg-[var(--ember)]/10 text-[var(--ember)] border-[var(--ember)]/30"
                : currentUser?.role === "operator"
                ? "bg-[var(--mint-bg)] text-[var(--mint)] border-[var(--mint-line)]"
                : "bg-[var(--surface-2)] text-[var(--text-3)] border-[var(--line)]"
            }`}>
              {currentUser?.role}
            </span>
          </div>
          <button
            onClick={handleReset}
            className="text-[11px] text-[var(--text-3)] hover:text-[var(--text)] underline decoration-dotted"
          >
            Reset Default
          </button>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-2 px-6 py-2 border-b border-[var(--line)] bg-[var(--surface-2)]/50 text-xs font-mono">
          <button
            onClick={() => setActiveTab("roles")}
            className={`px-3 py-1.5 rounded-[6px] transition-colors ${
              activeTab === "roles"
                ? "bg-[var(--surface)] text-[var(--mint)] border border-[var(--line)] font-medium"
                : "text-[var(--text-3)] hover:text-[var(--text)]"
            }`}
          >
            Judge Personas (1-Click)
          </button>
          <button
            onClick={() => setActiveTab("custom")}
            className={`px-3 py-1.5 rounded-[6px] transition-colors ${
              activeTab === "custom"
                ? "bg-[var(--surface)] text-[var(--mint)] border border-[var(--line)] font-medium"
                : "text-[var(--text-3)] hover:text-[var(--text)]"
            }`}
          >
            Custom Credentials
          </button>
          <button
            onClick={() => setActiveTab("keys")}
            className={`px-3 py-1.5 rounded-[6px] transition-colors ${
              activeTab === "keys"
                ? "bg-[var(--surface)] text-[var(--mint)] border border-[var(--line)] font-medium"
                : "text-[var(--text-3)] hover:text-[var(--text)]"
            }`}
          >
            Mint API Keys
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
          {feedback && (
            <div className="p-3 rounded-[8px] bg-[var(--mint-bg)] border border-[var(--mint-line)] text-xs text-[var(--mint)] font-mono">
              {feedback}
            </div>
          )}

          {activeTab === "roles" && (
            <div className="space-y-3">
              <p className="text-xs text-[var(--text-2)] mb-3">
                Select a pre-configured role to immediately test permission boundaries across Step Functions, Cedar policies, and rollback restoration:
              </p>

              {/* Admin Persona */}
              <div
                onClick={() => handleRoleSelect("admin@we-make-devs.org", "admin")}
                className={`p-4 rounded-[12px] border cursor-pointer transition-all flex items-start justify-between ${
                  currentUser?.role === "admin"
                    ? "bg-[var(--surface-2)] border-[var(--ember)]"
                    : "bg-[var(--surface-2)]/60 border-[var(--line)] hover:border-[var(--text-3)]"
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">Lead Cloud Architect</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[var(--ember)]/10 text-[var(--ember)] border border-[var(--ember)]/30 font-bold uppercase">ADMIN</span>
                  </div>
                  <p className="text-xs text-[var(--text-3)] font-mono">admin@we-make-devs.org</p>
                  <p className="text-xs text-[var(--text-2)] pt-1">
                    Unrestricted authority: approve remediations, trigger 1-click snapshot rollbacks, and generate API keys.
                  </p>
                </div>
                {currentUser?.role === "admin" && (
                  <span className="text-[var(--ember)] text-xs font-mono font-bold">ACTIVE</span>
                )}
              </div>

              {/* Operator Persona */}
              <div
                onClick={() => handleRoleSelect("operator@we-make-devs.org", "operator")}
                className={`p-4 rounded-[12px] border cursor-pointer transition-all flex items-start justify-between ${
                  currentUser?.role === "operator"
                    ? "bg-[var(--surface-2)] border-[var(--mint)]"
                    : "bg-[var(--surface-2)]/60 border-[var(--line)] hover:border-[var(--text-3)]"
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">FinOps SRE Operator</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[var(--mint-bg)] text-[var(--mint)] border border-[var(--mint-line)] font-bold uppercase">OPERATOR</span>
                  </div>
                  <p className="text-xs text-[var(--text-3)] font-mono">operator@we-make-devs.org</p>
                  <p className="text-xs text-[var(--text-2)] pt-1">
                    Standard operational authority: mint HMAC approval tokens, dismiss findings, and snooze alert windows. Rollbacks forbidden.
                  </p>
                </div>
                {currentUser?.role === "operator" && (
                  <span className="text-[var(--mint)] text-xs font-mono font-bold">ACTIVE</span>
                )}
              </div>

              {/* Viewer Persona */}
              <div
                onClick={() => handleRoleSelect("auditor@we-make-devs.org", "viewer")}
                className={`p-4 rounded-[12px] border cursor-pointer transition-all flex items-start justify-between ${
                  currentUser?.role === "viewer"
                    ? "bg-[var(--surface-2)] border-[var(--text-2)]"
                    : "bg-[var(--surface-2)]/60 border-[var(--line)] hover:border-[var(--text-3)]"
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">Compliance Auditor</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[var(--surface)] text-[var(--text-3)] border border-[var(--line)] font-bold uppercase">VIEWER</span>
                  </div>
                  <p className="text-xs text-[var(--text-3)] font-mono">auditor@we-make-devs.org</p>
                  <p className="text-xs text-[var(--text-2)] pt-1">
                    Read-only audit authority: view real-time spend, audit trails, and invariants. All mutation requests return 403 Forbidden.
                  </p>
                </div>
                {currentUser?.role === "viewer" && (
                  <span className="text-[var(--text-2)] text-xs font-mono font-bold">ACTIVE</span>
                )}
              </div>
            </div>
          )}

          {activeTab === "custom" && (
            <form onSubmit={handleCustomLogin} className="space-y-4 font-mono text-xs">
              <div>
                <label className="block text-[var(--text-2)] mb-1">OPERATOR EMAIL / IAM PRINCIPAL</label>
                <input
                  type="email"
                  value={customEmail}
                  onChange={(e) => setCustomEmail(e.target.value)}
                  placeholder="sre-oncall@your-company.com"
                  className="w-full px-3 py-2 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] text-[var(--text)] focus:border-[var(--mint)] focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-[var(--text-2)] mb-1">OPTIONAL API KEY OR BEARER TOKEN</label>
                <input
                  type="password"
                  value={customKey}
                  onChange={(e) => setCustomKey(e.target.value)}
                  placeholder="netra_live_..."
                  className="w-full px-3 py-2 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] text-[var(--text)] focus:border-[var(--mint)] focus:outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 rounded-[8px] bg-[var(--mint-bg)] border border-[var(--mint-line)] text-[var(--mint)] font-bold hover:bg-[var(--mint)]/20 transition-colors"
              >
                {isLoading ? "Signing Token..." : "Issue Session JWT"}
              </button>
            </form>
          )}

          {activeTab === "keys" && (
            <div className="space-y-4">
              <p className="text-xs text-[var(--text-2)]">
                Programmatic API keys allow CI/CD pipelines (e.g. GitHub Actions, Terraform, ArgoCD) to query spend velocity or trigger automated policy checks.
              </p>

              {currentUser?.role !== "admin" ? (
                <div className="p-4 rounded-[10px] bg-[var(--amber-bg)] border border-[var(--amber-line)] text-xs text-[var(--amber)]">
                  Only users with the <strong>ADMIN</strong> role can mint programmatic API keys. Switch to Lead Cloud Architect in the Personas tab first.
                </div>
              ) : (
                <div className="space-y-3">
                  <button
                    onClick={handleGenerateKey}
                    disabled={isLoading}
                    className="px-4 py-2 rounded-[8px] bg-[var(--mint-bg)] border border-[var(--mint-line)] text-xs font-mono text-[var(--mint)] font-bold hover:bg-[var(--mint)]/20 transition-colors flex items-center gap-2"
                  >
                    <span>Generate New API Key (POST /api/auth/keys)</span>
                  </button>

                  {generatedKey && (
                    <div className="p-4 rounded-[10px] bg-[var(--surface-2)] border border-[var(--line)] space-y-2 font-mono text-xs">
                      <div className="flex items-center justify-between text-[var(--text-3)] text-[11px]">
                        <span>RAW API KEY (STORE SECURELY):</span>
                        <span className="text-[var(--mint)]">HMAC-SHA256 Bound</span>
                      </div>
                      <code className="block p-2 rounded bg-[var(--ground)] text-[var(--mint)] break-all select-all">
                        {generatedKey}
                      </code>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-[var(--line)] bg-[var(--surface-2)] text-xs font-mono text-[var(--text-3)]">
          <span>Session Token: 8h TTL · Signed JWT</span>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded-[6px] bg-[var(--surface)] text-[var(--text)] border border-[var(--line)] hover:bg-[var(--line-soft)] transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
