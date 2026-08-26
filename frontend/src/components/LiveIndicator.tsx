import { useEffect, useState } from "react";

/** Punto verde parpadeante + "actualizado hace Xs", para que se note que
 * el dashboard tiene datos en vivo y no es una foto estatica. */
export default function LiveIndicator({ updatedAt }: { updatedAt: number }) {
  const [, forceTick] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => forceTick((t) => t + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  const seconds = Math.max(0, Math.round((Date.now() - updatedAt) / 1000));
  const label = seconds < 2 ? "actualizado ahora" : `actualizado hace ${seconds}s`;

  return (
    <span className="inline-flex items-center gap-1.5 text-[11px]" style={{ color: "var(--text-tertiary)" }}>
      <span className="relative flex h-1.5 w-1.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
      </span>
      {label}
    </span>
  );
}
