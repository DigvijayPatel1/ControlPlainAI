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
        <div className="auth-shell">
            <form className="auth-card" onSubmit={handleSubmit}>
                <div className="brand"><span className="brand-mark">CP</span><div><strong>ControlPlane</strong><small>AI governance</small></div></div>
                <h1>Create your account</h1>
                <p className="muted">A ControlPlane API key is generated for you automatically — you'll use it to connect the browser extension.</p>
                {error && <div className="notice">{error}</div>}
                <label className="setting">
                    <span>Full name</span>
                    <input required value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Ada Lovelace" />
                </label>
                <label className="setting">
                    <span>Email</span>
                    <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" />
                </label>
                <label className="setting">
                    <span>Password<small>Minimum 8 characters.</small></span>
                    <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
                </label>
                <button className="status on" type="submit" disabled={isLoading}>{isLoading ? 'Creating account…' : 'Create account'}</button>
                <p className="muted">Already have an account? <Link to="/login">Sign in</Link></p>
            </form>
        </div>
    )
}
