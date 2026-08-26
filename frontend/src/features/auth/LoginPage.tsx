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
        <div className="auth-shell">
            <form className="auth-card" onSubmit={handleSubmit}>
                <div className="brand"><span className="brand-mark">CP</span><div><strong>ControlPlane</strong><small>AI governance</small></div></div>
                <h1>Sign in</h1>
                <p className="muted">Access your guardrails dashboard.</p>
                {error && <div className="notice">{error}</div>}
                <label className="setting">
                    <span>Email</span>
                    <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" />
                </label>
                <label className="setting">
                    <span>Password</span>
                    <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
                </label>
                <button className="status on" type="submit" disabled={isLoading}>{isLoading ? 'Signing in…' : 'Sign in'}</button>
                <p className="muted">No account yet? <Link to="/register">Create one</Link></p>
            </form>
        </div>
    )
}
