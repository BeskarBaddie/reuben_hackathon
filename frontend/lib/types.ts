export type BoundaryGeometry = {
  type: "Polygon";
  coordinates: number[][][];
};

export type FarmCreatePayload = {
  name: string;
  crop: string;
  boundary: BoundaryGeometry;
  planting_date: string | null;
  irrigation_type: string;
  notes: string | null;
};

export type FarmRead = {
  id: string;
  owner_id: string;
  name: string;
  crop: string;
  planting_date: string | null;
  irrigation_type: string;
  area_hectares: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type FarmCreatedResponse = {
  farm: FarmRead;
  next_step: string;
};

export type AnalysisQueuedResponse = {
  analysis_id: string;
  status: "queued" | "processing" | "completed" | "failed";
};

export type AnalysisRead = {
  id: string;
  farm_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  ndvi: number | null;
  vegetation_health: string | null;
  vegetation_trend: string | null;
  water_stress: string | null;
  image_date: string | null;
  source: string | null;
  evidence: Record<string, unknown> | null;
  climate_season_start: string | null;
  climate_season_end: string | null;
  rainfall_this_season_mm: number | null;
  rainfall_historical_average_mm: number | null;
  rainfall_anomaly_percent: number | null;
  temperature_this_season_c: number | null;
  temperature_historical_average_c: number | null;
  temperature_anomaly_c: number | null;
  climate_signal: string | null;
  climate_source: string | null;
  climate_evidence: Record<string, unknown> | null;
  drought_score: number | null;
  drought_level: string | null;
  drought_drivers: string[] | null;
  flood_score: number | null;
  flood_level: string | null;
  flood_drivers: string[] | null;
  heat_score: number | null;
  heat_level: string | null;
  heat_drivers: string[] | null;
  overall_risk_level: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type RecommendationAction = {
  priority: number;
  action: string;
  reason: string;
  evidence: string[];
};

export type RecommendationRead = {
  id: string;
  analysis_id: string;
  provider: string;
  model: string | null;
  prompt_version: string;
  evidence_snapshot: Record<string, unknown>;
  output: {
    summary: string;
    actions: RecommendationAction[];
  };
  created_at: string;
};
