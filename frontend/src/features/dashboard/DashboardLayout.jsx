import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '../../app/hooks';
import { loggedOut } from '../auth/authSlice';
import { baseApi } from '../../api/baseApi';
const navItems = [
    { to: '/', label: 'Overview', end: true },
    { to: '/requests', label: 'Requests' },
    { to: '/reviews', label: 'Reviews' },
    { to: '/settings', label: 'Settings' },
];
const navLinkClasses = ({ isActive }) => `block rounded-lg px-3 py-2 text-sm font-medium transition-colors ${isActive ? 'bg-brand-green/20 text-mint' : 'text-white/70 hover:bg-white/5 hover:text-white'}`;
export default function DashboardLayout() {
    const dispatch = useAppDispatch();
    const navigate = useNavigate();
    const user = useAppSelector((state) => state.auth.user);
    function handleLogout() {
        dispatch(loggedOut());
        dispatch(baseApi.util.resetApiState());
        navigate('/login');
    }
    return (<div className="flex min-h-screen bg-paper font-sans text-ink">
            <aside className="flex w-64 shrink-0 flex-col bg-sidebar px-4 py-6 text-white">
                <div className="mb-8 flex items-center gap-3 px-2">
                    <span className="grid h-9 w-9 place-items-center rounded-lg bg-mint font-mono text-sm font-bold text-brand-green">
                        CP
                    </span>
                    <div className="leading-tight">
                        <strong className="block text-sm">ControlPlane</strong>
                        <small className="text-xs text-white/50">AI governance</small>
                    </div>
                </div>

                <nav className="flex flex-1 flex-col gap-1">
                    {navItems.map((item) => (<NavLink key={item.to} to={item.to} end={item.end} className={navLinkClasses}>
                            {item.label}
                        </NavLink>))}
                    {user?.role === 'admin' && (<NavLink to="/admin" className={navLinkClasses}>
                            Admin
                        </NavLink>)}
                </nav>

                <div className="mt-6 border-t border-white/10 pt-4">
                    <p className="mb-3 text-sm text-white/80">
                        {user?.full_name} <span className="text-xs text-white/40">({user?.role})</span>
                    </p>
                    <button type="button" onClick={handleLogout} className="w-full rounded-lg border border-white/15 py-2 text-sm font-medium text-white/80 transition-colors hover:bg-white/10 hover:text-white">
                        Sign out
                    </button>
                </div>
            </aside>

            <main className="flex-1 overflow-y-auto p-8">
                <Outlet />
            </main>
        </div>);
}
