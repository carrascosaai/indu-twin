import { ArrowDown, ArrowUp } from "lucide-react";
import type { ReactNode } from "react";

interface KpiCardProps {
  label: string;
  value: ReactNode;
  sublabel?: string;
  accent?: "default" | "warning" | "critical" | "success";
  icon?: ReactNode;
  trendPct?: number | null;
  trendInverse?: boolean;
}

const TINTS: Record<string, string> = {
  default: "var(--accent)",
  warning: "#d97706",
  critical: "#dc2626",
  success: "#059669",
};

export default function KpiCard({
  label,
  value,
  sublabel,
  accent = "default",
  icon,
  trendPct,
  trendInverse,
}: KpiCardProps) {
  const hasTrend = trendPct !== undefined && trendPct !== null;
  const isUp = hasTrend && trendPct! > 0;
  const isGood = hasTrend ? (trendInverse ? !isUp : isUp) : false;
  const tintColor = TINTS[accent];
  const valueColor = accent === "default" ? "var(--text-primary)" : tintColor;

  return (
    <div className="card card-interactive relative overflow-hidden p-5">
      <div
        className="absolute inset-x-0 top-0 h-0.5 opacity-70"
        style={{ backgroundColor: tintColor }}
      />
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
          {label}
        </p>
        {icon && (
          <span
            className="flex h-8 w-8 items-center justify-center rounded-lg"
            style={{ backgroundColor: `color-mix(in srgb, ${tintColor} 12%, var(--surface))`, color: tintColor }}
          >
            {icon}
          </span>
        )}
      </div>
      <p
        className="font-display mt-2 text-3xl font-semibold tracking-tight"
        style={{ color: valueColor }}
      >
        {value}
      </p>
      <div className="mt-1.5 flex items-center gap-1.5">
        {hasTrend && Math.abs(trendPct!) >= 0.5 && (
          <span
            className="inline-flex items-center gap-0.5 text-xs font-semibold"
            style={{ color: isGood ? "#059669" : "#dc2626" }}
          >
            {isUp ? <ArrowUp size={12} /> : <ArrowDown size={12} />}
            {Math.abs(trendPct!).toFixed(0)}%
          </span>
        )}
        {sublabel && (
          <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>
            {sublabel}
          </p>
        )}
      </div>
    </div>
  );
}
