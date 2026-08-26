import { useRequestsQuery } from './dashboardApi'
import { Panel, RequestTable } from './widgets'

export default function RequestsPage() {
    const { data, isLoading, error } = useRequestsQuery({ limit: 100 })

    return (
        <>
            <header className="topbar">
                <div>
                    <p className="eyebrow">SECURITY CENTRE / 02</p>
                    <h1>Requests</h1>
                    <p className="muted">Full guarded request history for your account.</p>
                </div>
            </header>
            {error && <div className="notice">Couldn't load request history.</div>}
            <Panel title="Request history">
                {isLoading ? <p className="muted">Loading…</p> : <RequestTable rows={data ?? []} />}
            </Panel>
        </>
    )
}