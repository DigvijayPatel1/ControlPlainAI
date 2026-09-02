import { useRequestsQuery } from './dashboardApi';
import { Panel, RequestTable } from './widgets';
export default function RequestsPage() {
    const { data, isLoading, error } = useRequestsQuery({ limit: 100 });
    return (<>
            <header className="mb-6">
                <p className="font-mono text-xs tracking-widest text-muted uppercase">Security centre / 02</p>
                <h1 className="mt-1 text-2xl font-semibold text-ink">Requests</h1>
                <p className="mt-1 text-sm text-muted">Full guarded request history for your account.</p>
            </header>

            {error && (<div className="mb-6 rounded-xl border border-brand-red/30 bg-red-50 px-4 py-3 text-sm text-brand-red">
                    Couldn't load request history.
                </div>)}

            <Panel title="Request history">
                {isLoading ? <p className="text-sm text-muted">Loading…</p> : <RequestTable rows={data ?? []}/>}
            </Panel>
        </>);
}
