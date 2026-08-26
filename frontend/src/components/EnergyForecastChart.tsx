import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useTheme } from "../context/ThemeContext";
import type { SeriesPoint } from "../types";

interface EnergyForecastChartProps {
  actual: SeriesPoint[];
  predicted: SeriesPoint[];
}

export default function EnergyForecastChart({ actual, predicted }: EnergyForecastChartProps) {
  const { theme } = useTheme();
  const gridColor = theme === "dark" ? "#25304a" : "#e2e8f0";
  const tickColor = theme === "dark" ? "#6b7690" : "#94a3b8";
  const tooltipBg = theme === "dark" ? "#141a2e" : "#ffffff";
  const tooltipText = theme === "dark" ? "#eef1f8" : "#0f1729";

  if (actual.length === 0 && predicted.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-dashed border-slate-200 text-sm text-slate-400 dark:border-white/10 dark:text-slate-500"
        style={{ height: 220 }}
      >
        Todavía no hay datos suficientes
      </div>
    );
  }

  const label = (iso: string) =>
    new Date(iso).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });

  const actualPoints = actual.map((p) => ({
    label: label(p.timestamp),
    actual: p.value,
    predicted: null as number | null,
  }));

  // Conecta el pronostico con el ultimo punto real para que la linea no quede suelta.
  const bridge = actual.length > 0 ? [{ label: label(actual[actual.length - 1].timestamp), actual: null as number | null, predicted: actual[actual.length - 1].value }] : [];

  const predictedPoints = predicted.map((p) => ({
    label: label(p.timestamp),
    actual: null as number | null,
    predicted: p.value,
  }));

  const chartData = [...actualPoints, ...bridge, ...predictedPoints];

  return (
    <ResponsiveContainer width="100%" height={220}>
      <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id="grad-actual" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.35} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
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
          formatter={(value, name) => [
            value !== null ? `${value} kWh` : "—",
            name === "actual" ? "Real" : "Previsto",
          ]}
          contentStyle={{
            borderRadius: 8,
            borderColor: gridColor,
            fontSize: 12,
            backgroundColor: tooltipBg,
            color: tooltipText,
          }}
        />
        <Area
          type="monotone"
          dataKey="actual"
          stroke="#3b82f6"
          fill="url(#grad-actual)"
          strokeWidth={2}
          connectNulls={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="predicted"
          stroke={tickColor}
          strokeWidth={2}
          strokeDasharray="4 4"
          dot={false}
          connectNulls
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
