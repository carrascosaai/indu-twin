import Pill from "./Pill";

function tier(score: number): { label: string; color: string } {
  if (score >= 70) return { label: "Eficiente", color: "#10b981" };
  if (score >= 40) return { label: "Media", color: "#f59e0b" };
  return { label: "Mejorable", color: "#ef4444" };
}

export default function EfficiencyBadge({ score }: { score: number }) {
  const { label, color } = tier(score);
  return <Pill color={color} label={`${label} · ${score}`} />;
}
