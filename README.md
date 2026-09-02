# ControlPlainAI

**ControlPlainAI** is a safety, cost, and observability guardrail platform for AI chat traffic. It sits between a user and an LLM (their own conversations on ChatGPT, Claude, or Gemini, or programmatic calls made through its own API) and inspects every prompt and response for PII, toxicity, bias, policy violations, hallucination, and format issues — then blocks, masks, routes to a human reviewer, or lets the content through, while tracking token usage, cost, and budget per user.

The project has three parts that work together:

| Component | What it is | Tech stack |
|---|---|---|
| **`backend/`** | The guardrail engine and API. Runs the safety/cost/performance pipeline, stores requests, budgets, and review items, authenticates users, and exposes a ChatGPT-compatible proxy endpoint. | FastAPI, PostgreSQL (SQLAlchemy async + Alembic), Redis, OpenAI SDK, JWT auth, `uv` for dependency management |
| **`frontend/`** | A web dashboard for signing up, viewing request history and analytics, managing the human-review queue, and configuring the account. | React 19, Redux Toolkit, React Router, Tailwind CSS 4, Vite |
| **`extension/`** | A Chrome (Manifest V3) browser extension that injects into `chatgpt.com`, `chat.openai.com`, `claude.ai`, and `gemini.google.com`, intercepts what you type and what the model replies, and routes it through the backend's guardrail pipeline before it's sent/shown. | React 19, Vite (3 separate build targets: popup UI, content script, background service worker), Tailwind CSS 4 |

## How the pieces fit together

1. **You sign up / log in on the frontend dashboard** (`frontend`), which talks to the backend's `/auth` endpoints and issues you a JWT plus an API key.
2. **You connect the browser extension** from the dashboard's Settings page — the frontend pushes your API key straight into the extension's storage via `chrome.runtime.sendMessage` (no copy/paste), using the extension ID you configure in `frontend/.env`.
3. **You chat normally on ChatGPT, Claude, or Gemini.** The extension's content script intercepts your prompt before it's sent and the model's response before it's rendered, and asks its background service worker to check each one.
4. **The service worker calls the backend's `/guardrails` endpoints** (never the LLM provider directly from the browser — the OpenAI key lives only on the backend).
5. **The backend runs the guardrail pipeline** (`backend/app/guardrails/pipeline.py`):
   - **Safety checks:** PII detection/redaction, policy checks, sensitivity checks, toxicity, bias
   - **Cost checks:** prompt optimization (token reduction), response caching, model routing (auto-selects a cheaper model when appropriate), token/cost estimation
   - **Performance checks (on responses):** drift detection, hallucination detection, format validation, and an optional LLM-as-judge pass for borderline cases
   - **Decision engine** turns all of the above into one verdict: **PASS**, **MASK** (redact PII and continue), **REVIEW** (hold for a human), or **BLOCK**
6. Every request is logged, budgets are decremented, and anything sent to **REVIEW** shows up in real time on the dashboard's Reviews page via a WebSocket (`backend/app/websocket/review_socket.py`).
7. There's also a **direct API path**: `POST /v1/chat/completions` (`chat_router.py`) is a ChatGPT-compatible endpoint that runs a prompt through the full guardrail pipeline and an actual OpenAI call, so you can point any OpenAI-SDK-compatible client at ControlPlainAI instead of at OpenAI directly.

## Backend structure (`backend/`)

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, health checks, lifespan (dev auto-creates tables)
│   ├── api/
│   │   ├── router.py            # aggregates all route modules
│   │   └── routes/
│   │       ├── auth_router.py         # /auth/register, /auth/login
│   │       ├── chat_router.py         # /v1/chat/completions — guarded OpenAI-compatible proxy
│   │       ├── guardrail_router.py    # /guardrails/* — used by the browser extension
│   │       ├── request_router.py      # /api/requests — request history for the caller
│   │       ├── analytics_router.py    # /v1/analytics/* — dashboard summaries
│   │       ├── budget_router.py       # /v1/budget — current spend/limits
│   │       ├── review_router.py, human_reviews_router.py  # human-review queue
│   ├── core/                    # config (pydantic-settings), DB engine, JWT/security, rate limiting, logging
│   ├── guardrails/
│   │   ├── pipeline.py           # orchestrates the full input/output guardrail flow
│   │   ├── decision_engine.py    # turns check results into PASS/MASK/REVIEW/BLOCK
│   │   ├── contracts.py          # shared CheckResult / PipelineResult dataclasses
│   │   ├── safety/               # pii_detector, pii_redactor, pii_policy, toxicity, bias, policy, sensitivity
│   │   ├── cost/                 # token_tracker, model_router, cache_manager, prompt_optimizer
│   │   ├── performance/          # drift_check, hallucination_check, format_validator
│   │   ├── judge/                # llm_judge.py — LLM-as-judge for borderline responses
│   │   └── providers/            # openai_provider.py
│   ├── llm/openai_provider.py   # OpenAI SDK wrapper used by chat_router
│   ├── models/                  # SQLAlchemy models: User, ApiKey, Budget, RequestLog, ReviewItem, RequestCheck
│   ├── repositories/             # DB query layer per model
│   ├── schemas/                  # Pydantic request/response schemas
│   ├── services/                 # auth, api_key, budget, audit, notification, review, redis
│   ├── websocket/review_socket.py  # live push of new/updated review items to the dashboard
│   ├── workers/                  # budget_reset_worker.py, review_queue_worker.py (background jobs)
│   └── scripts/create_api_key.py  # CLI helper to mint a dev API key
├── alembic/                      # DB migrations
├── tests/                        # pytest suite: guardrails, budget, PII policy, security, full e2e flow
├── docker-compose.yaml           # Postgres + Redis for local dev
├── pyproject.toml / uv.lock      # dependencies, managed with `uv`
└── .env.example
```

## Frontend structure (`frontend/`)

```
frontend/src/
├── App.jsx                 # routes: /login, /register, / (overview), /requests, /reviews, /settings
├── api/baseApi.js          # RTK Query base API talking to VITE_API_BASE
├── app/store.js            # Redux store
├── components/RouteGuards.jsx  # ProtectedRoute / PublicOnlyRoute
├── features/
│   ├── auth/                # LoginPage, RegisterPage, authApi, authSlice
│   └── dashboard/
│       ├── DashboardLayout.jsx
│       ├── OverviewPage.jsx     # usage/cost widgets
│       ├── RequestsPage.jsx     # request history
│       ├── ReviewsPage.jsx      # human-review queue (live via WebSocket)
│       ├── SettingsPage.jsx     # API key, "Connect extension" button
│       └── dashboardApi.js
└── lib/extension.js         # bridges the dashboard to the installed Chrome extension
```

## Extension structure (`extension/`)

```
extension/
├── manifest.json            # MV3 manifest — host permissions for chatgpt.com, claude.ai, gemini.google.com
├── src/
│   ├── background/service-worker.js   # owns the API key, talks to the backend, holds monitored-site list
│   ├── content/
│   │   ├── Content-main.jsx / chatController.js / GuardOverlay.jsx / guardBus.js / providers.js
│   │   # injected into the chat page: intercepts prompt submission and rendered responses
│   ├── lib/api.js            # sendMessage wrappers: CHECK_INPUT, CHECK_OUTPUT, GET_REVIEW_STATUS
│   ├── lib/storage.js
│   └── App.jsx               # the toolbar popup UI
├── vite.config.js            # builds the popup (index.html)
├── vite.content.config.js    # builds content-main.js (content script)
├── vite.background.config.js # builds service-worker.js (background script)
└── scripts/copy-extension-assets.mjs  # copies manifest.json/icons into dist/ after build
```

---

## Prerequisites

- **Python 3.12** and [`uv`](https://docs.astral.sh/uv/) (the backend uses `uv.lock`; `pip` works too if you prefer)
- **Node.js 18+** and npm (for both `frontend` and `extension`)
- **Docker** (for Postgres + Redis via `docker-compose.yaml`) — or your own local Postgres 16 and Redis 7
- An **OpenAI API key** (for the guarded `/v1/chat/completions` proxy and the LLM-judge check)
- **Google Chrome** or another Chromium-based browser (for the extension)

---

## Getting started — run order: backend → frontend → extension

### 1. Backend

```bash
cd backend

# start Postgres + Redis
docker compose up -d

# install dependencies
uv sync
# (or, without uv: python -m venv .venv && source .venv/bin/activate && pip install -e .)

# configure environment
cp .env.example .env
# then edit .env and set at minimum:
#   OPENAI_API_KEY=sk-...
#   JWT_SECRET_KEY=<a long random string>

# run the API (tables are auto-created on startup in development mode)
uv run fastapi dev app/main.py
# (or: uv run uvicorn app.main:app --reload --port 8000)
```

The API is now on `http://localhost:8000`. Check it's alive:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/database
curl http://localhost:8000/health/redis
```

Optional helpers, run from `backend/`:

```bash
uv run python app/scripts/create_api_key.py   # mint a demo API key + principal for local testing
uv run python reset_dev.py                     # wipe the demo API key/budget
uv run alembic upgrade head                    # apply migrations (dev mode auto-creates tables, but use this for a production-style setup)
uv run pytest                                  # run the test suite
```

Background workers (budget resets, review-queue processing) can be run alongside the API as separate processes if you need them locally:

```bash
uv run python -m app.workers.budget_reset_worker
uv run python -m app.workers.review_queue_worker
```

### 2. Frontend

```bash
cd frontend
npm install

cp .env.example .env
# VITE_API_BASE=http://localhost:8000 is already the default
# VITE_EXTENSION_ID can be filled in once you've loaded the extension (step 3) and
# copied its ID from chrome://extensions

npm run dev
```

The dashboard runs on `http://localhost:5173` (Vite will pick the next free port if that's taken — the backend's CORS is already configured to allow any `localhost`/`127.0.0.1` port in development). Register an account, log in, and you'll land on the Overview page.

### 3. Extension

```bash
cd extension
npm install
npm run build
```

`npm run build` runs three Vite builds back to back (popup, content script, background service worker) and then copies `manifest.json` and icons into `dist/` via `scripts/copy-extension-assets.mjs`.

Load it into Chrome:
1. Go to `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** and select `extension/dist`
4. Copy the extension's ID shown on its card
5. Paste that ID into `frontend/.env` as `VITE_EXTENSION_ID`, restart the frontend dev server, then use the **"Connect extension"** button on the dashboard's Settings page to push your API key into it automatically

Once connected, open `chatgpt.com`, `claude.ai`, or `gemini.google.com` — the extension will intercept prompts/responses on those sites and route them through your local backend at `http://localhost:8000` (already whitelisted in `manifest.json`'s `host_permissions`).

For iterative extension UI development without a full rebuild each time, `npm run dev` also works for the popup alone, but the content script and background worker require `npm run build` to take effect in the browser.

---

## Environment variables

**`backend/.env`** (see `backend/.env.example`):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string (async, `postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis connection string (used for response caching) |
| `OPENAI_API_KEY` / `OPENAI_MODEL` / `MAX_COMPLETION_TOKENS` | OpenAI credentials and defaults for the guarded proxy — server-side only, never sent to the browser |
| `JWT_SECRET_KEY` / `JWT_ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES` | Dashboard auth token settings |
| `DEFAULT_MONTHLY_BUDGET_USD` | Default spend cap assigned to new accounts |
| `FRONTEND_ORIGIN` | Allowed CORS origin in production (development allows any localhost port + `chrome-extension://` automatically) |

**`frontend/.env`** (see `frontend/.env.example`):

| Variable | Purpose |
|---|---|
| `VITE_API_BASE` | Backend base URL the dashboard calls |
| `VITE_EXTENSION_ID` | The installed extension's ID, enabling the one-click "Connect extension" flow |

---

## Testing

```bash
cd backend
uv run pytest
```

The suite (`backend/tests/`) covers the guardrail pipeline, budget enforcement, PII policy behavior, security/auth, and a full end-to-end request flow.

---

