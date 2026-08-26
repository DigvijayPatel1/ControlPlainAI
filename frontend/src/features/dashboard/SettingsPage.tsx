import { useState } from 'react'
import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { apiKeyIssued } from '../auth/authSlice'
import { useRotateApiKeyMutation } from './../auth/authApi'
import { useBudgetQuery } from './dashboardApi'
import ApiKeyCard from './ApiKeyCard'
import { Metric, Panel } from './widgets'

export default function SettingsPage() {
    const dispatch = useAppDispatch()
    const user = useAppSelector((state) => state.auth.user)
    const pendingApiKey = useAppSelector((state) => state.auth.pendingApiKey)
    const [rotateApiKey, { isLoading }] = useRotateApiKeyMutation()
    const { data: budget } = useBudgetQuery()
    const [rotateError, setRotateError] = useState('')

    async function handleRotate() {
        setRotateError('')
        try {
            const result = await rotateApiKey().unwrap()
            dispatch(apiKeyIssued(result.api_key))
        } catch {
            setRotateError('Could not generate a new key. Please try again.')
        }
    }

    return (
        <>
            <header className="topbar">
                <div>
                    <p className="eyebrow">SECURITY CENTRE / 04</p>
                    <h1>Settings</h1>
                    <p className="muted">Your account, budget, and extension connection.</p>
                </div>
            </header>

            {pendingApiKey && <ApiKeyCard />}

            <Panel title="Account">
                <label className="setting"><span>Name</span><input value={user?.full_name ?? ''} disabled /></label>
                <label className="setting"><span>Email</span><input value={user?.email ?? ''} disabled /></label>
                <label className="setting"><span>Role</span><input value={user?.role ?? ''} disabled /></label>
                <label className="setting"><span>Principal ID<small>Used by the extension via X-API-Key.</small></span><input value={user?.default_principal_id ?? ''} disabled /></label>
            </Panel>

            <Panel title="Budget">
                {budget?.configured ? (
                    <div className="metrics">
                        <Metric label="Monthly limit" value={`$${budget.monthly_limit_usd?.toFixed(2)}`} />
                        <Metric label="Spent" value={`$${budget.spent_usd?.toFixed(4)}`} />
                        <Metric label="Remaining" value={`$${budget.remaining_usd?.toFixed(4)}`} tone="green" />
                        <Metric label="Blocked" value={budget.blocked_count ?? 0} tone="danger" />
                    </div>
                ) : (
                    <p className="muted">No budget configured yet.</p>
                )}
            </Panel>

            <Panel title="Browser extension">
                <p className="muted">
                    Generate a new API key any time — the extension picks it up automatically once you
                    connect, or you can paste it into the extension popup manually.
                </p>
                {rotateError && <div className="notice">{rotateError}</div>}
                <button className="outline" type="button" onClick={handleRotate} disabled={isLoading}>
                    {isLoading ? 'Generating…' : 'Generate new API key'}
                </button>
            </Panel>
        </>
    )
}