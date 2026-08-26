import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { token, isLoading } = useAuth();
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  if (isLoading) {
    return (
      <div
        className="flex h-screen items-center justify-center text-sm text-slate-400 dark:text-slate-500"
        style={{ backgroundColor: "var(--canvas)" }}
      >
        Cargando sesión...
      </div>
    );
  }

  return <>{children}</>;
}
