import type { ReactNode } from "react";

interface TabSwitcherProps<T extends string> {
  value: T;
  onChange: (value: T) => void;
  options: { value: T; label: string; icon?: ReactNode }[];
}

export default function TabSwitcher<T extends string>({ value, onChange, options }: TabSwitcherProps<T>) {
  return (
    <div className="inline-flex rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 p-0.5 text-xs">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 font-medium transition ${
            value === opt.value
              ? "text-slate-900 dark:text-slate-50 shadow-sm"
              : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
          }`}
          style={value === opt.value ? { backgroundColor: "var(--surface)" } : undefined}
        >
          {opt.icon}
          {opt.label}
        </button>
      ))}
    </div>
  );
}
