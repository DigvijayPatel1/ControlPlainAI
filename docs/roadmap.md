# ControlPlane AI — Roadmap

## Phased Scope (full product vision)

| Phase | Scope |
|---|---|
| Phase 1 | FastAPI reverse proxy, MongoDB logs/state, token & latency tracking, regex + NER PII protection, React/Node dashboard |
| Phase 2 | LLM-as-judge evaluation, LiteLLM model routing, Redis semantic caching, WebSocket human review |
| Phase 3 | Redis messaging at scale, Prometheus/Grafana monitoring, OpenTelemetry tracing, virtual API keys, hierarchical budget controls |

For the hackathon, we build a working slice of Phase 1 + selected Phase 2 features, plus the extension/Entra enrollment path and offline red-team scanning from the merged design. Phase 3 items are presented as roadmap only.

## Hackathon Build Order — 7 Days

Two-track split: **Track A (backend/pipeline)**, **Track B (dashboard/extension/identity)**.

### Day 1 — Foundations
- **Track A:** FastAPI proxy skeleton (`api/router.py`, `api/routes/chat.py`), MongoDB connection (`core/database.py`), `request_log` repository + model + schema
- **Track B:** Entra ID app registration and enrollment token issuance (mock OAuth acceptable if real Entra setup is too slow); React dashboard skeleton
- **Checkpoint:** proxy logs every call end-to-end; enrollment issues a token

### Day 2 — Guardrail engine v1
- **Track A:** PII detector (regex + NER), toxicity/profanity check, embedding-similarity drift check, format validator — wired into `guardrails/pipeline.py`
- **Track B:** Browser extension skeleton that injects into a demo chatbot page and calls the proxy with the enrollment token attached
- **Checkpoint:** every request is scored on Performance + Safety; extension round-trips through the proxy successfully

### Day 3 — Decision engine + policies
- **Track A:** `guardrails/decision_engine.py` mapping scores → Allow / Mask / Block / Review; token counting and per-user cost tracking in `budget_service.py`
- **Track B:** Dashboard wired to show live verdicts; per-bot security policy toggle UI (Block / Mask / Monitor)
- **Checkpoint:** a flagged request is actually masked or blocked, not just logged, and shows up on the dashboard

### Day 4 — Human review + LLM-as-judge
- **Track A:** LLM-as-judge grounding check (`guardrails/judge/llm_judge.py`); `review_repo.py` + review queue collection
- **Track B:** Review queue UI (approve/edit/override) with WebSocket or polling live updates
- **Checkpoint:** a high-risk item appears in the queue and an admin overrides it live

### Day 5 — Security Centre + red-team scanner
- **Track A:** Risk-finding history aggregation (risk finding → DB → history), event overview rollups, seeded demo-session data
- **Track B:** Run Garak / DeepTeam offline against a demo chatbot's prompt library, pipe findings into the risk DB, build the risk report export view
- **Checkpoint:** dashboard shows aggregate risk history plus a red-team scan report, clearly separated from live traffic

### Day 6 — Routing, caching, MCP, polish
- **Track A:** Model routing (small vs. large model via LiteLLM), Redis semantic cache, MCP server exposing dashboard data, latency benchmarking
- **Track B:** UI polish, cost/token visualizations, clean seed data, fix rough edges across both entry points
- **Checkpoint:** the full demo path works end-to-end without manual intervention

### Day 7 — Demo prep
- Both tracks: rehearse the full script (see `demo-script.md`); finalize the pitch deck with the architecture diagram and objective-coverage table; record a backup demo video

## Explicitly deferred (mention as future work only)
Prometheus/Grafana, OpenTelemetry tracing, hierarchical multi-org budget controls, full production Entra tenant rollout.