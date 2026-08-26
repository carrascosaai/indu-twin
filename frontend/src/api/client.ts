import axios from "axios";
import type {
  Alert,
  Building,
  BuildingDashboard,
  BuildingThresholds,
  BuildingWithPolygon,
  DefaultThresholds,
  Incident,
  Polygon,
  PolygonDashboard,
  SensorReading,
  User,
  UserRole,
} from "../types";
import { clearStoredToken, getStoredToken } from "../auth/token";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8001";

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearStoredToken();
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

function downloadBlob(path: string, filename: string) {
  return api.get(path, { responseType: "blob" }).then((res) => {
    const url = URL.createObjectURL(res.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  });
}

export const downloadPolygonAlertsCsv = (polygonId: number) =>
  downloadBlob(`/api/polygons/${polygonId}/export/alerts.csv`, `alertas_poligono_${polygonId}.csv`);

export const downloadBuildingReadingsCsv = (buildingId: number, hours: number) =>
  downloadBlob(
    `/api/buildings/${buildingId}/export/readings.csv?hours=${hours}`,
    `lecturas_nave_${buildingId}.csv`
  );

export const fetchPolygons = () => api.get<Polygon[]>("/api/polygons").then((r) => r.data);

export const fetchPolygon = (id: number) =>
  api.get<Polygon>(`/api/polygons/${id}`).then((r) => r.data);

export const fetchPolygonDashboard = (id: number) =>
  api.get<PolygonDashboard>(`/api/polygons/${id}/dashboard`).then((r) => r.data);

export const fetchBuildings = (polygonId: number) =>
  api.get<Building[]>(`/api/polygons/${polygonId}/buildings`).then((r) => r.data);

export const createBuilding = (
  polygonId: number,
  payload: {
    name: string;
    code: string;
    building_type: string;
    lat: number;
    lng: number;
    area_m2: number;
  }
) => api.post<Building>(`/api/polygons/${polygonId}/buildings`, payload).then((r) => r.data);

export const createPolygon = (payload: {
  name: string;
  address?: string;
  center_lat: number;
  center_lng: number;
}) => api.post<Polygon>("/api/polygons", payload).then((r) => r.data);

export const deleteBuilding = (buildingId: number) => api.delete(`/api/buildings/${buildingId}`);

export const deletePolygon = (polygonId: number) => api.delete(`/api/polygons/${polygonId}`);

export const fetchBuildingDashboard = (buildingId: number) =>
  api.get<BuildingDashboard>(`/api/buildings/${buildingId}/dashboard`).then((r) => r.data);

export const fetchDefaultThresholds = () =>
  api.get<DefaultThresholds>("/api/buildings/thresholds/defaults").then((r) => r.data);

export const updateBuildingThresholds = (buildingId: number, payload: BuildingThresholds) =>
  api.patch<Building>(`/api/buildings/${buildingId}/thresholds`, payload).then((r) => r.data);

export const fetchSensorReadings = (sensorId: number, hours = 24) =>
  api
    .get<SensorReading[]>(`/api/sensors/${sensorId}/readings`, { params: { hours } })
    .then((r) => r.data);

export const fetchSensorApiKey = (sensorId: number) =>
  api
    .get<{ sensor_id: number; api_key: string }>(`/api/sensors/${sensorId}/api-key`)
    .then((r) => r.data);

export const regenerateSensorApiKey = (sensorId: number) =>
  api
    .post<{ sensor_id: number; api_key: string }>(`/api/sensors/${sensorId}/api-key/regenerate`)
    .then((r) => r.data);

export const fetchAlerts = (params: { polygon_id?: number; building_id?: number; status?: string }) =>
  api.get<Alert[]>("/api/alerts", { params }).then((r) => r.data);

export const fetchPolygonIncidents = (polygonId: number, status?: string) =>
  api
    .get<Incident[]>(`/api/polygons/${polygonId}/incidents`, { params: { status } })
    .then((r) => r.data);

export const resolveAlert = (alertId: number) =>
  api.patch<Alert>(`/api/alerts/${alertId}/resolve`).then((r) => r.data);

export const createIncident = (
  buildingId: number,
  payload: { title: string; description?: string; priority?: string }
) => api.post(`/api/buildings/${buildingId}/incidents`, payload).then((r) => r.data);

export const updateIncident = (incidentId: number, payload: { status?: string }) =>
  api.patch(`/api/incidents/${incidentId}`, payload).then((r) => r.data);

export const fetchSetupStatus = () =>
  api.get<{ needs_setup: boolean }>("/api/auth/setup-status").then((r) => r.data);

export const registerFirstAdmin = (payload: {
  email: string;
  password: string;
  full_name: string;
}) => api.post<{ access_token: string }>("/api/auth/register", payload).then((r) => r.data);

export const forgotPassword = (email: string) =>
  api.post<{ message: string }>("/api/auth/forgot-password", { email }).then((r) => r.data);

export const resetPassword = (token: string, newPassword: string) =>
  api
    .post<{ message: string }>("/api/auth/reset-password", {
      token,
      new_password: newPassword,
    })
    .then((r) => r.data);

export const fetchUsers = () => api.get<User[]>("/api/users").then((r) => r.data);

export const fetchAllBuildings = () =>
  api.get<BuildingWithPolygon[]>("/api/buildings").then((r) => r.data);

export interface PlanStatus {
  plan: string;
  polygons: { used: number; limit: number | null };
  buildings: { used: number; limit: number | null };
  users: { used: number; limit: number | null };
}

export const fetchPlanStatus = () => api.get<PlanStatus>("/api/plan").then((r) => r.data);

export const createUser = (payload: {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
  building_id?: number | null;
}) => api.post<User>("/api/users", payload).then((r) => r.data);

export const updateUser = (
  userId: number,
  payload: { role?: UserRole; building_id?: number | null }
) => api.patch<User>(`/api/users/${userId}`, payload).then((r) => r.data);

export const deleteUser = (userId: number) => api.delete(`/api/users/${userId}`);

export default api;
