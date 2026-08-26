import type { IncidentPriority, IncidentStatus } from "../types";

export const PRIORITY_LABELS: Record<IncidentPriority, string> = {
  low: "Baja",
  medium: "Media",
  high: "Alta",
};

export const STATUS_LABELS: Record<IncidentStatus, string> = {
  open: "Abierta",
  in_progress: "En curso",
  resolved: "Resuelta",
};

export const NEXT_STATUS: Record<IncidentStatus, IncidentStatus> = {
  open: "in_progress",
  in_progress: "resolved",
  resolved: "open",
};

export const STATUS_COLORS: Record<IncidentStatus, string> = {
  open: "#ef4444",
  in_progress: "#f59e0b",
  resolved: "#10b981",
};
