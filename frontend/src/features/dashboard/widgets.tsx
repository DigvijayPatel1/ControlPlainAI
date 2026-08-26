import type { ReactNode } from 'react'
import type { RequestRow } from './dashboardApi'

const TONE_TEXT: Record<string, string> = {
    '': 'text-ink',
    green: 'text-brand-green',
    amber: 'text-brand-amber',
    danger: 'text-brand-red',
}

export function Metric({ label, value, tone = '' }: { label: string; value: string | number; tone?: string }) {
    return (
        <div className="rounded-xl border border-line bg-card p-4">
            <span className="block text-xs font-medium tracking-wide text-muted uppercase">{label}</span>
            <strong className={`mt-1 block font-mono text-2xl ${TONE_TEXT[tone] ?? 'text-ink'}`}>{value}</strong>
        </div>
    )
}

export function Panel({ title, children }: { title: string; children: ReactNode }) {
    return (
        <section className="mb-6 rounded-2xl border border-line bg-card p-5">
            <div className="mb-4 flex items-center justify-between">
                <h2 className="text-base font-semibold text-ink">{title}</h2>
                <span className="rounded-full bg-mint px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider text-brand-green uppercase">
                    Live
                </span>
            </div>
            {children}
        </section>
    )
}

export function Empty({ text }: { text: string }) {
    return (
        <div className="rounded-xl border border-dashed border-line py-10 text-center text-sm text-muted">
            {text}
        </div>
    )
}

const VERDICT_STYLES: Record<string, string> = {
    pass: 'bg-mint text-brand-green',
    mask: 'bg-mint text-brand-green',
    review: 'bg-amber-100 text-brand-amber',
    block: 'bg-red-100 text-brand-red',
}

export function RequestTable({ rows }: { rows: RequestRow[] }) {
    if (!rows.length) return <Empty text="No request telemetry yet." />
    return (
        <div className="overflow-x-auto rounded-xl border border-line">
            <table className="w-full border-collapse text-sm">
                <thead>
                    <tr className="border-b border-line bg-paper text-left text-xs tracking-wide text-muted uppercase">
                        <th className="px-4 py-3 font-medium">Time</th>
                        <th className="px-4 py-3 font-medium">Verdict</th>
                        <th className="px-4 py-3 font-medium">Latency</th>
                        <th className="px-4 py-3 font-medium">Cost</th>
                        <th className="px-4 py-3 font-medium">Saved</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row) => (
                        <tr key={row.id} className="border-b border-line last:border-b-0 hover:bg-paper/60">
                            <td className="px-4 py-3 text-ink">{new Date(row.timestamp).toLocaleString()}</td>
                            <td className="px-4 py-3">
                                <span
                                    className={`rounded-full px-2 py-0.5 font-mono text-xs font-semibold uppercase ${
                                        VERDICT_STYLES[row.verdict.toLowerCase()] ?? 'bg-line text-ink'
                                    }`}
                                >
                                    {row.verdict}
                                </span>
                            </td>
                            <td className="px-4 py-3 font-mono text-ink">{row.latency_ms} ms</td>
                            <td className="px-4 py-3 font-mono text-ink">${row.cost_usd.toFixed(4)}</td>
                            <td className="px-4 py-3 font-mono text-muted">{row.tokens_saved ?? 0}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}