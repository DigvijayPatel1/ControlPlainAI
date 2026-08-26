import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAppDispatch } from '../../app/hooks'
import { useLoginMutation } from './authApi'
import { credentialsReceived } from './authSlice'

export default function LoginPage() {
    const dispatch = useAppDispatch()
    const navigate = useNavigate()
    const [login, { isLoading }] = useLoginMutation()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')

    async function handleSubmit(event: FormEvent) {
        event.preventDefault()
        setError('')
        try {
            const result = await login({ email, password }).unwrap()
            dispatch(credentialsReceived({ token: result.access_token, user: result.user }))
            navigate('/')
        } catch {
            setError('Invalid email or password.')
        }
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-paper px-6 font-sans">
            <form
                onSubmit={handleSubmit}
                className="w-full max-w-sm rounded-2xl border border-line bg-card p-8 shadow-sm"
            >
                <div className="mb-6 flex items-center gap-3">
                    <span className="grid h-9 w-9 place-items-center rounded-lg bg-sidebar font-mono text-sm font-bold text-mint">
                        CP
                    </span>
                    <div className="leading-tight">
                        <strong className="block text-sm text-ink">ControlPlane</strong>
                        <small className="text-xs text-muted">AI governance</small>
                    </div>
                </div>

                <h1 className="text-xl font-semibold text-ink">Sign in</h1>
                <p className="mt-1 mb-5 text-sm text-muted">Access your guardrails dashboard.</p>

                {error && (
                    <div className="mb-4 rounded-lg border border-brand-red/30 bg-red-50 px-3 py-2 text-sm text-brand-red">
                        {error}
                    </div>
                )}

                <label className="mb-4 block">
                    <span className="mb-1 block text-xs font-medium text-muted">Email</span>
                    <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@company.com"
                        className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-brand-green"
                    />
                </label>

                <label className="mb-6 block">
                    <span className="mb-1 block text-xs font-medium text-muted">Password</span>
                    <input
                        type="password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-brand-green"
                    />
                </label>

                <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full rounded-lg bg-brand-green py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-green/90 disabled:opacity-60"
                >
                    {isLoading ? 'Signing in…' : 'Sign in'}
                </button>

                <p className="mt-5 text-center text-sm text-muted">
                    No account yet?{' '}
                    <Link to="/register" className="font-medium text-brand-green hover:underline">
                        Create one
                    </Link>
                </p>
            </form>
        </div>
    )
}