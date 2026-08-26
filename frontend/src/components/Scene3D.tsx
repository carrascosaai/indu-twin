import { Edges, Line, OrbitControls, Text } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import type { Building } from "../types";
import { convexHull, expandHull } from "../utils/geometry";
import { statusColor } from "./StatusBadge";

interface Scene3DProps {
  centerLat: number;
  centerLng: number;
  buildings: Building[];
}

const METERS_PER_DEGREE_LAT = 110_540;

function project(lat: number, lng: number, centerLat: number, centerLng: number) {
  const metersPerDegreeLng = 111_320 * Math.cos((centerLat * Math.PI) / 180);
  const x = (lng - centerLng) * metersPerDegreeLng;
  const z = (lat - centerLat) * METERS_PER_DEGREE_LAT;
  // Escala de metros reales a unidades de escena manejables.
  return { x: x * 0.15, z: -z * 0.15 };
}

/** Perimetro del poligono industrial en el suelo: envolvente convexa de las
 * naves con un pequeno margen alrededor. */
function groundBoundary(points: { x: number; z: number }[]): [number, number, number][] {
  if (points.length < 3) return points.map((p) => [p.x, 0.01, p.z]);
  const hull = convexHull(points.map((p) => [p.x, p.z]));
  const expanded = expandHull(hull, 2.2);
  const withHeight = expanded.map(([x, z]) => [x, 0.01, z] as [number, number, number]);
  return [...withHeight, withHeight[0]];
}

function BuildingBlock({ building, x, z }: { building: Building; x: number; z: number }) {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const height = Math.max(1.2, Math.min(6, Math.sqrt(building.area_m2) / 12));
  const color = statusColor(building.status);
  const footprint = Math.max(1.4, Math.min(3.2, Math.sqrt(building.area_m2) / 22));
  const roofHeight = footprint * 0.28;

  const handleClick = (e: { stopPropagation: () => void }) => {
    e.stopPropagation();
    navigate(`/building/${building.id}`);
  };
  const handleOver = (e: { stopPropagation: () => void }) => {
    e.stopPropagation();
    document.body.style.cursor = "pointer";
  };
  const handleOut = () => {
    document.body.style.cursor = "auto";
  };

  return (
    <group position={[x, 0, z]}>
      <mesh
        position={[0, height / 2, 0]}
        castShadow
        receiveShadow
        onClick={handleClick}
        onPointerOver={handleOver}
        onPointerOut={handleOut}
      >
        <boxGeometry args={[footprint, height, footprint]} />
        <meshStandardMaterial color={color} roughness={0.65} metalness={0.08} />
        <Edges color={isDark ? "#020617" : "#1e293b"} opacity={0.25} transparent />
      </mesh>
      <mesh
        position={[0, height + roofHeight / 2, 0]}
        castShadow
        onClick={handleClick}
        onPointerOver={handleOver}
        onPointerOut={handleOut}
      >
        <coneGeometry args={[footprint * 0.75, roofHeight, 4]} />
        <meshStandardMaterial color={isDark ? "#334155" : "#475569"} roughness={0.8} />
      </mesh>
      <Text
        position={[0, height + roofHeight + 0.45, 0]}
        fontSize={0.32}
        color={isDark ? "#cbd5e1" : "#334155"}
        anchorX="center"
        anchorY="bottom"
      >
        {building.code}
      </Text>
    </group>
  );
}

export default function Scene3D({ centerLat, centerLng, buildings }: Scene3DProps) {
  const positioned = useMemo(
    () =>
      buildings.map((b) => ({
        building: b,
        ...project(b.lat, b.lng, centerLat, centerLng),
      })),
    [buildings, centerLat, centerLng]
  );

  const boundary = useMemo(() => groundBoundary(positioned.map((p) => ({ x: p.x, z: p.z }))), [positioned]);
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const bgColor = isDark ? "#0a0e1a" : "#eef2f9";
  const groundColor = isDark ? "#141a2e" : "#f1f5f9";
  const gridMajor = isDark ? "#2a3452" : "#cbd5e1";
  const gridMinor = isDark ? "#1c2338" : "#e2e8f0";

  return (
    <Canvas
      shadows
      camera={{ position: [14, 13, 14], fov: 45 }}
      className="rounded-lg"
      style={{ width: "100%", height: "100%", display: "block" }}
      resize={{ debounce: 0 }}
    >
      <color attach="background" args={[bgColor]} />
      <fog attach="fog" args={[bgColor, 25, 55]} />
      <ambientLight intensity={isDark ? 0.35 : 0.55} />
      <directionalLight
        position={[10, 16, 6]}
        intensity={isDark ? 0.9 : 1.2}
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-left={-20}
        shadow-camera-right={20}
        shadow-camera-top={20}
        shadow-camera-bottom={-20}
      />
      <hemisphereLight args={[isDark ? "#1e293b" : "#dbeafe", "#94a3b8", isDark ? 0.25 : 0.4]} />

      <gridHelper args={[40, 40, gridMajor, gridMinor]} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
        <planeGeometry args={[60, 60]} />
        <meshStandardMaterial color={groundColor} />
      </mesh>

      {boundary.length > 2 && (
        <Line points={boundary} color="#3b82f6" lineWidth={1.5} dashed={false} transparent opacity={0.6} />
      )}

      {positioned.map(({ building, x, z }) => (
        <BuildingBlock key={building.id} building={building} x={x} z={z} />
      ))}

      <OrbitControls
        enableDamping
        dampingFactor={0.1}
        minDistance={6}
        maxDistance={45}
        maxPolarAngle={Math.PI / 2.1}
      />
    </Canvas>
  );
}
