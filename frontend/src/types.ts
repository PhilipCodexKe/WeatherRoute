export interface WeatherCondition {
  wind_mph: number;
  wind_gusts_mph?: number;
  rain_in_per_hr: number;
  snow_in_per_hr: number;
  temperature_f?: number;
}

export interface CheckpointRisk {
  level: number; // 1 = Low, 2 = Moderate, 3 = High, 4 = Severe, 5 = No Travel
  label: string;
  base_level: number;
  load_adjustment?: string | null;
}

export interface Checkpoint {
  index: number;
  latitude: number;
  longitude: number;
  distance_miles: number;
  eta: string;
  segment_miles: number;
  weather: WeatherCondition;
  risk: CheckpointRisk;
}

export interface RouteSummary {
  total_miles: number;
  duration_hours: number;
  severe_miles: number;
  high_miles: number;
  moderate_miles: number;
  low_miles: number;
  no_travel_miles: number;
  no_travel_count: number;
  avg_risk: number;
}

export interface Coordinate {
  latitude: number;
  longitude: number;
}

export interface RouteOption {
  id: string;
  name: string;
  rank: number;
  is_recommended: boolean;
  recommendation_reason: string;
  distance_miles: number;
  duration_hours: number;
  summary: RouteSummary;
  geometry: Coordinate[];
  checkpoints: Checkpoint[];
}

export interface HeatmapGridPoint {
  latitude: number;
  longitude: number;
  risks: number[]; // 48 values representing hourly risk levels (0-47 hours)
}

export interface TripAnalysisResponse {
  origin: Coordinate;
  destination: Coordinate;
  departure_time: string;
  load_weight_lbs: number;
  sampling_interval_miles: number;
  routes: RouteOption[];
  corridor_heatmap: HeatmapGridPoint[];
}

export interface GeocodeResult {
  place_name: string;
  latitude: number;
  longitude: number;
}
