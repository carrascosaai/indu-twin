import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useTheme } from "../context/ThemeContext";
import type { SeriesPoint } from "../types";

interface SeriesChartProps {
  data: SeriesPoint[];
  color: string;
  unit: string;
  /** Cuando el rango cubre mas de un dia, se incluye la fecha en las etiquetas. */
  spansMultipleDays?: boolean;
}

export default function SeriesChart({ data, color, unit, spansMultipleDays }: SeriesChartProps) {
  const { theme } = useTheme();
  const gridColor = theme === "dark" ? "#25304a" : "#e2e8f0";
  const tickColor = theme === "dark" ? "#6b7690" : "#94a3b8";
  const tooltipBg = theme === "dark" ? "#141a2e" : "#ffffff";
  const tooltipText = theme === "dark" ? "#eef1f8" : "#0f1729";

  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-dashed border-slate-200 text-sm text-slate-400 dark:border-white/10 dark:text-slate-500"
        style={{ height: 220 }}
      >
        Todavía no hay datos suficientes
      </div>
    );
  }

  const chartData = data.map((p) => {
    const date = new Date(p.timestamp);
    const label = spansMultipleDays
      ? date.toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit" }) +
        " " +
        date.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })
      : date.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
    return { ...p, label };
  });

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.35} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: tickColor }}
          minTickGap={30}
          axisLine={false}
          tickLine={false}
        />
        <YAxis tick={{ fontSize: 11, fill: tickColor }} axisLine={false} tickLine={false} width={40} />
        <Tooltip
          formatter={(value) => [`${value ?? "—"} ${unit}`, ""]}
          contentStyle={{
            borderRadius: 8,
            borderColor: gridColor,
            fontSize: 12,
            backgroundColor: tooltipBg,
            color: tooltipText,
          }}
        />
        <Area type="monotone" dataKey="value" stroke={color} fill={`url(#grad-${color})`} strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
