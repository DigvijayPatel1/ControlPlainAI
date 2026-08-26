import { useEffect, useState } from 'react';
import { DEFAULT_STATE, getState, setState } from './lib/storage';
function openDashboard() {
    chrome.runtime.sendMessage({ type: 'OPEN_DASHBOARD' });
}
function Toggle({ label, checked, onChange, }) {
    return (<label className="flex items-center justify-between border-b border-white/10 py-3 last:border-b-0">
            <span className="text-sm text-white/90">{label}</span>
            <button type="button" role="switch" aria-checked={checked} onClick={onChange} className={`relative h-5 w-9 rounded-full transition-colors ${checked ? 'bg-brand-green' : 'bg-white/15'}`}>
                <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${checked ? 'translate-x-4.5' : 'translate-x-0.5'}`}/>
            </button>
        </label>);
}
export default function App() {
    const [state, setLocalState] = useState(DEFAULT_STATE);
    const [loaded, setLoaded] = useState(false);
    useEffect(() => {
        getState().then((loadedState) => {
            setLocalState(loadedState);
            setLoaded(true);
        });
    }, []);
    async function toggle(key) {
        const next = { ...state, [key]: !state[key] };
        setLocalState(next);
        await setState({ [key]: next[key] });
    }
    const connected = Boolean(state.apiKey);
    if (!loaded) {
        return <div className="h-40 w-80 bg-sidebar"/>;
    }
    return (<div className="w-80 bg-sidebar p-5 font-sans text-white">
            <header className="flex items-center gap-3">
                <span className="grid h-8 w-8 place-items-center rounded-lg bg-mint font-mono text-xs font-bold text-brand-green">
                    CP
                </span>
                <div className="flex-1 leading-tight">
                    <span className="block text-sm font-semibold">ControlPlane</span>
                    <span className="text-xs text-white/50">AI governance</span>
                </div>
                <span className={`h-2.5 w-2.5 rounded-full ${connected ? 'bg-brand-green' : 'bg-brand-red'}`} title={connected ? 'Connected' : 'Not connected'}/>
            </header>

            <div className={`mt-4 mb-4 rounded-lg px-3 py-2 text-xs break-all ${connected ? 'bg-brand-green/15 text-mint' : 'bg-brand-amber/15 text-brand-amber'}`}>
                {connected ? (<>
                        Connected
                        {state.principalId && <code className="mt-1 block opacity-80">{state.principalId}</code>}
                    </>) : (<>Not connected — sign in on the dashboard and click "Connect extension".</>)}
            </div>

            <div>
                <Toggle label="Protection" checked={state.enabled} onChange={() => toggle('enabled')}/>
                <Toggle label="Prompt optimization" checked={state.optimizationEnabled} onChange={() => toggle('optimizationEnabled')}/>
                <Toggle label="Show token savings" checked={state.showTokens} onChange={() => toggle('showTokens')}/>
            </div>

            <button onClick={openDashboard} className="mt-4 w-full rounded-lg bg-brand-green py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-green/90">
                Open dashboard
            </button>
        </div>);
}
