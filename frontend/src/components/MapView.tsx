import L from "leaflet";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { MapContainer, Marker, Polygon, Popup, TileLayer } from "react-leaflet";
import type { Building } from "../types";
import { convexHull, expandHull } from "../utils/geometry";
import { statusColor } from "./StatusBadge";

const STATUS_LABELS: Record<Building["status"], string> = {
  normal: "Normal",
  warning: "Alerta",
  critical: "Crítico",
};

function buildingIcon(status: Building["status"]) {
  const color = statusColor(status);
  const pulse = status === "critical" ? "box-shadow:0 0 0 5px rgba(239,68,68,0.25);" : "";
  return L.divIcon({
    className: "",
    html: `<div class="building-marker" style="width:22px;height:22px;background:${color};${pulse}"></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}

interface MapViewProps {
  centerLat: number;
  centerLng: number;
  buildings: Building[];
}

export default function MapView({ centerLat, centerLng, buildings }: MapViewProps) {
  const navigate = useNavigate();

  const boundary = useMemo(() => {
    if (buildings.length < 3) return null;
    const hull = convexHull(buildings.map((b) => [b.lat, b.lng]));
    // Margen aproximado de ~40m alrededor de las naves exteriores.
    return expandHull(hull, 0.00035);
  }, [buildings]);

  return (
    <MapContainer center={[centerLat, centerLng]} zoom={16} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {boundary && (
        <Polygon
          positions={boundary}
          pathOptions={{ color: "#3b82f6", weight: 2, fillColor: "#3b82f6", fillOpacity: 0.06, dashArray: "6 4" }}
        />
      )}
      {buildings.map((b) => (
        <Marker
          key={b.id}
          position={[b.lat, b.lng]}
          icon={buildingIcon(b.status)}
          eventHandlers={{ click: () => navigate(`/building/${b.id}`) }}
        >
          <Popup>
            <div className="min-w-[160px] text-sm">
              <p className="font-semibold text-slate-800 dark:text-slate-200">{b.name}</p>
              <p className="text-slate-500 dark:text-slate-400">
                {b.code} · {b.building_type} · {b.area_m2.toLocaleString("es-ES")} m²
              </p>
              <p className="mt-1 font-medium" style={{ color: statusColor(b.status) }}>
                {STATUS_LABELS[b.status]}
              </p>
              <button
                className="mt-1.5 font-medium text-blue-600 underline"
                onClick={() => navigate(`/building/${b.id}`)}
              >
                Ver detalle
              </button>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
