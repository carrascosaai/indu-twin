import { useState } from "react";
import { createPolygon } from "../api/client";
import { useToast } from "../context/ToastContext";
import Modal from "./Modal";

function errorMessage(err: unknown, fallback: string): string {
  return (
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback
  );
}

interface NewPolygonModalProps {
  onClose: () => void;
  onCreated: (polygonId: number) => void;
}

export default function NewPolygonModal({ onClose, onCreated }: NewPolygonModalProps) {
  const { showToast } = useToast();
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [lat, setLat] = useState("40.4168");
  const [lng, setLng] = useState("-3.7038");
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = name.trim() && !Number.isNaN(Number(lat)) && !Number.isNaN(Number(lng));

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      const polygon = await createPolygon({
        name: name.trim(),
        address: address.trim() || undefined,
        center_lat: Number(lat),
        center_lng: Number(lng),
      });
      showToast("Polígono creado");
      onCreated(polygon.id);
      onClose();
    } catch (err) {
      showToast(errorMessage(err, "No se pudo crear el polígono"), "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal title="Nuevo polígono industrial" onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Nombre</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Polígono Industrial Las Salinas"
            className="input w-full"
            autoFocus
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Dirección (opcional)</label>
          <input
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Ciudad, país"
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
          Coordenadas del centro del recinto — luego añade naves alrededor de este punto.
        </p>

        <button
          onClick={handleSubmit}
          disabled={!canSubmit || submitting}
          className="btn btn-primary w-full py-2 text-sm disabled:opacity-50"
        >
          {submitting ? "Creando..." : "Crear polígono"}
        </button>
      </div>
    </Modal>
  );
}
