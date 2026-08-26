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
            <header className="mb-6">
                <p className="font-mono text-xs tracking-widest text-muted uppercase">Security centre / 01</p>
                <h1 className="mt-1 text-2xl font-semibold text-ink">Overview</h1>
                <p className="mt-1 text-sm text-muted">Guardrails, spend, and review operations in one quiet place.</p>
            </header>

            {summaryError && (
                <div className="mb-6 rounded-xl border border-brand-amber/30 bg-amber-50 px-4 py-3 text-sm text-brand-amber">
                    Couldn't load analytics yet — send a few requests through the guardrail API first.
                </div>
            )}

            <div className="mb-6">
                <ApiKeyCard />
            </div>

            <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
                <Metric label="Requests" value={data.total_requests} />
                <Metric label="Blocked" value={data.blocked_requests} tone="danger" />
                <Metric label="Pending reviews" value={data.review_requests} tone="amber" />
                <Metric label="Total cost" value={`$${data.total_cost_usd.toFixed(4)}`} />
            </div>

            <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
                <Panel title="Efficiency">
                    <div className="grid grid-cols-3 gap-3">
                        <Metric label="Tokens saved" value={data.tokens_saved} />
                        <Metric label="Cache hit rate" value={`${(data.cache_hit_rate * 100).toFixed(1)}%`} />
                        <Metric label="Avg latency" value={`${Math.round(data.avg_latency_ms)} ms`} />
                    </div>
                </Panel>
                <Panel title="Spend">
                    <div className="grid grid-cols-2 gap-3">
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