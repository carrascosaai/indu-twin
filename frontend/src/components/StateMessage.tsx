interface StateMessageProps {
  title: string;
  description?: string;
  variant?: "loading" | "error" | "empty";
  action?: { label: string; onClick: () => void };
}

const ICONS: Record<NonNullable<StateMessageProps["variant"]>, string> = {
  loading: "⏳",
  error: "⚠️",
  empty: "📭",
};

export default function StateMessage({
  title,
  description,
  variant = "empty",
  action,
}: StateMessageProps) {
  return (
    <div
      className="flex h-full min-h-[240px] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-200 dark:border-white/10 p-8 text-center"
      style={{ backgroundColor: "var(--surface)" }}
    >
      <span className="text-2xl">{ICONS[variant]}</span>
      <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{title}</p>
      {description && <p className="max-w-sm text-xs text-slate-400 dark:text-slate-500">{description}</p>}
      {action && (
        <button onClick={action.onClick} className="btn btn-primary mt-2 px-3 py-1.5 text-xs">
          {action.label}
        </button>
      )}
    </div>
  );
}
