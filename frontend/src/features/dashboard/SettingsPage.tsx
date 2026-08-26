import { useState } from 'react'
import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { apiKeyIssued } from '../auth/authSlice'
import { useRotateApiKeyMutation } from '../auth/authApi'
import { useBudgetQuery } from './dashboardApi'
import ApiKeyCard from './ApiKeyCard'
import { Metric, Panel } from './widgets'

function Field({ label, value, hint }: { label: string; value: string; hint?: string }) {
    return (
        <label className="mb-4 block last:mb-0">
            <span className="mb-1 block text-xs font-medium text-muted">
                {label}
                {hint && <small className="ml-1 font-normal text-muted/70">{hint}</small>}
            </span>
            <input
                value={value}
                disabled
                className="w-full rounded-lg border border-line bg-paper px-3 py-2 font-mono text-sm text-ink disabled:cursor-not-allowed"
            />
        </label>
    )
}

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
            <header className="mb-6">
                <p className="font-mono text-xs tracking-widest text-muted uppercase">Security centre / 04</p>
                <h1 className="mt-1 text-2xl font-semibold text-ink">Settings</h1>
                <p className="mt-1 text-sm text-muted">Your account, budget, and extension connection.</p>
            </header>

            {pendingApiKey && (
                <div className="mb-6">
                    <ApiKeyCard />
                </div>
            )}

            <Panel title="Account">
                <Field label="Name" value={user?.full_name ?? ''} />
                <Field label="Email" value={user?.email ?? ''} />
                <Field label="Role" value={user?.role ?? ''} />
                <Field label="Principal ID" hint="Used by the extension via X-API-Key." value={user?.default_principal_id ?? ''} />
            </Panel>

            <Panel title="Budget">
                {budget?.configured ? (
                    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                        <Metric label="Monthly limit" value={`$${budget.monthly_limit_usd?.toFixed(2)}`} />
                        <Metric label="Spent" value={`$${budget.spent_usd?.toFixed(4)}`} />
                        <Metric label="Remaining" value={`$${budget.remaining_usd?.toFixed(4)}`} tone="green" />
                        <Metric label="Blocked" value={budget.blocked_count ?? 0} tone="danger" />
                    </div>
                ) : (
                    <p className="text-sm text-muted">No budget configured yet.</p>
                )}
            </Panel>

            <Panel title="Browser extension">
                <p className="mb-4 text-sm text-muted">
                    Generate a new API key any time — the extension picks it up automatically once you connect, or
                    you can paste it into the extension popup manually.
                </p>
                {rotateError && (
                    <div className="mb-4 rounded-lg border border-brand-red/30 bg-red-50 px-3 py-2 text-sm text-brand-red">
                        {rotateError}
                    </div>
                )}
                <button
                    type="button"
                    onClick={handleRotate}
                    disabled={isLoading}
                    className="rounded-lg border border-line px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-paper disabled:opacity-50"
                >
                    {isLoading ? 'Generating…' : 'Generate new API key'}
                </button>
            </Panel>
        </>
    )
}