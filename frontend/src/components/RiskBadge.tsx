import Pill from "./Pill";

function tierColor(label: string): string {
  if (label === "Alto") return "#ef4444";
  if (label === "Medio") return "#f59e0b";
  return "#10b981";
}

export default function RiskBadge({ score, label }: { score: number; label: string }) {
  return <Pill color={tierColor(label)} label={`Riesgo ${label} · ${score}`} />;
}
