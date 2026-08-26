import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { loggedOut } from '../auth/authSlice'
import { baseApi } from '../../api/baseApi'

const navItems: { to: string; label: string; end?: boolean }[] = [
    { to: '/', label: 'Overview', end: true },
    { to: '/requests', label: 'Requests' },
    { to: '/reviews', label: 'Reviews' },
    { to: '/settings', label: 'Settings' },
]

export default function DashboardLayout() {
    const dispatch = useAppDispatch()
    const navigate = useNavigate()
    const user = useAppSelector((state) => state.auth.user)

    function handleLogout() {
        dispatch(loggedOut())
        dispatch(baseApi.util.resetApiState())
        navigate('/login')
    }

    return (
        <div className="shell">
            <aside className="sidebar">
                <div className="brand"><span className="brand-mark">CP</span><div><strong>ControlPlane</strong><small>AI governance</small></div></div>
                <nav>
                    {navItems.map((item) => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            end={item.end}
                            className={({ isActive }) => (isActive ? 'nav active' : 'nav')}
                        >
                            {item.label}
                        </NavLink>
                    ))}
                    {user?.role === 'admin' && (
                        <NavLink to="/admin" className={({ isActive }) => (isActive ? 'nav active' : 'nav')}>
                            Admin
                        </NavLink>
                    )}
                </nav>
                <div className="side-foot" style={{ flexDirection: 'column', alignItems: 'stretch', gap: 8 }}>
                    <span>{user?.full_name} <small className="muted">({user?.role})</small></span>
                    <button className="outline" type="button" onClick={handleLogout}>Sign out</button>
                </div>
            </aside>
            <main className="main">
                <Outlet />
            </main>
        </div>
    )
}