import { useState } from "react";
import { createGoal } from "../api/client";
import { useToast } from "../context/ToastContext";
import type { Building } from "../types";
import Modal from "./Modal";

function errorMessage(err: unknown, fallback: string): string {
  return (
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback
  );
}

interface NewGoalModalProps {
  polygonId: number;
  buildings: Building[];
  onClose: () => void;
  onCreated: () => void;
}

const DURATION_OPTIONS = [
  { value: 30, label: "1 mes" },
  { value: 90, label: "3 meses (trimestre)" },
  { value: 180, label: "6 meses" },
  { value: 365, label: "1 año" },
];

export default function NewGoalModal({ polygonId, buildings, onClose, onCreated }: NewGoalModalProps) {
  const { showToast } = useToast();
  const [title, setTitle] = useState("");
  const [targetPct, setTargetPct] = useState("10");
  const [durationDays, setDurationDays] = useState(90);
  const [buildingId, setBuildingId] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  const pct = Number(targetPct);
  const canSubmit = title.trim() && pct > 0 && pct < 100 && !submitting;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await createGoal(polygonId, {
        title: title.trim(),
        target_reduction_pct: pct,
        duration_days: durationDays,
        building_id: buildingId ? Number(buildingId) : null,
      });
      showToast("Objetivo creado");
      onCreated();
      onClose();
    } catch (err) {
      showToast(errorMessage(err, "No se pudo crear el objetivo"), "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title="Nuevo objetivo de consumo" onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">
            Nombre del objetivo
          </label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Reducir consumo del trimestre"
            className="input w-full"
            autoFocus
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">
              Reducción objetivo
            </label>
            <div className="relative">
              <input
                type="number"
                min={1}
                max={99}
                value={targetPct}
                onChange={(e) => setTargetPct(e.target.value)}
                className="input w-full pr-7"
              />
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 dark:text-slate-500">
                %
              </span>
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Duración</label>
            <select
              value={durationDays}
              onChange={(e) => setDurationDays(Number(e.target.value))}
              className="input w-full"
            >
              {DURATION_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Ámbito</label>
          <select value={buildingId} onChange={(e) => setBuildingId(e.target.value)} className="input w-full">
            <option value="">Todo el polígono</option>
            {buildings.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        </div>
        <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
          La línea base se calcula a partir del consumo de los últimos 30 días — el progreso se
          medirá contra ese punto de partida durante toda la vigencia del objetivo.
        </p>

        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="btn btn-primary w-full py-2 text-sm disabled:opacity-50"
        >
          {submitting ? "Creando..." : "Crear objetivo"}
        </button>
      </div>
    </Modal>
  );
}
