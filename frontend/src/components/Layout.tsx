import { useQueryClient } from "@tanstack/react-query";
import { BellRing, Building2, Factory, LogOut, MapPin, Menu, Moon, Plus, Sun, Trash2, Users, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { deletePolygon } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { useToast } from "../context/ToastContext";
import { usePlanStatus, usePolygons } from "../hooks/useApi";
import NewPolygonModal from "./NewPolygonModal";

function NavItem({
  to,
  active,
  icon,
  children,
}: {
  to: string;
  active: boolean;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <Link
      to={to}
      className={`group relative flex items-center gap-2.5 rounded-lg py-2 pl-3.5 pr-3 text-sm font-medium transition-colors ${
        active ? "bg-white/[0.06] text-white" : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-100"
      }`}
    >
      <span
        className={`absolute left-0 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-full bg-blue-400 transition-opacity ${
          active ? "opacity-100" : "opacity-0"
        }`}
      />
      <span className={active ? "text-blue-400" : "text-slate-500 group-hover:text-slate-300"}>{icon}</span>
      <span className="truncate">{children}</span>
    </Link>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const params = useParams();
  const location = useLocation();
  const isTenant = user?.role === "tenant";
  const { data: polygons } = usePolygons(!isTenant);
  const { data: planStatus } = usePlanStatus();
  const activePolygonId = params.polygonId ? Number(params.polygonId) : polygons?.[0]?.id;
  const isAlertsRoute = location.pathname.includes("/alerts");
  const [showNewPolygon, setShowNewPolygon] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleDeletePolygon = async (polygonId: number, name: string) => {
    if (!window.confirm(`¿Eliminar "${name}"? Se borrarán también sus naves, sensores y datos.`)) return;
    try {
      await deletePolygon(polygonId);
      queryClient.invalidateQueries({ queryKey: ["polygons"] });
      showToast("Polígono eliminado");
      if (activePolygonId === polygonId) navigate("/");
    } catch {
      showToast("No se pudo eliminar el polígono", "error");
    }
  };

  return (
    <div className="flex min-h-screen" style={{ backgroundColor: "var(--canvas)" }}>
      <header className="app-header fixed inset-x-0 top-0 z-30 flex items-center justify-between px-4 py-3 md:hidden">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-600 text-white">
            <Factory size={14} strokeWidth={2.25} />
          </div>
          <p className="font-display text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            INDU-TWIN
          </p>
        </div>
        <button
          onClick={() => setMobileMenuOpen((v) => !v)}
          className="btn btn-ghost rounded-md p-1.5"
        >
          {mobileMenuOpen ? <X size={18} strokeWidth={2} /> : <Menu size={18} strokeWidth={2} />}
        </button>
      </header>

      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-30 bg-slate-900/40 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col overflow-hidden bg-[#0b1120] text-slate-200 transition-transform duration-200 md:relative md:translate-x-0 ${
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div
          className="pointer-events-none absolute inset-x-0 top-0 h-40 opacity-60"
          style={{ background: "radial-gradient(400px circle at 20% 0%, rgba(59,130,246,0.18), transparent 70%)" }}
        />
        <div className="relative flex items-center gap-2.5 px-6 py-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-400 to-blue-600 text-white shadow-sm shadow-blue-900/40">
            <Factory size={18} strokeWidth={2.25} />
          </div>
          <div>
            <p className="font-display text-sm font-semibold text-white">INDU-TWIN</p>
            <p className="text-[11px] text-slate-500">Digital Twin SaaS</p>
          </div>
        </div>

        {isTenant ? (
          <div className="relative space-y-0.5 px-3 pb-3">
            <NavItem
              to={`/building/${user.building_id}`}
              active={location.pathname === `/building/${user.building_id}`}
              icon={<Building2 size={16} strokeWidth={2} />}
            >
              Mi nave
            </NavItem>
          </div>
        ) : (
          <>
            <div className="relative space-y-0.5 px-3 pb-3">
              <NavItem
                to={activePolygonId ? `/polygon/${activePolygonId}/alerts` : "/alerts"}
                active={isAlertsRoute}
                icon={<BellRing size={16} strokeWidth={2} />}
              >
                Alertas e incidencias
              </NavItem>
              {user?.role === "admin" && (
                <NavItem to="/users" active={location.pathname === "/users"} icon={<Users size={16} strokeWidth={2} />}>
                  Usuarios
                </NavItem>
              )}
            </div>

            <div className="relative px-3">
              <div className="flex items-center justify-between px-3.5 pb-1.5">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-600">Polígonos</p>
                {user?.role === "admin" && (
                  <button
                    onClick={() => setShowNewPolygon(true)}
                    title="Nuevo polígono"
                    className="rounded p-0.5 text-slate-500 transition hover:bg-white/[0.08] hover:text-white"
                  >
                    <Plus size={13} strokeWidth={2} />
                  </button>
                )}
              </div>
              <nav className="space-y-0.5">
                {(polygons ?? []).map((p) => (
                  <div key={p.id} className="group/row relative">
                    <NavItem to={`/polygon/${p.id}`} active={activePolygonId === p.id} icon={<MapPin size={15} strokeWidth={2} />}>
                      {p.name}
                    </NavItem>
                    {user?.role === "admin" && (
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          handleDeletePolygon(p.id, p.name);
                        }}
                        title="Eliminar polígono"
                        className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-500 opacity-0 transition hover:bg-white/[0.1] hover:text-red-400 group-hover/row:opacity-100"
                      >
                        <Trash2 size={13} strokeWidth={2} />
                      </button>
                    )}
                  </div>
                ))}
              </nav>
            </div>
          </>
        )}

        <div className="relative mt-auto border-t border-white/[0.06] px-4 py-4">
          <div className="mb-3 flex items-center gap-2.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-slate-600 to-slate-800 text-xs font-semibold text-slate-200">
              {user?.full_name?.charAt(0).toUpperCase() ?? "?"}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-white">{user?.full_name}</p>
              <p className="flex items-center gap-1.5 text-[11px] text-slate-500">
                <span className="truncate">{user?.email}</span>
                <span className="shrink-0 rounded-full bg-white/[0.06] px-1.5 py-0.5 text-[10px] font-medium text-slate-300">
                  {user?.role === "admin" ? "Admin" : user?.role === "tenant" ? "Empresa" : "Operario"}
                </span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              onClick={handleLogout}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-md border border-white/10 py-1.5 text-xs font-medium text-slate-300 transition hover:border-white/20 hover:bg-white/[0.04]"
            >
              <LogOut size={13} strokeWidth={2} />
              Cerrar sesión
            </button>
            <button
              onClick={toggleTheme}
              title={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
              className="flex shrink-0 items-center justify-center rounded-md border border-white/10 p-1.5 text-slate-300 transition hover:border-white/20 hover:bg-white/[0.04]"
            >
              {theme === "dark" ? <Sun size={14} strokeWidth={2} /> : <Moon size={14} strokeWidth={2} />}
            </button>
          </div>
          <p className="mt-3 text-center text-[11px] text-slate-600">
            Plan{" "}
            <span className="font-semibold text-slate-400">
              {planStatus ? planStatus.plan.toUpperCase() : "…"}
            </span>
            {planStatus && !isTenant && (
              <>
                {" · "}
                {planStatus.buildings.used}
                {planStatus.buildings.limit !== null ? `/${planStatus.buildings.limit}` : ""} naves
              </>
            )}
          </p>
          <p className="mt-1 text-center text-[10px] text-slate-700">
            Demo con datos simulados — no uses datos reales
          </p>
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col pt-[52px] md:pt-0">{children}</div>

      {showNewPolygon && (
        <NewPolygonModal
          onClose={() => setShowNewPolygon(false)}
          onCreated={(polygonId) => {
            queryClient.invalidateQueries({ queryKey: ["polygons"] });
            navigate(`/polygon/${polygonId}`);
          }}
        />
      )}
    </div>
  );
}
