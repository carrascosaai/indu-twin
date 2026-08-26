import { useQueryClient } from "@tanstack/react-query";
import { BellRing } from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { resolveAlert, updateIncident } from "../api/client";
import AlertsList from "../components/AlertsList";
import Pill from "../components/Pill";
import { Skeleton } from "../components/Skeleton";
import StateMessage from "../components/StateMessage";
import TabSwitcher from "../components/TabSwitcher";
import { NEXT_STATUS, PRIORITY_LABELS, STATUS_COLORS, STATUS_LABELS } from "../constants/incidents";
import { useToast } from "../context/ToastContext";
import { useAlerts, useBuildings, usePolygonIncidents, usePolygons } from "../hooks/useApi";
import type { AlertStatus, IncidentStatus } from "../types";

const ALERT_TABS: { label: string; value: AlertStatus | "all" }[] = [
  { label: "Activas", value: "active" },
  { label: "Resueltas", value: "resolved" },
  { label: "Todas", value: "all" },
];

const INCIDENT_TABS: { label: string; value: IncidentStatus | "all" }[] = [
  { label: "Abiertas", value: "open" },
  { label: "En curso", value: "in_progress" },
  { label: "Resueltas", value: "resolved" },
  { label: "Todas", value: "all" },
];

export default function AlertsPage() {
  const params = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { data: polygons } = usePolygons();
  const polygonId = params.polygonId ? Number(params.polygonId) : polygons?.[0]?.id;

  const [alertTab, setAlertTab] = useState<AlertStatus | "all">("active");
  const [incidentTab, setIncidentTab] = useState<IncidentStatus | "all">("open");

  const { data: buildings } = useBuildings(polygonId);
  const {
    data: alerts,
    isLoading: isLoadingAlerts,
    isError: isAlertsError,
  } = useAlerts({ polygon_id: polygonId, status: alertTab === "all" ? undefined : alertTab });
  const {
    data: incidents,
    isLoading: isLoadingIncidents,
    isError: isIncidentsError,
  } = usePolygonIncidents(polygonId, incidentTab === "all" ? undefined : incidentTab);

  const buildingNames = Object.fromEntries((buildings ?? []).map((b) => [b.id, b.name]));

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["alerts"] });
    queryClient.invalidateQueries({ queryKey: ["polygon-incidents"] });
    queryClient.invalidateQueries({ queryKey: ["polygon-dashboard"] });
    queryClient.invalidateQueries({ queryKey: ["building-dashboard"] });
  };

  const handleResolveAlert = async (alertId: number) => {
    try {
      await resolveAlert(alertId);
      invalidate();
      showToast("Alerta resuelta");
    } catch {
      showToast("No se pudo resolver la alerta", "error");
    }
  };

  const handleAdvanceIncident = async (incidentId: number, current: IncidentStatus) => {
    try {
      await updateIncident(incidentId, { status: NEXT_STATUS[current] });
      invalidate();
      showToast(`Incidencia marcada como "${STATUS_LABELS[NEXT_STATUS[current]]}"`);
    } catch {
      showToast("No se pudo actualizar la incidencia", "error");
    }
  };

  if (!polygonId) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <StateMessage variant="empty" title="No hay ningún polígono seleccionado" />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      <header className="app-header px-4 py-4 sm:px-8 sm:py-5">
        <h1 className="flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-slate-50">
          <BellRing size={18} strokeWidth={2} className="text-slate-400 dark:text-slate-500" />
          Alertas e incidencias
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">Vista global de todo el polígono, por nave.</p>
      </header>

      <main className="flex-1 space-y-6 p-4 sm:p-8">
        <div className="card p-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Alertas</h2>
            <TabSwitcher
              value={alertTab}
              onChange={setAlertTab}
              options={ALERT_TABS.map((t) => ({ value: t.value, label: t.label }))}
            />
          </div>

          {isAlertsError ? (
            <StateMessage variant="error" title="No se pudieron cargar las alertas" />
          ) : isLoadingAlerts ? (
            <div className="space-y-3 py-1">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <AlertsList
              alerts={alerts ?? []}
              buildingNames={buildingNames}
              onResolve={handleResolveAlert}
              onSelectBuilding={(id) => navigate(`/building/${id}`)}
              emptyLabel="No hay alertas en esta categoría"
            />
          )}
        </div>

        <div className="card p-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Incidencias</h2>
            <TabSwitcher
              value={incidentTab}
              onChange={setIncidentTab}
              options={INCIDENT_TABS.map((t) => ({ value: t.value, label: t.label }))}
            />
          </div>

          {isIncidentsError ? (
            <StateMessage variant="error" title="No se pudieron cargar las incidencias" />
          ) : isLoadingIncidents ? (
            <div className="space-y-3 py-1">
              {Array.from({ length: 2 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (incidents?.length ?? 0) === 0 ? (
            <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-200 dark:border-white/10 py-10 text-sm text-slate-400 dark:text-slate-500">
              No hay incidencias en esta categoría
            </div>
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-white/5">
              {incidents!.map((inc) => (
                <li key={inc.id} className="-mx-2 flex items-center justify-between gap-2 rounded-lg px-2 py-2.5 transition hover:bg-slate-50/80 dark:hover:bg-white/5">
                  <button
                    onClick={() => navigate(`/building/${inc.building_id}`)}
                    className="text-left"
                  >
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-200 hover:underline">
                      {buildingNames[inc.building_id] ?? `Nave #${inc.building_id}`} · {inc.title}
                    </p>
                    <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                      Prioridad {PRIORITY_LABELS[inc.priority]}
                    </p>
                  </button>
                  <button
                    onClick={() => handleAdvanceIncident(inc.id, inc.status)}
                    title="Pulsa para avanzar el estado"
                    className="shrink-0 transition hover:opacity-75"
                  >
                    <Pill color={STATUS_COLORS[inc.status]} label={STATUS_LABELS[inc.status]} dot={false} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
