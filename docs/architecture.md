# ControlPlane AI — Architecture

## 1. Overview

ControlPlane AI is a real-time guardrail layer sitting between users and LLM backends. It has **two entry points that converge on one shared pipeline**:

1. **Direct API clients** — authenticated with a virtual API key, calling the proxy the same way they'd call an LLM provider directly.
2. **Browser extension clients** — enrolled via a Microsoft Entra ID token, injected into existing chatbots (customer support, internal employee, regulated-decision bots) to monitor traffic at the endpoint.

Both paths hit the same FastAPI guardrail proxy, so there is exactly one place where checks, decisions, and audit logging happen — this is what keeps latency predictable and the system auditable.

```
Direct API client ─┐
                    ├──> Guardrail Proxy ──> Decision Engine ──> Security Centre Dashboard
Browser extension ──┘         │                    │
                       (Performance,          (Allow / Mask /
                        Cost, Safety            Block / Review)
                        checks)
```

A separate, **offline** red-team scanner (Garak / DeepTeam) runs against a prompt library before deployment and feeds findings into the same risk database — it is intentionally kept out of the live request path because these tools are slow by design.

## 2. Core Layers

| Layer | Responsibility |
|---|---|
| Performance | Grounding/hallucination check, off-topic drift detection, format validation |
| Cost & Compute | Token tracking, model routing (small vs. large model), semantic caching |
| Responsibility & Safety | PII detection (regex + NER), toxicity/bias detection, policy checks |
| Decision Engine | Maps layer scores to one of: Allow, Mask, Block, Human Review |
| Security Centre | Audit log, risk-finding history, event overview, reporting, MCP server |

## 3. Identity & Access

- **Virtual API keys** — issued per direct-API consumer, tied to a budget/quota
- **Entra ID enrollment tokens** — issued per extension install, used to authenticate and regulate extension traffic
- Both identity types resolve to the same internal principal model so budgets and audit trails are unified regardless of entry point

## 4. Backend File Structure

```
backend/
├── app/
│   ├── main.py                          # FastAPI app entrypoint
│   ├── core/
│   │   ├── config.py                    # env/config management
│   │   ├── database.py                  # Mongo/Redis client setup
│   │   ├── security.py                  # API key + Entra token auth
│   │   ├── logging.py
│   │   └── rate_limit.py
│   ├── api/
│   │   ├── router.py                    # aggregates and mounts all route routers
│   │   ├── deps.py                      # shared dependencies (auth, db session)
│   │   └── routes/
│   │       ├── chat.py                  # /v1/chat/completions proxy endpoint
│   │       ├── admin.py                 # dashboard/admin APIs
│   │       ├── review.py                # human-in-the-loop endpoints
│   │       └── health.py
│   ├── proxy/
│   │   ├── llm_gateway.py               # LiteLLM wrapper, model routing
│   │   └── streaming.py                 # SSE/WebSocket streaming handler
│   ├── guardrails/
│   │   ├── pipeline.py                  # orchestrates prompt+response checks
│   │   ├── performance/
│   │   │   ├── hallucination_check.py
│   │   │   ├── drift_check.py
│   │   │   └── format_validator.py
│   │   ├── cost/
│   │   │   ├── token_tracker.py
│   │   │   ├── model_router.py
│   │   │   └── cache_manager.py
│   │   ├── safety/
│   │   │   ├── pii_detector.py
│   │   │   ├── toxicity_detector.py
│   │   │   ├── bias_detector.py
│   │   │   └── policy_checker.py
│   │   ├── judge/
│   │   │   └── llm_judge.py             # LLM-as-judge evaluation
│   │   └── decision_engine.py           # verdict → action mapping
│   ├── schemas/                          # Pydantic request/response schemas
│   │   ├── request_log.py
│   │   ├── review_item.py
│   │   ├── budget.py
│   │   └── api_key.py
│   ├── models/                           # DB document models
│   │   ├── request_log.py
│   │   ├── review_item.py
│   │   ├── budget.py
│   │   └── api_key.py
│   ├── repositories/                     # DB CRUD / query logic
│   │   ├── request_log_repo.py
│   │   ├── review_repo.py
│   │   ├── budget_repo.py
│   │   └── api_key_repo.py
│   ├── services/
│   │   ├── budget_service.py
│   │   ├── notification_service.py
│   │   └── audit_service.py
│   ├── workers/
│   │   ├── review_queue_worker.py
│   │   └── budget_reset_worker.py
│   └── websocket/
│       └── review_socket.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── requirements.txt
└── Dockerfile
```

**Layering rule of thumb:** `routes/` call `services/`, `services/` call `repositories/`, `repositories/` are the only layer that touches the database directly. `schemas/` define what crosses the API boundary; `models/` define what's stored. Keeping these separate means changing your API response shape never forces a database migration, and vice versa.

## 5. Frontend / Extension Structure

```
frontend/
├── src/
│   ├── pages/          # Dashboard, LiveFeed, ReviewQueue, Analytics, Settings
│   ├── components/     # VerdictBadge, RequestCard, ReviewModal, CostChart
│   ├── hooks/          # useWebSocket, useAuth
│   ├── api/            # client.ts
│   └── store/

extension/
├── src/
│   ├── content-script.js   # injected into monitored chatbot pages
│   ├── background.js       # holds Entra enrollment token, relays to proxy
│   └── popup/               # enrollment UI
```

## 6. Data Stores

- **MongoDB** — request logs, review queue, risk-finding history, budgets, API keys
- **Redis** — semantic cache, rate limiting counters (Phase 2+)

## 7. Deferred to Phase 3 (mentioned in pitch, not built for the hackathon)

Prometheus/Grafana monitoring, OpenTelemetry tracing, hierarchical budget controls, full production Entra tenant integration.