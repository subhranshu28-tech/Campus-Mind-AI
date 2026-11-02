import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import PasswordReset from "./pages/PasswordReset";
import AIAssistant from "./pages/AIAssistant";
import CollegeRegistration from "./pages/CollegeRegistration";

const Dashboard = lazy(() => import("./pages/Dashboard"));

function Protected({ children }) {
  const { user, checking } = useAuth();
  if (checking) return <div className="grid min-h-screen place-items-center text-sm text-slate-500">Loading your campus workspace…</div>;
  return user ? children : <Navigate to="/login" replace />;
}

function AppRoutes() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route path="/register-college" element={user ? <Navigate to="/" replace /> : <CollegeRegistration />} />
      <Route path="/password-reset" element={<PasswordReset />} />
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/ai" element={<Protected><AIAssistant /></Protected>} />
      <Route path="/" element={<Protected><Suspense fallback={<div className="grid min-h-screen place-items-center text-sm text-slate-500">Loading your campus workspace…</div>}><Dashboard /></Suspense></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return <AuthProvider><AppRoutes /></AuthProvider>;
}
