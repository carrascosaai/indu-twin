export type BuildingStatus = "normal" | "warning" | "critical";
export type SensorType = "temperature" | "energy" | "vibration" | "humidity";
export type AlertSeverity = "warning" | "critical";
export type AlertType = "threshold" | "anomaly";
export type AlertStatus = "active" | "resolved";
export type IncidentPriority = "low" | "medium" | "high";
export type IncidentStatus = "open" | "in_progress" | "resolved";
export type UserRole = "admin" | "viewer" | "tenant";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  building_id: number | null;
  created_at: string;
}

export interface Polygon {
  id: number;
  name: string;
  address: string | null;
  center_lat: number;
  center_lng: number;
  created_at: string;
}

export interface Building {
  id: number;
  polygon_id: number;
  name: string;
  code: string;
  building_type: string;
  lat: number;
  lng: number;
  area_m2: number;
  status: BuildingStatus;
  created_at: string;
  temp_warning: number | null;
  temp_critical: number | null;
  vibration_warning: number | null;
  vibration_critical: number | null;
  humidity_warning: number | null;
  humidity_critical: number | null;
  energy_anomaly_warning_pct: number | null;
  energy_anomaly_critical_pct: number | null;
}

export interface BuildingWithPolygon extends Building {
  polygon_name: string;
}

export interface BuildingThresholds {
  temp_warning: number | null;
  temp_critical: number | null;
  vibration_warning: number | null;
  vibration_critical: number | null;
  humidity_warning: number | null;
  humidity_critical: number | null;
  energy_anomaly_warning_pct: number | null;
  energy_anomaly_critical_pct: number | null;
}

export type DefaultThresholds = { [K in keyof BuildingThresholds]: number };

export interface SensorLatest {
  id: number;
  building_id: number;
  sensor_type: SensorType;
  name: string;
  unit: string;
  is_simulated: boolean;
  latest_value: number | null;
  latest_timestamp: string | null;
}

export interface SensorReading {
  id: number;
  value: number;
  timestamp: string;
}

export interface Alert {
  id: number;
  building_id: number;
  sensor_id: number | null;
  severity: AlertSeverity;
  alert_type: AlertType;
  message: string;
  value: number | null;
  threshold: number | null;
  status: AlertStatus;
  created_at: string;
  resolved_at: string | null;
}

export interface Incident {
  id: number;
  building_id: number;
  title: string;
  description: string | null;
  priority: IncidentPriority;
  status: IncidentStatus;
  created_at: string;
  resolved_at: string | null;
}

export interface SeriesPoint {
  timestamp: string;
  value: number;
}

export interface BuildingRankingItem {
  building_id: number;
  name: string;
  total_energy_kwh: number;
  efficiency_kwh_per_m2: number | null;
  efficiency_score: number;
}

export interface PolygonDashboard {
  polygon: Polygon;
  building_count: number;
  total_energy_kwh_24h: number;
  energy_trend_pct: number | null;
  predicted_energy_kwh_24h: number | null;
  active_alerts_count: number;
  overall_status: BuildingStatus;
  energy_series: SeriesPoint[];
  temperature_series: SeriesPoint[];
  predicted_energy_series: SeriesPoint[];
  ranking: BuildingRankingItem[];
  recent_alerts: Alert[];
}

export interface EnergyGoal {
  id: number;
  polygon_id: number;
  building_id: number | null;
  title: string;
  target_reduction_pct: number;
  baseline_kwh: number;
  baseline_days: number;
  start_date: string;
  end_date: string;
  created_at: string;
  current_kwh: number;
  target_kwh: number;
  progress_pct: number;
  is_on_track: boolean;
  days_remaining: number;
}

export interface BuildingDashboard {
  building: Building;
  sensors: SensorLatest[];
  active_alerts: Alert[];
  incidents: Incident[];
  efficiency_kwh_per_m2: number | null;
  efficiency_score: number;
  polygon_avg_kwh_per_m2: number | null;
  predicted_energy_kwh_24h: number | null;
  maintenance_risk_score: number;
  maintenance_risk_label: string;
}
