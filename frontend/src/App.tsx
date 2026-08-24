import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import './App.css'

type Section = 'overview' | 'requests' | 'safety' | 'cost' | 'tokens' | 'reviews' | 'cache' | 'settings'
type Summary = { total_requests: number; blocked_requests: number; review_requests: number; total_cost_usd: number; cost_saved_usd: number; tokens_saved: number; cache_hits: number; cache_hit_rate: number; avg_latency_ms: number }
type RequestRow = { id: string; timestamp: string; verdict: string; risk_score?: number; latency_ms: number; cost_usd: number; tokens_saved: number }
type Review = { review_id: string; prompt: string; proposed_response: string; flagged_reason: string; risk_score: number; created_at: string }

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'
const sections: Section[] = ['overview', 'requests', 'safety', 'cost', 'tokens', 'reviews', 'cache', 'settings']
const money = (value: number) => `$${value.toFixed(4)}`

function App() {
    const [section, setSection] = useState<Section>('overview')
    const [summary, setSummary] = useState<Summary | null>(null)
    const [requests, setRequests] = useState<RequestRow[]>([])
    const [reviews, setReviews] = useState<Review[]>([])
    const [apiKey, setApiKey] = useState(localStorage.getItem('controlplane_api_key') ?? '')
    const [connected, setConnected] = useState(false)
    const [enabled, setEnabled] = useState(localStorage.getItem('controlplane_enabled') !== 'false')
    const [optimization, setOptimization] = useState(localStorage.getItem('controlplane_optimization') !== 'false')
    const [error, setError] = useState('')

    async function api(path: string) {
        const response = await fetch(`${API_BASE}${path}`, { headers: apiKey ? { 'X-API-Key': apiKey } : {} })
        if (!response.ok) throw new Error(`API request failed (${response.status})`)
        return response.json()
    }

    async function loadData() {
        try {
            setError('')
            const [nextSummary, nextRequests, nextReviews] = await Promise.all([api('/v1/analytics/summary'), api('/v1/analytics/requests'), api('/v1/admin/reviews')])
            setSummary(nextSummary)
            setRequests(nextRequests)
            setReviews(nextReviews)
        } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to load backend data') }
    }

    useEffect(() => { if (apiKey) void loadData() }, [apiKey])
    useEffect(() => {
        const socket = new WebSocket(`${API_BASE.replace(/^http/, 'ws')}/ws/controlplane`)
        socket.onopen = () => setConnected(true)
        socket.onclose = () => setConnected(false)
        socket.onmessage = () => { void loadData() }
        return () => socket.close()
    }, [])

    const data = summary ?? { total_requests: 0, blocked_requests: 0, review_requests: 0, total_cost_usd: 0, cost_saved_usd: 0, tokens_saved: 0, cache_hits: 0, cache_hit_rate: 0, avg_latency_ms: 0 }
    const title = section[0].toUpperCase() + section.slice(1)

    return <div className="shell">
        <aside className="sidebar"><div className="brand"><span className="brand-mark">CP</span><div><strong>ControlPlane</strong><small>AI governance</small></div></div><nav>{sections.map(item => <button key={item} className={section === item ? 'nav active' : 'nav'} onClick={() => setSection(item)}>{item}</button>)}</nav><div className="side-foot"><span className={connected ? 'pulse online' : 'pulse'} />{connected ? 'Live connection' : 'Offline mode'}</div></aside>
        <main className="main"><header className="topbar"><div><p className="eyebrow">SECURITY CENTRE / 01</p><h1>{title}</h1><p className="muted">Guardrails, spend, and review operations in one quiet place.</p></div><button className={enabled ? 'status on' : 'status'} onClick={() => { const next = !enabled; setEnabled(next); localStorage.setItem('controlplane_enabled', String(next)) }}><span />Protection {enabled ? 'ON' : 'OFF'}</button></header>
            {error && <div className="notice">{error}. Add an API key in Settings to connect.</div>}
            {section === 'overview' && <><div className="metrics"><Metric label="Requests" value={data.total_requests} /><Metric label="Blocked" value={data.blocked_requests} tone="danger" /><Metric label="Pending reviews" value={data.review_requests} tone="amber" /><Metric label="Total cost" value={money(data.total_cost_usd)} /></div><div className="grid-two"><Panel title="Current posture"><div className="posture"><span className="shield">✓</span><div><strong>{enabled ? 'Protected and observing' : 'Protection paused'}</strong><p className="muted">{connected ? 'Backend telemetry is live.' : 'Connect the backend to stream telemetry.'}</p></div></div></Panel><Panel title="Efficiency"><div className="efficiency"><Metric label="Tokens saved" value={data.tokens_saved} /><Metric label="Cache hit rate" value={`${(data.cache_hit_rate * 100).toFixed(1)}%`} /><Metric label="Avg latency" value={`${Math.round(data.avg_latency_ms)} ms`} /></div></Panel></div><Panel title="Latest activity"><RequestTable rows={requests.slice(0, 5)} /></Panel></>}
            {section === 'requests' && <Panel title="Request history"><RequestTable rows={requests} /></Panel>}
            {section === 'reviews' && <Panel title="Human review queue"><div className="review-list">{reviews.length ? reviews.map(review => <article className="review" key={review.review_id}><div className="review-head"><span className="badge amber">Risk {review.risk_score.toFixed(2)}</span><time>{new Date(review.created_at).toLocaleString()}</time></div><p>{review.flagged_reason}</p><blockquote>{review.proposed_response}</blockquote><button className="outline">Open review {review.review_id.slice(0, 8)}</button></article>) : <Empty text="No pending reviews." />}</div></Panel>}
            {section === 'safety' && <CheckGrid />}
            {section === 'cost' && <div className="metrics"><Metric label="Total spend" value={money(data.total_cost_usd)} /><Metric label="Prompt savings" value={money(data.cost_saved_usd)} tone="green" /><Metric label="Cache hits" value={data.cache_hits} /></div>}
            {section === 'tokens' && <div className="metrics"><Metric label="Tokens saved" value={data.tokens_saved} tone="green" /><Metric label="Optimization" value={optimization ? 'Enabled' : 'Paused'} /><Metric label="Avg per request" value={data.total_requests ? Math.round(data.tokens_saved / data.total_requests) : 0} /></div>}
            {section === 'cache' && <Panel title="Cache telemetry"><div className="cache-hero"><strong>{(data.cache_hit_rate * 100).toFixed(1)}%</strong><span>hit rate</span></div><p className="muted">{data.cache_hits} safe responses served without a provider call.</p></Panel>}
            {section === 'settings' && <Panel title="Workspace settings"><label className="setting"><span>Backend API key<small>Stored locally in this browser.</small></span><input type="password" value={apiKey} onChange={event => setApiKey(event.target.value)} onBlur={() => { localStorage.setItem('controlplane_api_key', apiKey); void loadData() }} placeholder="cpai_..." /></label><label className="setting"><span>Protection<small>Backend enforcement remains authoritative.</small></span><input type="checkbox" checked={enabled} onChange={event => { setEnabled(event.target.checked); localStorage.setItem('controlplane_enabled', String(event.target.checked)) }} /></label><label className="setting"><span>Prompt optimization<small>Remove only conservative redundant wording.</small></span><input type="checkbox" checked={optimization} onChange={event => { setOptimization(event.target.checked); localStorage.setItem('controlplane_optimization', String(event.target.checked)) }} /></label></Panel>}
        </main></div>
}

function Metric({ label, value, tone = '' }: { label: string; value: string | number; tone?: string }) { return <div className={`metric ${tone}`}><span>{label}</span><strong>{value}</strong></div> }
function Panel({ title, children }: { title: string; children: ReactNode }) { return <section className="panel"><div className="panel-title"><h2>{title}</h2><span>LIVE</span></div>{children}</section> }
function Empty({ text }: { text: string }) { return <div className="empty">{text}</div> }
function RequestTable({ rows }: { rows: RequestRow[] }) { return rows.length ? <div className="table-wrap"><table><thead><tr><th>Time</th><th>Verdict</th><th>Risk</th><th>Latency</th><th>Cost</th><th>Saved</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td>{new Date(row.timestamp).toLocaleString()}</td><td><span className={`badge ${row.verdict.toLowerCase()}`}>{row.verdict}</span></td><td>{row.risk_score?.toFixed(2) ?? '-'}</td><td>{row.latency_ms} ms</td><td>{money(row.cost_usd)}</td><td>{row.tokens_saved ?? 0}</td></tr>)}</tbody></table></div> : <Empty text="No request telemetry yet." /> }
function CheckGrid() { return <div className="check-grid">{['PII', 'Policy', 'Toxicity', 'Bias', 'Grounding', 'Drift', 'Format'].map(check => <div className="check" key={check}><span>✓</span><strong>{check}</strong><small>monitored</small></div>)}</div> }

export default App
