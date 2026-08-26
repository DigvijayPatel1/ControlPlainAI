import { useEffect, useState } from 'react'
import { DEFAULT_STATE, getState, setState } from './lib/storage'
import type { ExtensionState } from './lib/storage'

function openDashboard() {
    chrome.runtime.sendMessage({ type: 'OPEN_DASHBOARD' })
}

function Toggle({
    label,
    checked,
    onChange,
}: {
    label: string
    checked: boolean
    onChange: () => void
}) {
    return (
        <label className="flex items-center justify-between border-b border-neutral-800 py-3 last:border-b-0">
            <span className="text-sm text-neutral-200">{label}</span>
            <button
                type="button"
                role="switch"
                aria-checked={checked}
                onClick={onChange}
                className={`relative h-5 w-9 rounded-full transition-colors ${
                    checked ? 'bg-emerald-500' : 'bg-neutral-700'
                }`}
            >
                <span
                    className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
                        checked ? 'translate-x-4.5' : 'translate-x-0.5'
                    }`}
                />
            </button>
        </label>
    )
}

export default function App() {
    const [state, setLocalState] = useState<ExtensionState>(DEFAULT_STATE)
    const [loaded, setLoaded] = useState(false)

    useEffect(() => {
        getState().then((loadedState) => {
            setLocalState(loadedState)
            setLoaded(true)
        })
    }, [])

    async function toggle(key: 'enabled' | 'optimizationEnabled' | 'showTokens') {
        const next = { ...state, [key]: !state[key] }
        setLocalState(next)
        await setState({ [key]: next[key] })
    }

    const connected = Boolean(state.apiKey)

    if (!loaded) {
        return <div className="h-40 w-80 bg-neutral-950" />
    }

    return (
        <div className="w-80 bg-neutral-950 p-5 font-sans text-neutral-100">
            <header className="flex items-center justify-between">
                <span className="text-lg font-semibold tracking-tight">ControlPlane</span>
                <span
                    className={`h-2.5 w-2.5 rounded-full ${connected ? 'bg-emerald-500' : 'bg-rose-500'}`}
                    title={connected ? 'Connected' : 'Not connected'}
                />
            </header>
            <p className="mt-1 mb-4 text-xs text-neutral-400">AI governance controls</p>

            <div
                className={`mb-4 rounded-lg px-3 py-2 text-xs break-all ${
                    connected
                        ? 'bg-emerald-950/60 text-emerald-300'
                        : 'bg-amber-950/60 text-amber-300'
                }`}
            >
                {connected ? (
                    <>
                        Connected
                        {state.principalId && (
                            <code className="mt-1 block opacity-80">{state.principalId}</code>
                        )}
                    </>
                ) : (
                    <>Not connected — sign in on the dashboard and click "Connect extension".</>
                )}
            </div>

            <div>
                <Toggle label="Protection" checked={state.enabled} onChange={() => toggle('enabled')} />
                <Toggle
                    label="Prompt optimization"
                    checked={state.optimizationEnabled}
                    onChange={() => toggle('optimizationEnabled')}
                />
                <Toggle
                    label="Show token savings"
                    checked={state.showTokens}
                    onChange={() => toggle('showTokens')}
                />
            </div>

            <button
                onClick={openDashboard}
                className="mt-4 w-full rounded-lg bg-emerald-500 py-2.5 text-sm font-semibold text-neutral-950 transition-colors hover:bg-emerald-400"
            >
                Open dashboard
            </button>
        </div>
    )
}