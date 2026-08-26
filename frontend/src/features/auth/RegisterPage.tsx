import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAppDispatch } from '../../app/hooks'
import { useRegisterMutation } from './authApi'
import { credentialsReceived } from './authSlice'

export default function RegisterPage() {
    const dispatch = useAppDispatch()
    const navigate = useNavigate()
    const [register, { isLoading }] = useRegisterMutation()
    const [fullName, setFullName] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')

    async function handleSubmit(event: FormEvent) {
        event.preventDefault()
        setError('')
        try {
            const result = await register({ email, full_name: fullName, password }).unwrap()
            dispatch(
                credentialsReceived({
                    token: result.access_token,
                    user: result.user,
                    apiKey: result.api_key ?? undefined,
                }),
            )
            navigate('/')
        } catch (err) {
            const status = (err as { status?: number })?.status
            setError(status === 409 ? 'That email is already registered.' : 'Registration failed. Please check your details.')
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

                <h1 className="text-xl font-semibold text-ink">Create your account</h1>
                <p className="mt-1 mb-5 text-sm text-muted">
                    A ControlPlane API key is generated for you automatically — you'll use it to connect the
                    browser extension.
                </p>

                {error && (
                    <div className="mb-4 rounded-lg border border-brand-red/30 bg-red-50 px-3 py-2 text-sm text-brand-red">
                        {error}
                    </div>
                )}

                <label className="mb-4 block">
                    <span className="mb-1 block text-xs font-medium text-muted">Full name</span>
                    <input
                        required
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        placeholder="Ada Lovelace"
                        className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-brand-green"
                    />
                </label>

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
                    <span className="mb-1 block text-xs font-medium text-muted">
                        Password <small className="font-normal text-muted/70">Minimum 8 characters.</small>
                    </span>
                    <input
                        type="password"
                        required
                        minLength={8}
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
                    {isLoading ? 'Creating account…' : 'Create account'}
                </button>

                <p className="mt-5 text-center text-sm text-muted">
                    Already have an account?{' '}
                    <Link to="/login" className="font-medium text-brand-green hover:underline">
                        Sign in
                    </Link>
                </p>
            </form>
        </div>
    )
}