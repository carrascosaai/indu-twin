import { useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Download,
  Droplets,
  Plus,
  Settings2,
  Thermometer,
  Trash2,
  Waves,
  X,
  Zap,
} from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  createIncident,
  deleteBuilding,
  downloadBuildingReadingsCsv,
  resolveAlert,
  updateIncident,
} from "../api/client";
import AlertsList from "../components/AlertsList";
import DeviceKeyButton from "../components/DeviceKeyButton";
import EfficiencyBadge from "../components/EfficiencyBadge";
import LiveIndicator from "../components/LiveIndicator";
import Pill from "../components/Pill";
import RiskBadge from "../components/RiskBadge";
import SeriesChart from "../components/SeriesChart";
import { BuildingSkeleton } from "../components/Skeleton";
import StateMessage from "../components/StateMessage";
import StatusBadge from "../components/StatusBadge";
import ThresholdsModal from "../components/ThresholdsModal";
import TimeRangeSelector from "../components/TimeRangeSelector";
import { NEXT_STATUS, PRIORITY_LABELS, STATUS_COLORS, STATUS_LABELS } from "../constants/incidents";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { useBuildingDashboard, useSensorReadings } from "../hooks/useApi";
import type { IncidentPriority, IncidentStatus, SensorType } from "../types";

const SENSOR_META: Record<SensorType, { label: string; color: string; icon: typeof Zap }> = {
  temperature: { label: "Temperatura", color: "#f97316", icon: Thermometer },
  energy: { label: "Consumo eléctrico", color: "#3b82f6", icon: Zap },
  vibration: { label: "Vibración", color: "#8b5cf6", icon: Waves },
  humidity: { label: "Humedad", color: "#0ea5e9", icon: Droplets },
};

function formatSensorValue(type: SensorType, value: number, unit: string): string {
  if (type === "energy" && value < 1) return `${Math.round(value * 1000)} Wh`;
  return `${value} ${unit}`;
}

function SensorChartCard({
  sensorId,
  type,
  unit,
  value,
  hours,
  showDeviceKey,
}: {
  sensorId: number;
  type: SensorType;
  unit: string;
  value: number | null;
  hours: number;
  showDeviceKey: boolean;
}) {
  const { data: readings } = useSensorReadings(sensorId, hours);
  const meta = SENSOR_META[type];
  const Icon = meta.icon;

  return (
    <div className="card card-interactive p-5">
      <div className="mb-1 flex items-baseline justify-between">
        <div className="flex items-center gap-1.5">
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-800 dark:text-slate-200">
            <Icon size={14} strokeWidth={2} style={{ color: meta.color }} />
            {meta.label}
          </h3>
          {showDeviceKey && <DeviceKeyButton sensorId={sensorId} />}
        </div>
        <span className="font-display text-xl font-semibold" style={{ color: meta.color }}>
          {value !== null ? formatSensorValue(type, value, unit) : "—"}
        </span>
      </div>
      <SeriesChart data={readings ?? []} color={meta.color} unit={unit} spansMultipleDays={hours > 24} />
    </div>
  );
}

export default function BuildingPage() {
  const { buildingId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { user } = useAuth();
  const id = Number(buildingId);
  const { data: dashboard, isLoading, isError, error, refetch, dataUpdatedAt } = useBuildingDashboard(id);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<IncidentPriority>("medium");
  const [hours, setHours] = useState(24);
  const [isCreatingIncident, setIsCreatingIncident] = useState(false);
  const [showThresholds, setShowThresholds] = useState(false);

  if (isError) {
    const status = (error as { response?: { status?: number } })?.response?.status;
    const isForbidden = status === 403;
    return (
      <div className="flex h-full items-center justify-center p-8">
        <StateMessage
          variant="error"
          title={isForbidden ? "No tienes acceso a esta nave" : "No se pudo cargar esta nave"}
          description={
            isForbidden
              ? "Tu cuenta solo puede ver los datos de su propia nave."
              : "Puede que la nave no exista o que se haya perdido la conexión con el servidor."
          }
          action={isForbidden ? undefined : { label: "Reintentar", onClick: () => refetch() }}
        />
      </div>
    );
  }

  if (isLoading || !dashboard) {
    return <BuildingSkeleton />;
  }

  const {
    building,
    sensors,
    active_alerts,
    incidents,
    efficiency_kwh_per_m2,
    efficiency_score,
    polygon_avg_kwh_per_m2,
    predicted_energy_kwh_24h,
    maintenance_risk_score,
    maintenance_risk_label,
  } = dashboard;

  const invalidateBuilding = () =>
    queryClient.invalidateQueries({ queryKey: ["building-dashboard", id] });

  const handleResolve = async (alertId: number) => {
    try {
      await resolveAlert(alertId);
      invalidateBuilding();
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      showToast("Alerta resuelta");
    } catch {
      showToast("No se pudo resolver la alerta", "error");
    }
  };

  const handleCreateIncident = async () => {
    if (!title.trim()) return;
    setIsCreatingIncident(true);
    try {
      await createIncident(id, { title, description, priority });
      setTitle("");
      setDescription("");
      setPriority("medium");
      setShowForm(false);
      invalidateBuilding();
      showToast("Incidencia creada");
    } catch {
      showToast("No se pudo crear la incidencia", "error");
    } finally {
      setIsCreatingIncident(false);
    }
  };

  const handleAdvanceStatus = async (incidentId: number, current: IncidentStatus) => {
    try {
      await updateIncident(incidentId, { status: NEXT_STATUS[current] });
      invalidateBuilding();
      showToast(`Incidencia marcada como "${STATUS_LABELS[NEXT_STATUS[current]]}"`);
    } catch {
      showToast("No se pudo actualizar la incidencia", "error");
    }
  };

  const handleExport = async () => {
    try {
      await downloadBuildingReadingsCsv(id, hours);
      showToast("Descarga iniciada");
    } catch {
      showToast("No se pudo exportar las lecturas", "error");
    }
  };

  const handleDeleteBuilding = async () => {
    if (!window.confirm(`¿Eliminar "${building.name}"? Se borrarán también sus sensores, históricos, alertas e incidencias.`)) {
      return;
    }
    try {
      await deleteBuilding(id);
      queryClient.invalidateQueries({ queryKey: ["buildings"] });
      queryClient.invalidateQueries({ queryKey: ["polygon-dashboard"] });
      showToast("Nave eliminada");
      navigate("/");
    } catch {
      showToast("No se pudo eliminar la nave", "error");
    }
  };

  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      <header className="app-header px-4 py-4 sm:px-8 sm:py-5">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 dark:text-slate-500 transition hover:text-slate-600 dark:hover:text-slate-300"
          >
            <ArrowLeft size={13} strokeWidth={2} />
            Volver
          </button>
          {user?.role === "admin" && (
            <div className="flex flex-wrap items-center gap-3 sm:gap-4">
              <button
                onClick={() => setShowThresholds(true)}
                className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 dark:text-slate-500 transition hover:text-slate-700 dark:hover:text-slate-200"
              >
                <Settings2 size={13} strokeWidth={2} />
                Umbrales de alerta
              </button>
              <button
                onClick={handleDeleteBuilding}
                className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 dark:text-slate-500 transition hover:text-red-600"
              >
                <Trash2 size={13} strokeWidth={2} />
                Eliminar nave
              </button>
            </div>
          )}
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-50">{building.name}</h1>
            <div className="flex items-center gap-2">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {building.code} · {building.building_type} · {building.area_m2.toLocaleString("es-ES")} m²
              </p>
              <span className="text-slate-300 dark:text-slate-600">·</span>
              <LiveIndicator updatedAt={dataUpdatedAt} />
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="text-right">
              <div className="flex items-center gap-1.5">
                {efficiency_kwh_per_m2 !== null && <EfficiencyBadge score={efficiency_score} />}
                <RiskBadge score={maintenance_risk_score} label={maintenance_risk_label} />
              </div>
              {efficiency_kwh_per_m2 !== null && polygon_avg_kwh_per_m2 !== null && (
                <p className="mt-1 text-[11px] text-slate-400 dark:text-slate-500">
                  {efficiency_kwh_per_m2.toFixed(3)} kWh/m² · media poligono{" "}
                  {polygon_avg_kwh_per_m2.toFixed(3)}
                </p>
              )}
            </div>
            <StatusBadge status={building.status} />
          </div>
        </div>
      </header>

      <main className="flex-1 space-y-6 p-4 sm:p-8">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <TimeRangeSelector value={hours} onChange={setHours} />
            {predicted_energy_kwh_24h !== null && (
              <span className="text-xs text-slate-400 dark:text-slate-500">
                Previsión próximas 24h:{" "}
                <span className="font-medium text-slate-600 dark:text-slate-300">
                  {predicted_energy_kwh_24h.toFixed(1)} kWh
                </span>
              </span>
            )}
          </div>
          <button
            onClick={handleExport}
            className="btn btn-secondary self-start px-3 py-1.5 text-xs sm:self-auto"
          >
            <Download size={13} strokeWidth={2} />
            Exportar lecturas
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {sensors.map((s) => (
            <SensorChartCard
              key={s.id}
              sensorId={s.id}
              type={s.sensor_type}
              unit={s.unit}
              value={s.latest_value}
              hours={hours}
              showDeviceKey={user?.role === "admin"}
            />
          ))}
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="card p-5">
            <h2 className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-200">Alertas activas</h2>
            <AlertsList alerts={active_alerts} onResolve={handleResolve} emptyLabel="Sin alertas activas" />
          </div>

          <div className="card p-5">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Incidencias</h2>
              <button
                onClick={() => setShowForm((v) => !v)}
                className="btn btn-primary px-2.5 py-1 text-xs"
              >
                {showForm ? <X size={13} strokeWidth={2} /> : <Plus size={13} strokeWidth={2} />}
                {showForm ? "Cancelar" : "Nueva incidencia"}
              </button>
            </div>

            {showForm && (
              <div className="mb-4 space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3">
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Titulo"
                  className="input w-full"
                />
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Descripcion (opcional)"
                  className="input w-full"
                  rows={2}
                />
                <div className="flex items-center justify-between">
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value as IncidentPriority)}
                    className="input text-xs"
                  >
                    {(Object.keys(PRIORITY_LABELS) as IncidentPriority[]).map((p) => (
                      <option key={p} value={p}>
                        Prioridad {PRIORITY_LABELS[p]}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={handleCreateIncident}
                    disabled={isCreatingIncident}
                    className="btn btn-primary px-3 py-1.5 text-xs disabled:opacity-60"
                  >
                    {isCreatingIncident ? "Creando..." : "Crear incidencia"}
                  </button>
                </div>
              </div>
            )}

            {incidents.length === 0 ? (
              <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-200 dark:border-white/10 py-10 text-sm text-slate-400 dark:text-slate-500">
                Sin incidencias registradas
              </div>
            ) : (
              <ul className="divide-y divide-slate-100 dark:divide-white/5">
                {incidents.map((inc) => (
                  <li key={inc.id} className="-mx-2 rounded-lg px-2 py-2.5 transition hover:bg-slate-50/80 dark:hover:bg-white/5">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{inc.title}</p>
                        <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                          Prioridad {PRIORITY_LABELS[inc.priority]}
                        </p>
                      </div>
                      <button
                        onClick={() => handleAdvanceStatus(inc.id, inc.status)}
                        title="Pulsa para avanzar el estado"
                        className="shrink-0 transition hover:opacity-75"
                      >
                        <Pill color={STATUS_COLORS[inc.status]} label={STATUS_LABELS[inc.status]} dot={false} />
                      </button>
                    </div>
                    {inc.description && (
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{inc.description}</p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </main>

      {showThresholds && (
        <ThresholdsModal
          building={building}
          onClose={() => setShowThresholds(false)}
          onSaved={invalidateBuilding}
        />
      )}
    </div>
  );
}
