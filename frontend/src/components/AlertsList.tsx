import { Check } from "lucide-react";
import type { Alert } from "../types";

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "ahora mismo";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  return `hace ${Math.floor(hours / 24)} d`;
}

interface AlertsListProps {
  alerts: Alert[];
  buildingNames?: Record<number, string>;
  onResolve?: (id: number) => void;
  onSelectBuilding?: (buildingId: number) => void;
  emptyLabel?: string;
}

export default function AlertsList({
  alerts,
  buildingNames,
  onResolve,
  onSelectBuilding,
  emptyLabel,
}: AlertsListProps) {
  if (alerts.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-dashed border-slate-200 dark:border-white/10 py-10 text-sm text-slate-400 dark:text-slate-500">
        {emptyLabel ?? "Sin alertas"}
      </div>
    );
  }

  return (
    <ul className="divide-y divide-slate-100 dark:divide-white/5">
      {alerts.map((alert) => {
        const color = alert.severity === "critical" ? "#ef4444" : "#f59e0b";
        return (
          <li key={alert.id} className="-mx-2 flex items-start justify-between gap-3 rounded-lg px-2 py-3 transition hover:bg-slate-50/80 dark:hover:bg-white/5">
            <div className="flex items-start gap-3">
              <span className="relative mt-1.5 flex h-2 w-2 shrink-0">
                {alert.severity === "critical" && alert.status === "active" && (
                  <span
                    className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60"
                    style={{ backgroundColor: color }}
                  />
                )}
                <span className="relative inline-flex h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
              </span>
              <div>
                {onSelectBuilding ? (
                  <button
                    onClick={() => onSelectBuilding(alert.building_id)}
                    className="text-left text-sm font-medium text-slate-800 dark:text-slate-200 hover:underline"
                  >
                    {buildingNames?.[alert.building_id] ? `${buildingNames[alert.building_id]} · ` : ""}
                    {alert.message}
                  </button>
                ) : (
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                    {buildingNames?.[alert.building_id] ? `${buildingNames[alert.building_id]} · ` : ""}
                    {alert.message}
                  </p>
                )}
                <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
                  {alert.alert_type === "anomaly" ? "Anomalía" : "Umbral"} · {timeAgo(alert.created_at)}
                  {alert.status === "resolved" && " · resuelta"}
                </p>
              </div>
            </div>
            {onResolve && alert.status === "active" && (
              <button
                onClick={() => onResolve(alert.id)}
                className="btn btn-secondary shrink-0 gap-1 px-2.5 py-1 text-xs"
              >
                <Check size={12} strokeWidth={2.5} />
                Resolver
              </button>
            )}
          </li>
        );
      })}
    </ul>
  );
}
