import { useState } from "react";
import { createBuilding } from "../api/client";
import { useToast } from "../context/ToastContext";
import Modal from "./Modal";

function errorMessage(err: unknown, fallback: string): string {
  return (
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback
  );
}

interface NewBuildingModalProps {
  polygonId: number;
  defaultLat: number;
  defaultLng: number;
  onClose: () => void;
  onCreated: () => void;
}

export default function NewBuildingModal({
  polygonId,
  defaultLat,
  defaultLng,
  onClose,
  onCreated,
}: NewBuildingModalProps) {
  const { showToast } = useToast();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [buildingType, setBuildingType] = useState("producción");
  const [areaM2, setAreaM2] = useState("1000");
  const [lat, setLat] = useState(String(defaultLat));
  const [lng, setLng] = useState(String(defaultLng));
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = name.trim() && code.trim() && !Number.isNaN(Number(lat)) && !Number.isNaN(Number(lng));

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await createBuilding(polygonId, {
        name: name.trim(),
        code: code.trim(),
        building_type: buildingType,
        lat: Number(lat),
        lng: Number(lng),
        area_m2: Number(areaM2) || 0,
      });
      showToast("Nave creada, ya generando datos");
      onCreated();
      onClose();
    } catch (err) {
      showToast(errorMessage(err, "No se pudo crear la nave"), "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title="Nueva nave" onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Nombre</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nave D4 - Almacén Frío"
            className="input w-full"
            autoFocus
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Código</label>
            <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="D4" className="input w-full" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Tipo</label>
            <select value={buildingType} onChange={(e) => setBuildingType(e.target.value)} className="input w-full">
              <option value="producción">Producción</option>
              <option value="almacén">Almacén</option>
              <option value="logística">Logística</option>
              <option value="taller">Taller</option>
            </select>
          </div>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Superficie (m²)</label>
          <input
            type="number"
            value={areaM2}
            onChange={(e) => setAreaM2(e.target.value)}
            className="input w-full"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Latitud</label>
            <input
              type="number"
              step="0.0001"
              value={lat}
              onChange={(e) => setLat(e.target.value)}
              className="input w-full"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Longitud</label>
            <input
              type="number"
              step="0.0001"
              value={lng}
              onChange={(e) => setLng(e.target.value)}
              className="input w-full"
            />
          </div>
        </div>
        <p className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
          Se rellenan con el centro del polígono — ajústalas si conoces la ubicación exacta.
        </p>

        <button
          onClick={handleSubmit}
          disabled={!canSubmit || submitting}
          className="btn btn-primary w-full py-2 text-sm disabled:opacity-50"
        >
          {submitting ? "Creando..." : "Crear nave"}
        </button>
      </div>
    </Modal>
  );
}
