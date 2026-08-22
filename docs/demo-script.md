# ControlPlane AI — Demo Script

Target length: 3-4 minutes live demo + 1-2 minutes architecture walkthrough. Have the backup video ready in case wifi/live-model calls fail.

## 0. Setup (before judges arrive)
- Seed the demo-session database with clean sample history so the dashboard doesn't look empty on first load
- Confirm both entry points work: a direct API call and the browser extension on the demo chatbot page
- Have the pitch deck open to the architecture slide as your starting screen, not a terminal

## 1. Hook (15 seconds)
State the problem in one line: enterprises can't trust raw LLM output at speed, and checking after the fact is too slow. ControlPlane AI checks it in real time, before it ever reaches the user.

## 2. Clean request — show the fast path (30 seconds)
- Send an ordinary, safe query through the direct API client
- Point out: verdict = Allow, latency shown on screen, request appears instantly in the Live Feed
- Message: "most traffic never touches a human — it just passes through, fast."

## 3. PII leak — show auto-correction (30 seconds)
- Send a prompt/response pair that would leak a name, email, or phone number
- Show the response coming back redacted, verdict = Mask
- Point to the dashboard entry showing what was masked and why

## 4. Off-topic / hallucinated response — show block (30 seconds)
- Send a query designed to trigger drift or an ungrounded claim
- Show verdict = Block, and the replacement message the user actually receives instead
- Message: "the user never sees the bad output — they see a safe fallback."

## 5. High-risk case — human-in-the-loop (45 seconds)
- Send a query that lands in the "uncertain" zone (ambiguous risk score)
- Show it landing in the Review Queue in real time (WebSocket update)
- Switch to the admin view, approve/edit/override the flagged response live
- Message: "the system knows what it doesn't know, and escalates instead of guessing."

## 6. Extension entry point (30 seconds)
- Switch to the browser extension running on the demo customer-support chatbot
- Send a message through the actual chatbot UI, not the API directly
- Show the same event appearing in the same Live Feed — proving both entry points share one pipeline
- Mention: enrollment was authenticated via Entra ID, so this is tied to a managed identity, not an anonymous script

## 7. Cost & routing (30 seconds)
- Show the Analytics view: tokens used, cost saved by routing simple queries to the smaller model, cache hit rate
- Send a repeated query to show the semantic cache firing (near-instant response, $0 marginal cost)

## 8. Security Centre / red-team scan (20 seconds)
- Show the risk-finding history and the offline Garak/DeepTeam scan report
- Message: "this isn't just reactive — we proactively test the chatbot for vulnerabilities before it ever goes live."

## 9. Close (20 seconds)
- One-line recap: real-time, both entry points, five possible outcomes, auditable, and it adds negligible latency
- Point to the roadmap slide for Phase 3 (Prometheus/Grafana, OpenTelemetry, hierarchical budgets) as "where this goes next," so judges see production maturity was considered even where you didn't have a week to build it

## Fallback plan
If a live LLM call fails or wifi drops: switch immediately to the recorded backup video, narrate over it exactly as above. Don't apologize at length — acknowledge briefly and move on.