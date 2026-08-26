interface PillProps {
  color: string;
  label: string;
  dot?: boolean;
  pulse?: boolean;
}

/** Insignia base: fondo tenue derivado del color, texto en el tono fuerte.
 * Todas las insignias de estado/eficiencia/riesgo comparten este mismo
 * tratamiento visual para que la app se sienta como un unico sistema. */
export default function Pill({ color, label, dot = true, pulse = false }: PillProps) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{ backgroundColor: `color-mix(in srgb, ${color} 16%, var(--surface))`, color }}
    >
      {dot && (
        <span className="relative flex h-1.5 w-1.5 shrink-0">
          {pulse && (
            <span
              className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60"
              style={{ backgroundColor: color }}
            />
          )}
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
        </span>
      )}
      {label}
    </span>
  );
}
