import { useQuery } from "@tanstack/react-query";
import {
  fetchAlerts,
  fetchBuildingDashboard,
  fetchBuildings,
  fetchDefaultThresholds,
  fetchGoals,
  fetchPlanStatus,
  fetchPolygonDashboard,
  fetchPolygonIncidents,
  fetchPolygons,
  fetchSensorReadings,
} from "../api/client";

const LIVE_REFRESH_MS = 10_000;

// No tiene sentido seguir sondeando cada 10s un endpoint que ya sabemos que
// esta prohibido (403) o no existe (404): no se va a arreglar solo.
function liveRefetchInterval(query: { state: { error: unknown } }): number | false {
  const status = (query.state.error as { response?: { status?: number } } | null)?.response
    ?.status;
  if (status && status >= 400 && status < 500) return false;
  return LIVE_REFRESH_MS;
}

export const usePolygons = (enabled = true) =>
  useQuery({ queryKey: ["polygons"], queryFn: fetchPolygons, enabled });

export const usePolygonDashboard = (polygonId: number | undefined) =>
  useQuery({
    queryKey: ["polygon-dashboard", polygonId],
    queryFn: () => fetchPolygonDashboard(polygonId as number),
    enabled: polygonId !== undefined,
    refetchInterval: liveRefetchInterval,
  });

export const useBuildings = (polygonId: number | undefined) =>
  useQuery({
    queryKey: ["buildings", polygonId],
    queryFn: () => fetchBuildings(polygonId as number),
    enabled: polygonId !== undefined,
    refetchInterval: liveRefetchInterval,
  });

export const useBuildingDashboard = (buildingId: number | undefined) =>
  useQuery({
    queryKey: ["building-dashboard", buildingId],
    queryFn: () => fetchBuildingDashboard(buildingId as number),
    enabled: buildingId !== undefined,
    refetchInterval: liveRefetchInterval,
  });

export const useSensorReadings = (sensorId: number | undefined, hours = 24) =>
  useQuery({
    queryKey: ["sensor-readings", sensorId, hours],
    queryFn: () => fetchSensorReadings(sensorId as number, hours),
    enabled: sensorId !== undefined,
    refetchInterval: liveRefetchInterval,
  });

export const useAlerts = (params: { polygon_id?: number; building_id?: number; status?: string }) =>
  useQuery({
    queryKey: ["alerts", params],
    queryFn: () => fetchAlerts(params),
    refetchInterval: liveRefetchInterval,
  });

export const usePolygonIncidents = (polygonId: number | undefined, status?: string) =>
  useQuery({
    queryKey: ["polygon-incidents", polygonId, status],
    queryFn: () => fetchPolygonIncidents(polygonId as number, status),
    enabled: polygonId !== undefined,
    refetchInterval: liveRefetchInterval,
  });

export const useDefaultThresholds = () =>
  useQuery({
    queryKey: ["default-thresholds"],
    queryFn: fetchDefaultThresholds,
    staleTime: Infinity,
  });

export const usePlanStatus = () =>
  useQuery({
    queryKey: ["plan-status"],
    queryFn: fetchPlanStatus,
    staleTime: 30_000,
  });

export const useGoals = (polygonId: number | undefined) =>
  useQuery({
    queryKey: ["goals", polygonId],
    queryFn: () => fetchGoals(polygonId as number),
    enabled: polygonId !== undefined,
    staleTime: 60_000,
  });
