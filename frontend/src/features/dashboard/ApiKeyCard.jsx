import { useState } from 'react';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import { apiKeyAcknowledged } from '../auth/authSlice';
import { connectExtension, isExtensionConfigured } from '../../lib/extension';
export default function ApiKeyCard() {
    const dispatch = useAppDispatch();
    const pendingApiKey = useAppSelector((state) => state.auth.pendingApiKey);
    const [connectState, setConnectState] = useState('idle');
    const [reveal, setReveal] = useState(false);
    if (!pendingApiKey)
        return null;
    async function handleConnect() {
        setConnectState('connecting');
        const result = await connectExtension(pendingApiKey.raw_key, pendingApiKey.principal_id);
        setConnectState(result.ok ? 'connected' : 'failed');
    }
    return (<div className="rounded-2xl border border-brand-amber/30 bg-amber-50/60 p-5">
            <div className="mb-3 flex items-center justify-between">
                <h2 className="text-base font-semibold text-ink">Your ControlPlane API key</h2>
                <span className="rounded-full bg-brand-amber/15 px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider text-brand-amber uppercase">
                    Shown once
                </span>
            </div>
            <p className="mb-4 text-sm text-muted">
                This key authenticates the browser extension as you. It's shown only now — store it somewhere
                safe, or connect the extension directly below.
            </p>

            <code className="mb-4 block break-all rounded-lg border border-line bg-card px-3 py-3 font-mono text-sm text-ink">
                {reveal ? pendingApiKey.raw_key : '•'.repeat(40)}
            </code>

            <div className="flex flex-wrap items-center gap-3">
                <button type="button" onClick={() => setReveal((v) => !v)} className="rounded-lg border border-line px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-white">
                    {reveal ? 'Hide key' : 'Reveal key'}
                </button>

                {isExtensionConfigured() ? (<button type="button" onClick={handleConnect} disabled={connectState === 'connecting'} className="rounded-lg bg-brand-green px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-green/90 disabled:opacity-60">
                        {connectState === 'connected' ? 'Connected ✓' : connectState === 'connecting' ? 'Connecting…' : 'Connect extension'}
                    </button>) : (<span className="text-sm text-muted">Set VITE_EXTENSION_ID to enable one-click connect.</span>)}

                <button type="button" onClick={() => dispatch(apiKeyAcknowledged())} className="rounded-lg px-4 py-2 text-sm font-medium text-muted transition-colors hover:bg-white/60">
                    I've saved it, dismiss
                </button>
            </div>

            {connectState === 'failed' && (<p className="mt-3 rounded-lg border border-brand-red/30 bg-red-50 px-3 py-2 text-sm text-brand-red">
                    Couldn't reach the extension automatically. Paste the key into the extension popup instead.
                </p>)}
        </div>);
}
