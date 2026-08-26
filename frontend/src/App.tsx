import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import AdminRoute from "./components/AdminRoute";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import TenantRedirect from "./components/TenantRedirect";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";

// Cargadas bajo demanda: son las paginas del panel (detras de login), no
// hace falta que viajen en el bundle inicial de /login.
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const AlertsPage = lazy(() => import("./pages/AlertsPage"));
const BuildingPage = lazy(() => import("./pages/BuildingPage"));
const UsersPage = lazy(() => import("./pages/UsersPage"));

function PageFallback() {
  return (
    <div
      className="flex h-full items-center justify-center p-8 text-sm text-slate-400 dark:text-slate-500"
      style={{ minHeight: "50vh" }}
    >
      Cargando...
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Suspense fallback={<PageFallback />}>
                <Routes>
                  <Route
                    path="/"
                    element={
                      <TenantRedirect>
                        <DashboardPage />
                      </TenantRedirect>
                    }
                  />
                  <Route
                    path="/polygon/:polygonId"
                    element={
                      <TenantRedirect>
                        <DashboardPage />
                      </TenantRedirect>
                    }
                  />
                  <Route
                    path="/polygon/:polygonId/alerts"
                    element={
                      <TenantRedirect>
                        <AlertsPage />
                      </TenantRedirect>
                    }
                  />
                  <Route
                    path="/alerts"
                    element={
                      <TenantRedirect>
                        <AlertsPage />
                      </TenantRedirect>
                    }
                  />
                  <Route path="/building/:buildingId" element={<BuildingPage />} />
                  <Route
                    path="/users"
                    element={
                      <AdminRoute>
                        <UsersPage />
                      </AdminRoute>
                    }
                  />
                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </Suspense>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
