import { Navigate, Route, Routes } from 'react-router-dom';
import LoginPage from './features/auth/LoginPage';
import RegisterPage from './features/auth/RegisterPage';
import DashboardLayout from './features/dashboard/DashboardLayout';
import OverviewPage from './features/dashboard/OverviewPage';
import RequestsPage from './features/dashboard/RequestsPage';
import ReviewsPage from './features/dashboard/ReviewsPage';
import SettingsPage from './features/dashboard/SettingsPage';
import { ProtectedRoute, PublicOnlyRoute } from './components/RouteGuards';
function App() {
    return (<Routes>
            <Route element={<PublicOnlyRoute />}>
                <Route path="/login" element={<LoginPage />}/>
                <Route path="/register" element={<RegisterPage />}/>
            </Route>

            <Route element={<ProtectedRoute />}>
                <Route element={<DashboardLayout />}>
                    <Route path="/" element={<OverviewPage />}/>
                    <Route path="/requests" element={<RequestsPage />}/>
                    <Route path="/reviews" element={<ReviewsPage />}/>
                    <Route path="/settings" element={<SettingsPage />}/>
                </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace/>}/>
        </Routes>);
}
export default App;
