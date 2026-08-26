import { useEffect, useState } from 'react';
import { guardBus } from './guardBus';
import { sendNow, setPrompt } from './chatController';
import { getState, onStateChanged } from '../lib/storage';
const STATUS_META = {
    idle: { label: 'ControlPlane', icon: 'CP', badge: 'bg-white/40', dot: 'bg-white/40' },
    checking: { label: 'Checking…', icon: '…', badge: 'bg-brand-amber', dot: 'bg-brand-amber' },
    pass: { label: 'Looks safe', icon: '✓', badge: 'bg-brand-green', dot: 'bg-brand-green' },
    mask: { label: 'Optimized available', icon: '✨', badge: 'bg-brand-green', dot: 'bg-brand-green' },
    review: { label: 'Sent for review', icon: '!', badge: 'bg-brand-amber', dot: 'bg-brand-amber' },
    block: { label: 'Blocked', icon: '✕', badge: 'bg-brand-red', dot: 'bg-brand-red' },
    error: { label: "Couldn't check", icon: '!', badge: 'bg-brand-red', dot: 'bg-brand-red' },
};
export default function GuardOverlay() {
    const [status, setStatus] = useState('idle');
    const [result, setResult] = useState();
    const [error, setError] = useState();
    const [expanded, setExpanded] = useState(false);
    const [optimized, setOptimized] = useState(false);
    const [optimizationEnabled, setOptimizationEnabled] = useState(true);
    const [showTokens, setShowTokens] = useState(true);
    useEffect(() => guardBus.subscribe((event) => {
        setStatus(event.status);
        setResult(event.result);
        setError(event.error);
        setOptimized(false);
        setExpanded(event.status !== 'idle' && event.status !== 'checking');
    }), []);
    useEffect(() => {
        const applyState = (state) => {
            setOptimizationEnabled(state.optimizationEnabled);
            setShowTokens(state.showTokens);
        };
        getState().then(applyState);
        return onStateChanged(applyState);
    }, []);
    const meta = STATUS_META[status];
    const showActions = status === 'pass' || status === 'mask';
    const hasSavings = Boolean(result && result.tokens_saved > 0);
    const canOptimize = optimizationEnabled && hasSavings;
    function handleOptimize() {
        if (result?.optimized_content && setPrompt(result.optimized_content)) {
            setOptimized(true);
        }
    }
    function handleSend() {
        setExpanded(false);
        sendNow();
    }
    return (<div className="font-sans">
            <button type="button" onClick={() => setExpanded((v) => !v)} title="ControlPlane AI" className={`fixed right-5 bottom-28 z-[2147483647] grid h-11 w-11 place-items-center rounded-full text-sm font-bold text-white shadow-lg shadow-black/25 transition-transform hover:scale-105 ${meta.badge}`}>
                <span className={status === 'checking' ? 'animate-pulse' : ''}>{meta.icon}</span>
            </button>

            {expanded && (<div className="fixed right-5 bottom-42 z-[2147483647] w-75 rounded-2xl border border-line bg-card p-4 text-sm text-ink shadow-2xl shadow-black/30">
                    <div className="mb-2 flex items-center gap-2">
                        <span className={`h-2 w-2 rounded-full ${meta.dot}`}/>
                        <strong className="flex-1 text-sm">{meta.label}</strong>
                        <button type="button" onClick={() => setExpanded(false)} aria-label="Dismiss" className="text-lg leading-none text-muted hover:text-ink">
                            ×
                        </button>
                    </div>

                    {status === 'error' && <p className="mb-2 text-muted">{error}</p>}

                    {status === 'block' && (<ul className="mb-2 list-disc space-y-1 pl-4 text-brand-red">
                            {(result?.reasons ?? ['This message was blocked by your guardrail policy.']).map((reason) => (<li key={reason}>{reason}</li>))}
                        </ul>)}

                    {status === 'review' && (<p className="mb-2 text-muted">
                            This message needs a human reviewer's sign-off before it's sent. You'll be notified once
                            it's resolved.
                        </p>)}

                    {result && (status === 'pass' || status === 'mask') && (<div className="mb-3 flex gap-2">
                            <div className="flex-1 rounded-lg bg-paper p-2">
                                <span className="block text-[11px] text-muted">Tokens</span>
                                <strong className="text-sm">{result.original_tokens}</strong>
                            </div>
                            <div className="flex-1 rounded-lg bg-paper p-2">
                                <span className="block text-[11px] text-muted">Est. cost</span>
                                <strong className="text-sm">${result.estimated_cost_usd.toFixed(6)}</strong>
                            </div>
                            {showTokens && hasSavings && (<div className="flex-1 rounded-lg bg-paper p-2">
                                    <span className="block text-[11px] text-muted">Could save</span>
                                    <strong className="text-sm">{result.tokens_saved} tok</strong>
                                </div>)}
                        </div>)}

                    {showActions && (<div className="flex flex-col gap-2">
                            {canOptimize && !optimized && (<button type="button" onClick={handleOptimize} className="rounded-lg bg-mint px-3 py-2 text-sm font-semibold text-brand-green transition-colors hover:bg-mint/80">
                                    ✨ Optimize &amp; keep editing
                                </button>)}
                            <button type="button" onClick={handleSend} className="rounded-lg bg-sidebar px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-sidebar/90">
                                {optimized ? 'Send optimized' : 'Send anyway'}
                            </button>
                        </div>)}
                </div>)}
        </div>);
}
