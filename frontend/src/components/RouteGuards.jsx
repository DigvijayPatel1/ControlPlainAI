import { Navigate, Outlet } from 'react-router-dom';
import { useAppSelector } from '../app/hooks';
export function ProtectedRoute() {
    const token = useAppSelector((state) => state.auth.token);
    if (!token)
        return <Navigate to="/login" replace/>;
    return <Outlet />;
}
export function PublicOnlyRoute() {
    const token = useAppSelector((state) => state.auth.token);
    if (token)
        return <Navigate to="/" replace/>;
    return <Outlet />;
}
export function RoleRoute({ allow }) {
    const user = useAppSelector((state) => state.auth.user);
    if (!user || !allow.includes(user.role))
        return <Navigate to="/" replace/>;
    return <Outlet />;
}
