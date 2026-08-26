import type { ReactElement } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useAppSelector } from '../app/hooks'
import type { UserRole } from '../features/auth/authSlice'

export function ProtectedRoute(): ReactElement {
    const token = useAppSelector((state) => state.auth.token)
    if (!token) return <Navigate to="/login" replace />
    return <Outlet />
}

export function PublicOnlyRoute(): ReactElement {
    const token = useAppSelector((state) => state.auth.token)
    if (token) return <Navigate to="/" replace />
    return <Outlet />
}

export function RoleRoute({ allow }: { allow: UserRole[] }): ReactElement {
    const user = useAppSelector((state) => state.auth.user)
    if (!user || !allow.includes(user.role)) return <Navigate to="/" replace />
    return <Outlet />
}
