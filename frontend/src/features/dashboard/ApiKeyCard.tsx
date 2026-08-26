import { useState } from 'react'
import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { apiKeyAcknowledged } from '../auth/authSlice'
import { connectExtension, isExtensionConfigured } from '../../lib/extension'

export default function ApiKeyCard() {
    const dispatch = useAppDispatch()
    const pendingApiKey = useAppSelector((state) => state.auth.pendingApiKey)
    const [connectState, setConnectState] = useState<'idle' | 'connecting' | 'connected' | 'failed'>('idle')
    const [reveal, setReveal] = useState(false)

    if (!pendingApiKey) return null

    async function handleConnect() {
        setConnectState('connecting')
        const result = await connectExtension(pendingApiKey!.raw_key, pendingApiKey!.principal_id)
        setConnectState(result.ok ? 'connected' : 'failed')
    }

    return (
        <div className="panel">
            <div className="panel-title"><h2>Your ControlPlane API key</h2><span className="badge amber">Shown once</span></div>
            <p className="muted">
                This key authenticates the browser extension as you. It's shown only now — store it
                somewhere safe, or connect the extension directly below.
            </p>
            <div className="table-wrap">
                <code style={{ display: 'block', padding: 12, wordBreak: 'break-all' }}>
                    {reveal ? pendingApiKey.raw_key : '•'.repeat(40)}
                </code>
            </div>
            <div style={{ display: 'flex', gap: 12, marginTop: 12, flexWrap: 'wrap' }}>
                <button className="outline" type="button" onClick={() => setReveal((v) => !v)}>
                    {reveal ? 'Hide key' : 'Reveal key'}
                </button>
                {isExtensionConfigured() ? (
                    <button className="status on" type="button" onClick={handleConnect} disabled={connectState === 'connecting'}>
                        {connectState === 'connected' ? 'Connected ✓' : connectState === 'connecting' ? 'Connecting…' : 'Connect extension'}
                    </button>
                ) : (
                    <span className="muted">Set VITE_EXTENSION_ID to enable one-click connect.</span>
                )}
                <button className="outline" type="button" onClick={() => dispatch(apiKeyAcknowledged())}>
                    I've saved it, dismiss
                </button>
            </div>
            {connectState === 'failed' && (
                <p className="notice">
                    Couldn't reach the extension automatically. Paste the key into the extension popup instead.
                </p>
            )}
        </div>
    )
}
