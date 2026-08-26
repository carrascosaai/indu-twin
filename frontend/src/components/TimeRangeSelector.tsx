export const TIME_RANGES = [
  { label: "24h", hours: 24 },
  { label: "7d", hours: 24 * 7 },
  { label: "30d", hours: 24 * 30 },
] as const;

interface TimeRangeSelectorProps {
  value: number;
  onChange: (hours: number) => void;
}

export default function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <div className="inline-flex rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 p-0.5 text-xs">
      {TIME_RANGES.map((r) => (
        <button
          key={r.hours}
          onClick={() => onChange(r.hours)}
          className={`rounded-md px-2.5 py-1 font-medium transition ${
            value === r.hours
              ? "text-slate-900 dark:text-slate-50 shadow-sm"
              : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
          }`}
          style={value === r.hours ? { backgroundColor: "var(--surface)" } : undefined}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}
