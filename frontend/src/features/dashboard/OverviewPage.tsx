import { useSummaryQuery, useRequestsQuery } from './dashboardApi'
import ApiKeyCard from './ApiKeyCard'
import { Metric, Panel, RequestTable } from './widgets'

export default function OverviewPage() {
    const { data: summary, error: summaryError } = useSummaryQuery()
    const { data: requests } = useRequestsQuery({ limit: 5 })

    const data = summary ?? {
        total_requests: 0,
        blocked_requests: 0,
        review_requests: 0,
        total_cost_usd: 0,
        cost_saved_usd: 0,
        tokens_saved: 0,
        cache_hits: 0,
        cache_hit_rate: 0,
        avg_latency_ms: 0,
    }

    return (
        <>
            <header className="topbar">
                <div>
                    <p className="eyebrow">SECURITY CENTRE / 01</p>
                    <h1>Overview</h1>
                    <p className="muted">Guardrails, spend, and review operations in one quiet place.</p>
                </div>
            </header>

            {summaryError && <div className="notice">Couldn't load analytics yet — send a few requests through the guardrail API first.</div>}

            <ApiKeyCard />

            <div className="metrics">
                <Metric label="Requests" value={data.total_requests} />
                <Metric label="Blocked" value={data.blocked_requests} tone="danger" />
                <Metric label="Pending reviews" value={data.review_requests} tone="amber" />
                <Metric label="Total cost" value={`$${data.total_cost_usd.toFixed(4)}`} />
            </div>

            <div className="grid-two">
                <Panel title="Efficiency">
                    <div className="efficiency">
                        <Metric label="Tokens saved" value={data.tokens_saved} />
                        <Metric label="Cache hit rate" value={`${(data.cache_hit_rate * 100).toFixed(1)}%`} />
                        <Metric label="Avg latency" value={`${Math.round(data.avg_latency_ms)} ms`} />
                    </div>
                </Panel>
                <Panel title="Spend">
                    <div className="efficiency">
                        <Metric label="Prompt savings" value={`$${data.cost_saved_usd.toFixed(4)}`} tone="green" />
                        <Metric label="Cache hits" value={data.cache_hits} />
                    </div>
                </Panel>
            </div>

            <Panel title="Latest activity">
                <RequestTable rows={requests ?? []} />
            </Panel>
        </>
    )
}