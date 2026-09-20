"use client";

import React, { useState, useEffect } from "react";
import {
  isDemoMode,
  setDemoMode,
  getApiBase,
  getConnectedAwsAccount,
  setConnectedAwsAccount,
  testAwsConnection,
} from "@/lib/api";

interface AwsConnectModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AwsConnectModal({ isOpen, onClose }: AwsConnectModalProps) {
  const [activeTab, setActiveTab] = useState<"api" | "iam">("api");
  const [apiUrl, setApiUrl] = useState("");
  const [accountId, setAccountId] = useState("");
  const [region, setRegion] = useState("ap-south-1");
  const [roleArn, setRoleArn] = useState("");
  const [accessKeyId, setAccessKeyId] = useState("");
  const [secretKey, setSecretKey] = useState("");

  const [testStatus, setTestStatus] = useState<{
    loading: boolean;
    success?: boolean;
    message?: string;
    latency_ms?: number;
    burn_inr_hour?: number;
  }>({ loading: false });

  const [isDemo, setIsDemo] = useState(true);
  const [currentAccount, setCurrentAccount] = useState<{
    accountId: string;
    region: string;
    endpoint: string;
  } | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setIsDemo(isDemoMode());
      const savedEndpoint = window.localStorage.getItem("netra_live_api_url") || "";
      setApiUrl(savedEndpoint);
      const acc = getConnectedAwsAccount();
      setCurrentAccount(acc);
      if (acc) {
        setAccountId(acc.accountId);
        setRegion(acc.region);
      }
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTestConnection = async () => {
    if (!apiUrl.trim()) {
      setTestStatus({
        loading: false,
        success: false,
        message: "Please enter an API Gateway endpoint URL first.",
      });
      return;
    }

    setTestStatus({ loading: true });
    const res = await testAwsConnection(apiUrl.trim());
    setTestStatus({
      loading: false,
      success: res.ok,
      message: res.message,
      latency_ms: res.latency_ms,
      burn_inr_hour: res.burn_inr_hour,
    });
  };

  const handleConnectApi = () => {
    if (!apiUrl.trim()) return;
    const cleanEndpoint = apiUrl.trim().replace(/\/+$/, "");
    setConnectedAwsAccount({
      accountId: accountId || "AWS-LIVE",
      region: region,
      endpoint: cleanEndpoint,
    });
    window.location.reload();
  };

  const handleConnectIam = () => {
    if (!accountId.trim()) {
      alert("Please enter a valid 12-digit AWS Account ID.");
      return;
    }
    // Store credentials in sessionStorage only (never persistent localStorage for secrets)
    if (typeof window !== "undefined") {
      if (accessKeyId) {
        window.sessionStorage.setItem("netra_aws_akid", accessKeyId);
      }
      if (secretKey) {
        window.sessionStorage.setItem("netra_aws_secret", secretKey);
      }
    }
    setConnectedAwsAccount({
      accountId: accountId.trim(),
      region: region,
      endpoint: apiUrl.trim() || getApiBase(),
    });
    window.location.reload();
  };

  const handleDisconnect = () => {
    setConnectedAwsAccount(null);
    setDemoMode(true);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in font-sans">
      <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[16px] max-w-2xl w-full p-6 space-y-5 shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-[var(--line-soft)] pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-[10px] bg-[#FF9900]/10 border border-[#FF9900]/30 flex items-center justify-center text-[#FF9900]">
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-bold text-[var(--text)] tracking-tight font-display flex items-center gap-2">
                Connect AWS Account
                <span className="px-2 py-0.5 rounded-[5px] text-[10px] font-mono uppercase bg-[var(--surface-2)] text-[var(--text-3)] border border-[var(--line-soft)]">
                  Live Telemetry
                </span>
              </h2>
              <p className="text-xs text-[var(--text-3)]">
                Link this cockpit directly to your AWS infrastructure or deployed SAM backend
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--text-3)] hover:text-[var(--text)] text-sm font-mono p-1.5 rounded-[6px] hover:bg-[var(--surface-2)] transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Current Active Status Indicator */}
        <div className="p-3.5 rounded-[10px] bg-[var(--surface-2)] border border-[var(--line-soft)] flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-2.5 w-2.5">
              {!isDemo ? (
                <>
                  <span className="animate-pulse-dot absolute inline-flex h-full w-full rounded-full bg-[var(--mint)] opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[var(--mint)]"></span>
                </>
              ) : (
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[var(--amber)]"></span>
              )}
            </span>
            <span className="text-[var(--text-2)]">
              Mode:{" "}
              <strong className={!isDemo ? "text-[var(--mint)]" : "text-[var(--amber)]"}>
                {!isDemo ? "LIVE AWS CONNECTED" : "DEMO SANDBOX (MOCK DATA)"}
              </strong>
              {currentAccount?.accountId && (
                <span className="text-[var(--text-3)] ml-1.5">
                  ({currentAccount.accountId} · {currentAccount.region})
                </span>
              )}
            </span>
          </div>

          {!isDemo && (
            <button
              onClick={handleDisconnect}
              className="px-2.5 py-1 rounded-[6px] text-[11px] font-mono bg-[var(--ember-bg)] border border-[var(--ember-line)] text-[var(--ember)] hover:opacity-80 transition-opacity"
            >
              Disconnect & Return to Demo
            </button>
          )}
        </div>

        {/* Tabs: API Gateway vs IAM Credentials */}
        <div className="flex border-b border-[var(--line-soft)] gap-2 text-xs font-mono">
          <button
            onClick={() => setActiveTab("api")}
            className={`pb-2 px-3 border-b-2 font-semibold transition-colors flex items-center gap-1.5 ${
              activeTab === "api"
                ? "border-[var(--mint)] text-[var(--mint)]"
                : "border-transparent text-[var(--text-3)] hover:text-[var(--text-2)]"
            }`}
          >
            <span>1. NETRA API Gateway</span>
            <span className="px-1.5 py-0.2 rounded text-[9px] bg-[var(--mint-bg)] text-[var(--mint)]">
              Recommended
            </span>
          </button>
          <button
            onClick={() => setActiveTab("iam")}
            className={`pb-2 px-3 border-b-2 font-semibold transition-colors flex items-center gap-1.5 ${
              activeTab === "iam"
                ? "border-[var(--mint)] text-[var(--mint)]"
                : "border-transparent text-[var(--text-3)] hover:text-[var(--text-2)]"
            }`}
          >
            <span>2. IAM & Account Login</span>
          </button>
        </div>

        {/* Tab 1: API Gateway Endpoint */}
        {activeTab === "api" && (
          <div className="space-y-4 overflow-y-auto pr-1 flex-1">
            <div className="text-xs text-[var(--text-2)] leading-relaxed space-y-2">
              <p>
                Connect to the live HTTP API Gateway generated when you run{" "}
                <code className="px-1.5 py-0.5 rounded bg-[var(--ground)] border border-[var(--line-soft)] text-[var(--text)] font-mono">
                  make deploy
                </code>{" "}
                or{" "}
                <code className="px-1.5 py-0.5 rounded bg-[var(--ground)] border border-[var(--line-soft)] text-[var(--text)] font-mono">
                  sam deploy
                </code>{" "}
                in your AWS account.
              </p>
              <div className="p-2.5 rounded-[8px] bg-[var(--ground)] border border-[var(--line-soft)] text-[11px] font-mono text-[var(--text-3)]">
                💡 To retrieve your endpoint from your terminal:
                <div className="text-[var(--mint)] mt-1 select-all">
                  aws cloudformation describe-stacks --stack-name netra --query &apos;Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue&apos; --output text
                </div>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-mono text-[var(--text-2)] block">
                API Gateway Endpoint URL
              </label>
              <input
                type="url"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="https://xyz123abc.execute-api.ap-south-1.amazonaws.com"
                className="w-full px-3.5 py-2.5 rounded-[8px] bg-[var(--ground)] border border-[var(--line)] text-xs font-mono text-[var(--text)] placeholder-[var(--text-3)] focus:outline-none focus:border-[var(--mint)] transition-colors"
              />
            </div>

            {/* Test Connection Button & Status Card */}
            <div className="flex items-center gap-3">
              <button
                onClick={handleTestConnection}
                disabled={testStatus.loading}
                className="px-3 py-2 rounded-[8px] bg-[var(--surface-2)] border border-[var(--line)] text-xs font-mono text-[var(--text-2)] hover:text-[var(--text)] hover:border-[var(--line-strong)] transition-all flex items-center gap-2"
              >
                {testStatus.loading ? (
                  <>
                    <span className="animate-spin text-[var(--mint)]">⟳</span>
                    <span>Pinging Endpoint...</span>
                  </>
                ) : (
                  <>
                    <span>⚡</span>
                    <span>Test Connection</span>
                  </>
                )}
              </button>

              <button
                onClick={handleConnectApi}
                disabled={!apiUrl.trim()}
                className="px-4 py-2 rounded-[8px] bg-[var(--mint)] hover:bg-[var(--mint)]/90 text-black font-semibold text-xs font-mono transition-opacity disabled:opacity-50"
              >
                Save & Connect Live AWS
              </button>
            </div>

            {/* Test Result Message */}
            {testStatus.message && (
              <div
                className={`p-3 rounded-[8px] text-xs font-mono border ${
                  testStatus.success
                    ? "bg-[var(--mint-bg)] border-[var(--mint-line)] text-[var(--mint)]"
                    : "bg-[var(--ember-bg)] border-[var(--ember-line)] text-[var(--ember)]"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span>{testStatus.success ? "✓" : "⚠"}</span>
                  <span>{testStatus.message}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: IAM & Account Login */}
        {activeTab === "iam" && (
          <div className="space-y-4 overflow-y-auto pr-1 flex-1">
            <div className="text-xs text-[var(--text-2)] leading-relaxed">
              Authenticate an AWS Account for client-side telemetry and cross-account monitoring.
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-mono text-[var(--text-2)] block">
                  AWS Account ID
                </label>
                <input
                  type="text"
                  value={accountId}
                  onChange={(e) => setAccountId(e.target.value)}
                  placeholder="123456789012"
                  maxLength={12}
                  className="w-full px-3 py-2 rounded-[8px] bg-[var(--ground)] border border-[var(--line)] text-xs font-mono text-[var(--text)] placeholder-[var(--text-3)] focus:outline-none focus:border-[var(--mint)]"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-mono text-[var(--text-2)] block">
                  Target Region
                </label>
                <select
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="w-full px-3 py-2 rounded-[8px] bg-[var(--ground)] border border-[var(--line)] text-xs font-mono text-[var(--text)] focus:outline-none focus:border-[var(--mint)]"
                >
                  <option value="ap-south-1">ap-south-1 (Mumbai)</option>
                  <option value="us-east-1">us-east-1 (N. Virginia)</option>
                  <option value="eu-west-1">eu-west-1 (Ireland)</option>
                  <option value="us-west-2">us-west-2 (Oregon)</option>
                </select>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-mono text-[var(--text-2)] block flex items-center justify-between">
                <span>IAM Role ARN (Optional for Cross-Account AssumeRole)</span>
              </label>
              <input
                type="text"
                value={roleArn}
                onChange={(e) => setRoleArn(e.target.value)}
                placeholder="arn:aws:iam::123456789012:role/NetraReadRole"
                className="w-full px-3 py-2 rounded-[8px] bg-[var(--ground)] border border-[var(--line)] text-xs font-mono text-[var(--text)] placeholder-[var(--text-3)] focus:outline-none focus:border-[var(--mint)]"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-mono text-[var(--text-2)] block">
                  Access Key ID (Optional)
                </label>
                <input
                  type="password"
                  value={accessKeyId}
                  onChange={(e) => setAccessKeyId(e.target.value)}
                  placeholder="AKIA..."
                  className="w-full px-3 py-2 rounded-[8px] bg-[var(--ground)] border border-[var(--line)] text-xs font-mono text-[var(--text)] placeholder-[var(--text-3)] focus:outline-none focus:border-[var(--mint)]"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-mono text-[var(--text-2)] block">
                  Secret Access Key (Optional)
                </label>
                <input
                  type="password"
                  value={secretKey}
                  onChange={(e) => setSecretKey(e.target.value)}
                  placeholder="••••••••••••••••"
                  className="w-full px-3 py-2 rounded-[8px] bg-[var(--ground)] border border-[var(--line)] text-xs font-mono text-[var(--text)] placeholder-[var(--text-3)] focus:outline-none focus:border-[var(--mint)]"
                />
              </div>
            </div>

            {/* Privacy notice */}
            <div className="p-3 rounded-[8px] bg-[var(--ground)] border border-[var(--line-soft)] text-[11px] text-[var(--text-3)] space-y-1">
              <div className="text-[var(--text-2)] font-semibold flex items-center gap-1.5 font-mono">
                <span>🔒</span>
                <span>Client-Side Security Guarantee</span>
              </div>
              <p>
                Credentials are kept strictly in ephemeral browser memory (`sessionStorage`) and are wiped when the tab is closed. No credentials are ever sent to backend logs or external servers.
              </p>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={handleConnectIam}
                className="px-4 py-2 rounded-[8px] bg-[var(--mint)] hover:bg-[var(--mint)]/90 text-black font-semibold text-xs font-mono transition-opacity"
              >
                Authorize & Connect Account
              </button>
            </div>
          </div>
        )}

        {/* Modal Footer */}
        <div className="border-t border-[var(--line-soft)] pt-3 flex items-center justify-between text-xs font-mono">
          <span className="text-[var(--text-3)]">
            Active Stack: AWS Serverless · ap-south-1
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-[7px] text-[var(--text-2)] hover:text-[var(--text)] hover:bg-[var(--surface-2)] transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
