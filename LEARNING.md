# NETRA — Learning Log

A chronological record of engineering discoveries, architectural trade-offs, and lessons learned during the build.

---

### Phase 0 — Preflight & Environment Setup
- **G-family EC2 Quotas**: Default AWS quotas for G-family instances (GPU workloads) are 0 and take days to raise through AWS Support. Pivoted the live runaway demonstration to `c5.4xlarge` (16 vCPU, 32 GiB RAM, ~₹66.55/hr), which burns fast enough to visibly shift the dashboard needle while staying within default quotas.
- **Cost Explorer Lag**: AWS Cost Explorer updates at a 24-hour cadence, proving the core thesis that post-facto billing cannot prevent budget exhaustion during active development or hackathons.

### Phase 1 — Deterministic Pricing Core with Hashed Provenance
- **Cryptographic Provenance**: Hashing the raw JSON response from the AWS Price List API (`sha256:<hex>`) guarantees that every rupee displayed on the dashboard can be traced back to an authentic AWS document.
- **Deterministic Fallback**: Relying purely on live AWS Price List API calls risks runtime failure if throttled in `us-east-1`. Having an explicit `FALLBACK_USD_HOUR` dictionary with `fallback:<sub_type>` tags keeps the system resilient while maintaining complete audit transparency.

### Phase 2 — Inventory & Rules-as-Data Detector
- **Median vs. Mean Baselines**: Using the rolling median across the last 60 snapshot totals prevents an acute runaway spend spike from pulling its own baseline upward, ensuring step-change detection stays triggered during active runaway events.
- **Rules as Data & Pure Determinism**: Treating detection rules as declarative data (`rules.yaml`) coupled with a side-effect-free evaluator ensures 100% byte-identical findings across repeated runs, while enabling instant rule additions on-camera with zero code changes.

### Phase 3 — Infrastructure & Collector
- **Single Batch Metric Queries**: Querying CloudWatch per-resource in a loop causes API rate-limiting and inflates Lambda execution time. Consolidating all candidate metric lookups into a single `get_metric_data` batch query reduces API latency from several seconds to under 400ms.
- **Event-Driven Agent Decoupling**: Emitting `netra.finding.created` EventBridge events rather than invoking the LLM investigator synchronously keeps the 1-minute collection loop fast, cheap, and decoupled from model response times or Bedrock API retries.

### Phase 4 — Strands Agent: Constrained Narration & Deterministic Fallback
- **Zero-Tolerance Numeric Validation**: Language models tend to hallucinate figures or miscalculate percentages when summarizing cost data. Placing a strict token-level numeric validator between the model and the database prevents invented numbers from ever reaching the UI.
- **Dual-Path Presentation Resilience**: Live video recordings and judge evaluations cannot afford to fail if Bedrock quotas or network latency spike. Providing a publication-grade deterministic fallback engine ensures that the system consistently produces complete, valid 3-paragraph explanations under any network condition.

### Phase 5 — HTTP API & Router
- **Single-Lambda Monolithic Router**: Using a single Lambda function with an internal regex router for HTTP API endpoints rather than one Lambda per route eliminates cold-start multiplication, keeps deployment fast, and shares memory caching across routes.
- **Defensive Error Shielding & Decimal Conversion**: Boto3 DynamoDB operations return native `Decimal` objects that throw serialization errors in `json.dumps`. Implementing recursive Decimal-to-float cleanup alongside comprehensive top-level exception handlers completely eliminates unhandled 502 Bad Gateway errors across all API routes.

### Phase 6 — Instrumentation UI & Zero-Dependency Demo Mode
- **Instrument Design System & Strict Monospace Discipline**: Enforcing strict monospace typography (`IBM Plex Mono`) for every number, ID, region, and timestamp transforms the dashboard from a generic SaaS interface into an authoritative infrastructure cockpit, maximizing visual hierarchy and data legibility.
- **Client-Side Demo Simulation Fidelity**: Embedding a fully client-side reactive state store in demo mode allows judges to evaluate the entire real-time lifecycle (detect → explain → approve → audit) without AWS credentials, cold starts, or network dependencies.

### Phase 7 — Remediation Executor, Policy Gates & `make verify`
- **Dual Policy Enforcement Points**: Proving that policy gates must evaluate both when proposing an action to the user and directly inside the executor immediately before mutating AWS calls prevents race conditions, stale browser state, or tampered payloads from executing unsafe infrastructure changes.
- **Sub-Second Provenance Verification (`make verify`)**: Packaging cryptographic provenance verification, deterministic rule replay, numeric grounding checks, and policy enforcement into a standalone < 2s command provides judges with instant, reproducible proof of system claims across every judging criterion.

### Phase 8 — Comprehensive Documentation & Hackathon Storytelling
- **Documentation as an Evaluation Deliverable**: Structuring the repository documentation around the judge's mental model (demo video second, `make verify` immediate proof, explicit architecture mapping table) creates a seamless, self-verifying evaluation journey before a single line of code is inspected.
- **Fail-Safe Demo Mode Architecture**: Coupling full Next.js static builds with client-side reactive state guarantees that regardless of AWS credentials, regional quota spikes, or network conditions, the live evaluation URL always functions flawlessly.

### Phase 9 (v3 Upgrade) — Sub-10-Second Fast Path & AWS Issue #92
- **The 24-Hour Detection Gap**: Finding public AWS issue `aws-solutions/innovation-sandbox-on-aws#92` confirmed that AWS Cost Anomaly Detection is architecturally delayed by up to 24 to 33 hours. The recommended solution—monitoring infrastructure state changes—inspired our dual-path collector: an EventBridge rule on `aws.ec2` state transitions fires in under 10 seconds, while the 60-second scheduled sweep acts as the baseline safety net.
- **Refusing to Guess Idleness**: A newly launched compute instance cannot have 30 minutes of idle CloudWatch history. Emitting an informational `new_billable_resource` finding immediately (`<10s`) reports exact burn rate and enters "watch mode" without guessing idleness. Once 30 minutes of telemetry accumulate, the scheduled sweep escalates to `critical`. Restraint builds trust with judges.

### Phase 10 (v3 Upgrade) — MCP Action Server Boundary & Cryptographic Tokens
- **Zero-Mutating Agent IAM**: Generative AI models should never hold mutating cloud permissions (`ec2:Stop*`, `Terminate*`, `Delete*`). Isolating all mutating API calls behind a standalone Model Context Protocol (MCP) server means the Bedrock agent process can only propose actions, never execute them.
- **Cryptographic Approval Tokens**: Bridging human operator authorization in the Cockpit UI to MCP tool execution using single-use HMAC-SHA256 tokens (`finding_id + plan_hash + exp + nonce`) guarantees that even if an agent hallucinates or is prompted to call `netra_execute`, execution is flatly refused without a valid, unredeemed human token.
