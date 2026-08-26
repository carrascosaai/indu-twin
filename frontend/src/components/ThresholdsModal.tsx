import { useState } from "react";
import { updateBuildingThresholds } from "../api/client";
import { useDefaultThresholds } from "../hooks/useApi";
import { useToast } from "../context/ToastContext";
import type { Building, BuildingThresholds } from "../types";
import Modal from "./Modal";

interface ThresholdsModalProps {
  building: Building;
  onClose: () => void;
  onSaved: () => void;
}

type FieldKey = keyof BuildingThresholds;

interface FieldRow {
  warningKey: FieldKey;
  criticalKey: FieldKey;
  label: string;
  unit: string;
  /** Los campos de energia se editan en % en la UI pero se guardan como fraccion (0-1). */
  isPercent?: boolean;
}

const ROWS: FieldRow[] = [
  { warningKey: "temp_warning", criticalKey: "temp_critical", label: "Temperatura", unit: "°C" },
  { warningKey: "vibration_warning", criticalKey: "vibration_critical", label: "Vibración", unit: "mm/s" },
  { warningKey: "humidity_warning", criticalKey: "humidity_critical", label: "Humedad", unit: "%" },
  {
    warningKey: "energy_anomaly_warning_pct",
    criticalKey: "energy_anomaly_critical_pct",
    label: "Anomalía de consumo",
    unit: "% sobre la media",
    isPercent: true,
  },
];

function toDisplay(value: number | null, isPercent?: boolean): string {
  if (value === null) return "";
  return isPercent ? String(Math.round(value * 100)) : String(value);
}

function toStored(raw: string, isPercent?: boolean): number | null {
  if (raw.trim() === "") return null;
  const n = Number(raw);
  if (Number.isNaN(n)) return null;
  return isPercent ? n / 100 : n;
}

export default function ThresholdsModal({ building, onClose, onSaved }: ThresholdsModalProps) {
  const { data: defaults } = useDefaultThresholds();
  const { showToast } = useToast();
  const [values, setValues] = useState<Record<FieldKey, string>>({
    temp_warning: toDisplay(building.temp_warning),
    temp_critical: toDisplay(building.temp_critical),
    vibration_warning: toDisplay(building.vibration_warning),
    vibration_critical: toDisplay(building.vibration_critical),
    humidity_warning: toDisplay(building.humidity_warning),
    humidity_critical: toDisplay(building.humidity_critical),
    energy_anomaly_warning_pct: toDisplay(building.energy_anomaly_warning_pct, true),
    energy_anomaly_critical_pct: toDisplay(building.energy_anomaly_critical_pct, true),
  });
  const [isSaving, setIsSaving] = useState(false);

  const setField = (key: FieldKey, raw: string) => setValues((v) => ({ ...v, [key]: raw }));

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const payload: BuildingThresholds = {
        temp_warning: toStored(values.temp_warning),
        temp_critical: toStored(values.temp_critical),
        vibration_warning: toStored(values.vibration_warning),
        vibration_critical: toStored(values.vibration_critical),
        humidity_warning: toStored(values.humidity_warning),
        humidity_critical: toStored(values.humidity_critical),
        energy_anomaly_warning_pct: toStored(values.energy_anomaly_warning_pct, true),
        energy_anomaly_critical_pct: toStored(values.energy_anomaly_critical_pct, true),
      };
      await updateBuildingThresholds(building.id, payload);
      showToast("Umbrales actualizados");
      onSaved();
      onClose();
    } catch {
      showToast("No se pudieron guardar los umbrales", "error");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal title={`Umbrales de alerta · ${building.code}`} onClose={onClose}>
      <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">
        Deja un campo vacío para usar el valor global por defecto. Útil para naves con procesos
        especiales (hornos, cámaras frigoríficas...) que no deberían disparar alertas constantes.
      </p>
      <div className="space-y-4">
        {ROWS.map((row) => {
          const defaultWarning = defaults?.[row.warningKey];
          const defaultCritical = defaults?.[row.criticalKey];
          return (
            <div key={row.warningKey}>
              <p className="mb-1 text-xs font-medium text-slate-700 dark:text-slate-300">
                {row.label} <span className="text-slate-400 dark:text-slate-500">({row.unit})</span>
              </p>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <input
                    type="number"
                    value={values[row.warningKey]}
                    onChange={(e) => setField(row.warningKey, e.target.value)}
                    placeholder={
                      defaultWarning !== undefined
                        ? String(row.isPercent ? Math.round(defaultWarning * 100) : defaultWarning)
                        : "aviso"
                    }
                    className="input w-full text-xs"
                  />
                  <p className="mt-0.5 text-[10px] text-slate-400 dark:text-slate-500">Aviso</p>
                </div>
                <div>
                  <input
                    type="number"
                    value={values[row.criticalKey]}
                    onChange={(e) => setField(row.criticalKey, e.target.value)}
                    placeholder={
                      defaultCritical !== undefined
                        ? String(row.isPercent ? Math.round(defaultCritical * 100) : defaultCritical)
                        : "crítico"
                    }
                    className="input w-full text-xs"
                  />
                  <p className="mt-0.5 text-[10px] text-slate-400 dark:text-slate-500">Crítico</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-5 flex justify-end gap-2">
        <button onClick={onClose} className="btn btn-secondary px-3 py-1.5 text-xs">
          Cancelar
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="btn btn-primary px-3 py-1.5 text-xs disabled:opacity-60"
        >
          {isSaving ? "Guardando..." : "Guardar umbrales"}
        </button>
      </div>
    </Modal>
  );
}
