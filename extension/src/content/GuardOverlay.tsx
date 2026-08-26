import { useEffect, useState } from 'react'
import { guardBus } from './guardBus'
import type { GuardStatus } from './guardBus'
import { sendNow, setPrompt } from './chatController'
import type { GuardrailCheckResult } from '../lib/api'

const STATUS_META: Record<GuardStatus, { label: string; color: string; icon: string }> = {
    idle: { label: 'ControlPlane', color: '#6b7280', icon: 'CP' },
    checking: { label: 'Checking…', color: '#b7791f', icon: '…' },
    pass: { label: 'Looks safe', color: '#2e7d57', icon: '✓' },
    mask: { label: 'Optimized available', color: '#2e7d57', icon: '✨' },
    review: { label: 'Sent for review', color: '#b7791f', icon: '!' },
    block: { label: 'Blocked', color: '#be5147', icon: '✕' },
    error: { label: "Couldn't check", color: '#be5147', icon: '!' },
}

export default function GuardOverlay() {
    const [status, setStatus] = useState<GuardStatus>('idle')
    const [result, setResult] = useState<GuardrailCheckResult | undefined>()
    const [error, setError] = useState<string | undefined>()
    const [expanded, setExpanded] = useState(false)
    const [optimized, setOptimized] = useState(false)

    useEffect(
        () =>
            guardBus.subscribe((event) => {
                setStatus(event.status)
                setResult(event.result)
                setError(event.error)
                setOptimized(false)
                // Auto-expand whenever there's something worth looking at;
                // stay quiet (badge only) once it's a plain pass with no savings.
                setExpanded(event.status !== 'idle' && event.status !== 'checking')
            }),
        [],
    )

    const meta = STATUS_META[status]
    const showActions = status === 'pass' || status === 'mask'
    const hasSavings = Boolean(result && result.tokens_saved > 0)

    function handleOptimize() {
        if (result?.optimized_content && setPrompt(result.optimized_content)) {
            setOptimized(true)
        }
    }

    function handleSend() {
        setExpanded(false)
        sendNow()
    }

    function handleDismiss() {
        setExpanded(false)
    }

    return (
        <div className="cp-root">
            <style>{CSS}</style>

            <button
                className="cp-badge"
                style={{ background: meta.color }}
                onClick={() => setExpanded((v) => !v)}
                title="ControlPlane AI"
            >
                <span className={status === 'checking' ? 'cp-spin' : ''}>{meta.icon}</span>
            </button>

            {expanded && (
                <div className="cp-card">
                    <div className="cp-card-head">
                        <span className="cp-dot" style={{ background: meta.color }} />
                        <strong>{meta.label}</strong>
                        <button className="cp-close" onClick={handleDismiss} aria-label="Dismiss">×</button>
                    </div>

                    {status === 'error' && <p className="cp-muted">{error}</p>}

                    {status === 'block' && (
                        <ul className="cp-reasons">
                            {(result?.reasons ?? ['This message was blocked by your guardrail policy.']).map((reason) => (
                                <li key={reason}>{reason}</li>
                            ))}
                        </ul>
                    )}

                    {status === 'review' && (
                        <p className="cp-muted">
                            This message needs a human reviewer's sign-off before it's sent. You'll be notified once
                            it's resolved.
                        </p>
                    )}

                    {result && (status === 'pass' || status === 'mask') && (
                        <div className="cp-stats">
                            <div>
                                <span>Tokens</span>
                                <strong>{result.original_tokens}</strong>
                            </div>
                            <div>
                                <span>Est. cost</span>
                                <strong>${result.estimated_cost_usd.toFixed(6)}</strong>
                            </div>
                            {hasSavings && (
                                <div>
                                    <span>Could save</span>
                                    <strong>{result.tokens_saved} tokens</strong>
                                </div>
                            )}
                        </div>
                    )}

                    {showActions && (
                        <div className="cp-actions">
                            {hasSavings && !optimized && (
                                <button className="cp-btn cp-btn-ghost" onClick={handleOptimize}>
                                    ✨ Optimize &amp; keep editing
                                </button>
                            )}
                            <button className="cp-btn cp-btn-primary" onClick={handleSend}>
                                {optimized ? 'Send optimized' : 'Send anyway'}
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

const CSS = `
.cp-root { font-family: 'DM Sans', system-ui, sans-serif; }
.cp-badge {
    position: fixed; right: 20px; bottom: 110px; z-index: 2147483647;
    width: 44px; height: 44px; border-radius: 50%; border: none; color: #fff;
    font-weight: 700; font-size: 15px; cursor: pointer;
    box-shadow: 0 4px 16px rgba(0,0,0,.28); display: grid; place-items: center;
    transition: transform .15s ease;
}
.cp-badge:hover { transform: scale(1.08); }
.cp-spin { display: inline-block; animation: cp-pulse 1s ease-in-out infinite; }
@keyframes cp-pulse { 0%,100% { opacity: .5 } 50% { opacity: 1 } }
.cp-card {
    position: fixed; right: 20px; bottom: 164px; z-index: 2147483647;
    width: 300px; background: #fff; color: #17211b; border-radius: 14px;
    box-shadow: 0 12px 40px rgba(0,0,0,.25); padding: 16px; font-size: 13px;
}
.cp-card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.cp-card-head strong { flex: 1; font-size: 14px; }
.cp-dot { width: 8px; height: 8px; border-radius: 50%; }
.cp-close { border: none; background: none; font-size: 18px; line-height: 1; cursor: pointer; color: #718078; }
.cp-muted { color: #718078; margin: 0 0 8px; }
.cp-reasons { margin: 0 0 8px; padding-left: 18px; color: #be5147; }
.cp-stats { display: flex; gap: 10px; margin-bottom: 12px; }
.cp-stats > div { flex: 1; background: #f4f7f1; border-radius: 8px; padding: 8px; }
.cp-stats span { display: block; font-size: 11px; color: #718078; }
.cp-stats strong { font-size: 13px; }
.cp-actions { display: flex; flex-direction: column; gap: 8px; }
.cp-btn { border: none; border-radius: 8px; padding: 9px 12px; font-weight: 600; cursor: pointer; font-size: 13px; }
.cp-btn-primary { background: #1d2a22; color: #fff; }
.cp-btn-ghost { background: #eef4ec; color: #1d2a22; }
`
