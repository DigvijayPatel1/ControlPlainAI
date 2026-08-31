import { useEffect, useState } from 'react';
import { guardBus } from './guardBus';
import { getState, onStateChanged } from '../lib/storage';

const NOT_CONNECTED_MARKERS = ['ControlPlane API key is not configured', 'API key is disabled', 'API key has expired'];

const STATUS_META = {
    idle: { label: 'ControlPlane', icon: 'CP', badge: 'bg-white/40', dot: 'bg-white/40' },
    checking: { label: 'Checking…', icon: '…', badge: 'bg-brand-amber', dot: 'bg-brand-amber' },
    pass: { label: 'Sent — looks safe', icon: '✓', badge: 'bg-brand-green', dot: 'bg-brand-green' },
    mask: { label: 'Sent — sensitive info redacted', icon: '✨', badge: 'bg-brand-amber', dot: 'bg-brand-amber' },
    review: { label: 'Sent for review', icon: '!', badge: 'bg-brand-amber', dot: 'bg-brand-amber' },
    block: { label: 'Blocked', icon: '✕', badge: 'bg-brand-red', dot: 'bg-brand-red' },
    error: { label: "Couldn't check", icon: '!', badge: 'bg-brand-red', dot: 'bg-brand-red' },
    'checking-response': { label: 'Checking response…', icon: '…', badge: 'bg-brand-amber', dot: 'bg-brand-amber' },
    'response-pass': { label: 'Response looks safe', icon: '✓', badge: 'bg-brand-green', dot: 'bg-brand-green' },
    'response-mask': { label: 'Response redacted', icon: '✨', badge: 'bg-brand-amber', dot: 'bg-brand-amber' },
    'response-review': { label: 'Response flagged for review', icon: '!', badge: 'bg-brand-amber', dot: 'bg-brand-amber' },
    'response-block': { label: 'Response blocked', icon: '✕', badge: 'bg-brand-red', dot: 'bg-brand-red' },
    'response-error': { label: "Couldn't check response", icon: '!', badge: 'bg-brand-red', dot: 'bg-brand-red' },
};
const CHECKING_STATUSES = new Set(['checking', 'checking-response']);

export default function GuardOverlay() {
    const [status, setStatus] = useState('idle');
    const [result, setResult] = useState();
    const [error, setError] = useState();
    const [expanded, setExpanded] = useState(false);
    const [optimizationEnabled, setOptimizationEnabled] = useState(true);
    const [showTokens, setShowTokens] = useState(true);
    const [notConnected, setNotConnected] = useState(false);

    useEffect(() => guardBus.subscribe((event) => {
        setStatus(event.status);
        setResult(event.result);
        setError(event.error);

        const looksLikeNotConnected = Boolean(
            event.error && NOT_CONNECTED_MARKERS.some((marker) => event.error.includes(marker))
        );
        setNotConnected(looksLikeNotConnected);
        // Not-connected is shown as a persistent banner, not an auto-collapsing
        // popover — this was previously a tiny corner dot the user had every
        // reason to miss, which made "nothing is happening" look identical to
        // "everything is fine." The same reasoning applies to 'error' below:
        // it's a stop-and-explain state (the redaction-verification failure
        // in chatController.js lands here too), so it stays open until
        // dismissed rather than fading on its own.
        //
        // 'pass' and 'mask' both auto-send now (see chatController.js), so
        // neither needs to hold the panel open waiting for a click — they
        // get a brief confirmation instead, handled by the auto-dismiss
        // timer below. All prompt mutation (redaction + verification) is
        // chatController.js's responsibility alone — this component only
        // displays the resulting status, it never touches the page's DOM.
        const isAutoSent = event.status === 'pass' || event.status === 'mask';
        setExpanded(looksLikeNotConnected || (event.status !== 'idle' && !CHECKING_STATUSES.has(event.status) && !isAutoSent));

        if (isAutoSent) {
            setExpanded(true);
            const timer = setTimeout(() => setExpanded(false), 4000);
            return () => clearTimeout(timer);
        }
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
    const hasSavings = Boolean(result && result.tokens_saved > 0);
    function openDashboard() {
        chrome.runtime.sendMessage({ type: 'OPEN_DASHBOARD' });
    }
    return (<div className="font-sans">
            <button type="button" onClick={() => setExpanded((v) => !v)} title="ControlPlane AI" className={`fixed right-5 bottom-28 z-[2147483647] grid h-11 w-11 place-items-center rounded-full text-sm font-bold text-white shadow-lg shadow-black/25 transition-transform hover:scale-105 ${notConnected ? 'bg-brand-red animate-pulse' : meta.badge}`}>
                <span className={CHECKING_STATUSES.has(status) ? 'animate-pulse' : ''}>{notConnected ? '!' : meta.icon}</span>
            </button>

            {expanded && notConnected && (<div className="fixed right-5 bottom-42 z-[2147483647] w-75 rounded-2xl border border-brand-red bg-card p-4 text-sm text-ink shadow-2xl shadow-black/30">
                    <div className="mb-2 flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-brand-red"/>
                        <strong className="flex-1 text-sm">ControlPlane isn't connected</strong>
                    </div>
                    <p className="mb-3 text-muted">
                        Messages are being held, not sent, until this extension is connected to your account.
                        Connect it from the dashboard to resume sending.
                    </p>
                    <button type="button" onClick={openDashboard} className="w-full rounded-lg bg-sidebar px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-sidebar/90">
                        Open dashboard to connect
                    </button>
                </div>)}

            {expanded && !notConnected && (<div className="fixed right-5 bottom-42 z-[2147483647] w-75 rounded-2xl border border-line bg-card p-4 text-sm text-ink shadow-2xl shadow-black/30">
                    <div className="mb-2 flex items-center gap-2">
                        <span className={`h-2 w-2 rounded-full ${meta.dot}`}/>
                        <strong className="flex-1 text-sm">{meta.label}</strong>
                        <button type="button" onClick={() => setExpanded(false)} aria-label="Dismiss" className="text-lg leading-none text-muted hover:text-ink">
                            ×
                        </button>
                    </div>

                    {status === 'error' && <p className="mb-2 text-muted">{error}</p>}
                    {status === 'response-error' && <p className="mb-2 text-muted">{error}</p>}

                    {status === 'block' && (<ul className="mb-2 list-disc space-y-1 pl-4 text-brand-red">
                            {(result?.reasons ?? ['This message was blocked by your guardrail policy.']).map((reason) => (<li key={reason}>{reason}</li>))}
                        </ul>)}

                    {status === 'response-block' && (<ul className="mb-2 list-disc space-y-1 pl-4 text-brand-red">
                            {(result?.reasons ?? ['This response was blocked by your guardrail policy.']).map((reason) => (<li key={reason}>{reason}</li>))}
                        </ul>)}

                    {status === 'review' && (<p className="mb-2 text-muted">
                            This message needs a human reviewer's sign-off before it's sent. You'll be notified once
                            it's resolved.
                        </p>)}

                    {status === 'response-review' && (<p className="mb-2 text-muted">
                            This response has been flagged and sent for human review.
                        </p>)}

                    {status === 'response-mask' && (<p className="mb-2 text-muted">
                            Sensitive information in the response was automatically redacted.
                        </p>)}

                    {status === 'response-pass' && (<p className="mb-2 text-muted">
                            This response passed all guardrail checks.
                        </p>)}

                    {status === 'mask' && (<p className="mb-2 text-muted">
                            Sensitive information was found, redacted, and the message was sent.
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
                </div>)}
        </div>);
}