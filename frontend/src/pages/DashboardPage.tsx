import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Box, Building2, Download, Gauge, Map as MapIcon, Plus, Zap } from "lucide-react";
import { lazy, Suspense, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { downloadPolygonAlertsCsv } from "../api/client";
import AlertsList from "../components/AlertsList";
import EfficiencyBadge from "../components/EfficiencyBadge";
import EnergyForecastChart from "../components/EnergyForecastChart";
import KpiCard from "../components/KpiCard";
import LiveIndicator from "../components/LiveIndicator";
import NewBuildingModal from "../components/NewBuildingModal";
import { DashboardSkeleton } from "../components/Skeleton";
import SeriesChart from "../components/SeriesChart";
import StateMessage from "../components/StateMessage";
import StatusBadge from "../components/StatusBadge";
import TabSwitcher from "../components/TabSwitcher";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { useBuildings, usePolygonDashboard, usePolygons } from "../hooks/useApi";

const MapView = lazy(() => import("../components/MapView"));
const Scene3D = lazy(() => import("../components/Scene3D"));

export default function DashboardPage() {
  const params = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState<"map" | "3d">("map");
  const [showNewBuilding, setShowNewBuilding] = useState(false);
  const { data: polygons, isLoading: isLoadingPolygons, isError: isPolygonsError, refetch: refetchPolygons } = usePolygons();
  const activePolygonId = params.polygonId ? Number(params.polygonId) : polygons?.[0]?.id;

  const {
    data: dashboard,
    isLoading: isLoadingDashboard,
    isError: isDashboardError,
    refetch: refetchDashboard,
    dataUpdatedAt,
  } = usePolygonDashboard(activePolygonId);
  const { data: buildings } = useBuildings(activePolygonId);

  if (isPolygonsError) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <StateMessage
          variant="error"
          title="No se pudo conectar con el servidor"
          description="Comprueba que el backend de INDU-TWIN esté en marcha e inténtalo de nuevo."
          action={{ label: "Reintentar", onClick: () => refetchPolygons() }}
        />
      </div>
    );
  }

  if (!isLoadingPolygons && (polygons?.length ?? 0) === 0) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <StateMessage
          variant="empty"
          title="Todavía no hay polígonos"
          description={
            user?.role === "admin"
              ? 'Pulsa el "+" junto a Polígonos, en el menú lateral, para crear el primero.'
              : "Pide a un administrador que cree el primer polígono industrial."
          }
        />
      </div>
    );
  }

  if (isDashboardError) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <StateMessage
          variant="error"
          title="No se pudo cargar el polígono"
          description="Ha fallado la petición al servidor. Puedes reintentarlo."
          action={{ label: "Reintentar", onClick: () => refetchDashboard() }}
        />
      </div>
    );
  }

  if (!activePolygonId || isLoadingDashboard || !dashboard) {
    return <DashboardSkeleton />;
  }

  const buildingNames = Object.fromEntries((buildings ?? []).map((b) => [b.id, b.name]));

  const handleExport = async () => {
    try {
      await downloadPolygonAlertsCsv(dashboard.polygon.id);
      showToast("Descarga iniciada");
    } catch {
      showToast("No se pudo exportar las alertas", "error");
    }
  };

  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      <header className="app-header px-4 py-4 sm:px-8 sm:py-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-50">{dashboard.polygon.name}</h1>
            <div className="flex items-center gap-2">
              <p className="text-sm text-slate-500 dark:text-slate-400">{dashboard.polygon.address}</p>
              <span className="text-slate-300 dark:text-slate-600">·</span>
              <LiveIndicator updatedAt={dataUpdatedAt} />
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <StatusBadge status={dashboard.overall_status} />
            <button
              onClick={handleExport}
              className="btn btn-secondary px-3 py-1.5 text-xs"
            >
              <Download size={13} strokeWidth={2} />
              Exportar alertas
            </button>
            {user?.role === "admin" && (
              <button
                onClick={() => setShowNewBuilding(true)}
                className="btn btn-primary px-3 py-1.5 text-xs"
              >
                <Plus size={13} strokeWidth={2} />
                Nueva nave
              </button>
            )}
          </div>
        </div>
      </header>

      {showNewBuilding && (
        <NewBuildingModal
          polygonId={dashboard.polygon.id}
          defaultLat={dashboard.polygon.center_lat}
          defaultLng={dashboard.polygon.center_lng}
          onClose={() => setShowNewBuilding(false)}
          onCreated={() => {
            queryClient.invalidateQueries({ queryKey: ["buildings", dashboard.polygon.id] });
            queryClient.invalidateQueries({ queryKey: ["polygon-dashboard", dashboard.polygon.id] });
          }}
        />
      )}

      <main className="flex-1 space-y-6 p-4 sm:p-8">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            label="Edificios / naves"
            value={dashboard.building_count}
            icon={<Building2 size={16} strokeWidth={2} />}
          />
          <KpiCard
            label="Consumo (24h)"
            value={`${dashboard.total_energy_kwh_24h.toFixed(0)} kWh`}
            icon={<Zap size={16} strokeWidth={2} />}
            trendPct={dashboard.energy_trend_pct}
            trendInverse
            sublabel="vs. 24h anteriores"
          />
          <KpiCard
            label="Alertas activas"
            value={dashboard.active_alerts_count}
            accent={dashboard.active_alerts_count > 0 ? "critical" : "success"}
            icon={<AlertTriangle size={16} strokeWidth={2} />}
          />
          <KpiCard
            label="Estado general"
            value={<StatusBadge status={dashboard.overall_status} />}
            icon={<Gauge size={16} strokeWidth={2} />}
          />
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <div className="flex h-[420px] flex-col overflow-hidden card p-2 xl:col-span-2">
            <div className="mb-2 flex justify-end">
              <TabSwitcher
                value={viewMode}
                onChange={setViewMode}
                options={[
                  { value: "map", label: "Mapa", icon: <MapIcon size={13} strokeWidth={2} /> },
                  { value: "3d", label: "3D", icon: <Box size={13} strokeWidth={2} /> },
                ]}
              />
            </div>
            <div className="flex-1 overflow-hidden rounded-lg">
              <Suspense
                fallback={
                  <div className="flex h-full items-center justify-center text-sm text-slate-400 dark:text-slate-500">
                    Cargando...
                  </div>
                }
              >
                {viewMode === "map" ? (
                  <MapView
                    centerLat={dashboard.polygon.center_lat}
                    centerLng={dashboard.polygon.center_lng}
                    buildings={buildings ?? []}
                  />
                ) : (
                  <Scene3D
                    centerLat={dashboard.polygon.center_lat}
                    centerLng={dashboard.polygon.center_lng}
                    buildings={buildings ?? []}
                  />
                )}
              </Suspense>
            </div>
          </div>

          <div className="card p-5">
            <h2 className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-200">Alertas recientes</h2>
            <AlertsList alerts={dashboard.recent_alerts} buildingNames={buildingNames} />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="card p-5">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Consumo: real y previsto</h2>
              {dashboard.predicted_energy_kwh_24h !== null && (
                <span className="text-xs text-slate-400 dark:text-slate-500">
                  Próximas 24h:{" "}
                  <span className="font-medium text-slate-600 dark:text-slate-300">
                    {dashboard.predicted_energy_kwh_24h.toFixed(0)} kWh
                  </span>
                </span>
              )}
            </div>
            <EnergyForecastChart
              actual={dashboard.energy_series}
              predicted={dashboard.predicted_energy_series}
            />
          </div>
          <div className="card p-5">
            <h2 className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-200">Evolución de temperatura (24h)</h2>
            <SeriesChart data={dashboard.temperature_series} color="#f97316" unit="C" />
          </div>
        </div>

        <div className="card p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-800 dark:text-slate-200">Ranking de consumo por nave (24h)</h2>
          {dashboard.ranking.length === 0 ? (
            <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-200 dark:border-white/10 py-10 text-sm text-slate-400 dark:text-slate-500">
              Añade una nave para empezar a ver datos
            </div>
          ) : (
          <ul className="divide-y divide-slate-100 dark:divide-white/5">
            {dashboard.ranking.map((item, idx) => {
              const max = dashboard.ranking[0]?.total_energy_kwh || 1;
              const RANK_COLORS = ["#eab308", "#94a3b8", "#b45309"];
              return (
                <li
                  key={item.building_id}
                  className="-mx-2 flex cursor-pointer items-center gap-4 rounded-lg px-2 py-2.5 transition hover:bg-slate-50/80 dark:hover:bg-white/5"
                  onClick={() => navigate(`/building/${item.building_id}`)}
                >
                  <span
                    className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold"
                    style={
                      idx < 3
                        ? { backgroundColor: `color-mix(in srgb, ${RANK_COLORS[idx]} 18%, var(--surface))`, color: RANK_COLORS[idx] }
                        : { color: "var(--text-tertiary)" }
                    }
                  >
                    {idx + 1}
                  </span>
                  <span className="w-44 shrink-0 truncate text-sm font-medium text-slate-700 dark:text-slate-300">
                    {item.name}
                  </span>
                  <div className="h-1.5 flex-1 rounded-full bg-slate-100 dark:bg-white/10">
                    <div
                      className="h-1.5 rounded-full bg-gradient-to-r from-blue-400 to-blue-600"
                      style={{ width: `${Math.max(4, (item.total_energy_kwh / max) * 100)}%` }}
                    />
                  </div>
                  <span className="w-20 shrink-0 text-right text-sm text-slate-500 dark:text-slate-400">
                    {item.total_energy_kwh.toFixed(1)} kWh
                  </span>
                  <span className="w-28 shrink-0 text-right">
                    <EfficiencyBadge score={item.efficiency_score} />
                  </span>
                </li>
              );
            })}
          </ul>
          )}
        </div>
      </main>
    </div>
  );
}
