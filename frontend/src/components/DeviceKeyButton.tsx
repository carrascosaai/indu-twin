import { Check, Copy, KeyRound, RefreshCw } from "lucide-react";
import { useState } from "react";
import { fetchSensorApiKey, regenerateSensorApiKey } from "../api/client";
import { useToast } from "../context/ToastContext";

/** Botón admin-only para ver/copiar/regenerar la API key que hay que
 * programar en el dispositivo físico (ESP32...) de este sensor, para que
 * pueda mandar lecturas a /api/ingest/reading. */
export default function DeviceKeyButton({ sensorId }: { sensorId: number }) {
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleOpen = async () => {
    const next = !open;
    setOpen(next);
    if (next && apiKey === null) {
      setIsLoading(true);
      try {
        const data = await fetchSensorApiKey(sensorId);
        setApiKey(data.api_key);
      } catch {
        showToast("No se pudo obtener la clave del dispositivo", "error");
        setOpen(false);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleCopy = async () => {
    if (!apiKey) return;
    await navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleRegenerate = async () => {
    if (!window.confirm("La clave actual dejará de funcionar. ¿Regenerar?")) return;
    setIsLoading(true);
    try {
      const data = await regenerateSensorApiKey(sensorId);
      setApiKey(data.api_key);
      showToast("Clave regenerada");
    } catch {
      showToast("No se pudo regenerar la clave", "error");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={handleOpen}
        title="Clave del dispositivo (para el sensor físico)"
        className="rounded-md p-1 text-slate-400 dark:text-slate-500 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-white/10 dark:hover:text-slate-300"
      >
        <KeyRound size={13} strokeWidth={2} />
      </button>
      {open && (
        <div
          className="absolute right-0 top-full z-20 mt-1 w-64 rounded-lg p-3 text-left"
          style={{ backgroundColor: "var(--surface)", boxShadow: "var(--shadow-float)" }}
        >
          <p className="mb-1.5 text-[11px] font-medium text-slate-500 dark:text-slate-400">
            Clave para el dispositivo físico
          </p>
          {isLoading && !apiKey ? (
            <div className="h-6 animate-shimmer rounded" />
          ) : (
            <div className="flex items-center gap-1">
              <code className="flex-1 truncate rounded bg-slate-100 dark:bg-white/10 px-1.5 py-1 text-[11px] text-slate-700 dark:text-slate-300">
                {apiKey}
              </code>
              <button
                onClick={handleCopy}
                title="Copiar"
                className="rounded p-1 text-slate-400 transition hover:bg-slate-100 dark:hover:bg-white/10"
              >
                {copied ? <Check size={12} strokeWidth={2} /> : <Copy size={12} strokeWidth={2} />}
              </button>
            </div>
          )}
          <button
            onClick={handleRegenerate}
            disabled={isLoading}
            className="mt-2 flex items-center gap-1.5 text-[11px] font-medium text-slate-400 dark:text-slate-500 transition hover:text-red-600 disabled:opacity-50"
          >
            <RefreshCw size={11} strokeWidth={2} />
            Regenerar clave
          </button>
        </div>
      )}
    </div>
  );
}
