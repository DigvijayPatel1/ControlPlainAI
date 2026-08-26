import type { ReactNode } from 'react'
import type { RequestRow } from './dashboardApi'

export function Metric({ label, value, tone = '' }: { label: string; value: string | number; tone?: string }) {
    return (
        <div className={`metric ${tone}`}>
            <span>{label}</span>
            <strong>{value}</strong>
        </div>
    )
}

export function Panel({ title, children }: { title: string; children: ReactNode }) {
    return (
        <section className="panel">
            <div className="panel-title"><h2>{title}</h2><span>LIVE</span></div>
            {children}
        </section>
    )
}

export function Empty({ text }: { text: string }) {
    return <div className="empty">{text}</div>
}

export function RequestTable({ rows }: { rows: RequestRow[] }) {
    if (!rows.length) return <Empty text="No request telemetry yet." />
    return (
        <div className="table-wrap">
            <table>
                <thead>
                    <tr><th>Time</th><th>Verdict</th><th>Latency</th><th>Cost</th><th>Saved</th></tr>
                </thead>
                <tbody>
                    {rows.map((row) => (
                        <tr key={row.id}>
                            <td>{new Date(row.timestamp).toLocaleString()}</td>
                            <td><span className={`badge ${row.verdict.toLowerCase()}`}>{row.verdict}</span></td>
                            <td>{row.latency_ms} ms</td>
                            <td>${row.cost_usd.toFixed(4)}</td>
                            <td>{row.tokens_saved ?? 0}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}