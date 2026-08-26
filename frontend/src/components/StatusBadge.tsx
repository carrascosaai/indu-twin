import Pill from "./Pill";
import type { BuildingStatus } from "../types";

const LABELS: Record<BuildingStatus, string> = {
  normal: "Normal",
  warning: "Alerta",
  critical: "Crítico",
};

export default function StatusBadge({ status }: { status: BuildingStatus }) {
  return <Pill color={statusColor(status)} label={LABELS[status]} pulse={status === "critical"} />;
}

export function statusColor(status: BuildingStatus): string {
  if (status === "critical") return "#ef4444";
  if (status === "warning") return "#f59e0b";
  return "#10b981";
}
