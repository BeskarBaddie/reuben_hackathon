"use client";

import dynamic from "next/dynamic";
import { Save } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { createFarm, generateRecommendations, getAnalysis, startAnalysis } from "@/lib/api";
import type { BoundaryGeometry, FarmCreatePayload } from "@/lib/types";

const BoundaryMap = dynamic(() => import("@/components/boundary-map"), { ssr: false });

const demoUserId = "11111111-1111-4111-8111-111111111111";

export default function Home() {
  const [boundary, setBoundary] = useState<BoundaryGeometry | null>(null);
  const [form, setForm] = useState({
    name: "",
    crop: "maize",
    plantingDate: "",
    irrigationType: "rainfed",
    notes: ""
  });

  const mutation = useMutation({
    mutationFn: (payload: FarmCreatePayload) => createFarm(payload, demoUserId)
  });
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const analysisQuery = useQuery({
    queryKey: ["analysis", analysisId],
    queryFn: () => getAnalysis(analysisId as string, demoUserId),
    enabled: Boolean(analysisId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "processing" || status === "queued" ? 1500 : false;
    }
  });
  const analysisMutation = useMutation({
    mutationFn: (farmId: string) => startAnalysis(farmId, demoUserId),
    onSuccess: (response) => setAnalysisId(response.analysis_id)
  });
  const recommendationMutation = useMutation({
    mutationFn: (id: string) => generateRecommendations(id, demoUserId)
  });

  const boundaryPreview = useMemo(
    () => (boundary ? JSON.stringify(boundary, null, 2) : ""),
    [boundary]
  );

  function updateField(name: string, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!boundary) {
      return;
    }

    mutation.mutate({
      name: form.name,
      crop: form.crop,
      planting_date: form.plantingDate || null,
      irrigation_type: form.irrigationType,
      notes: form.notes || null,
      boundary
    });
  }

  return (
    <main className="page-shell">
      <header className="topbar">
        <div className="brand">
          <strong>Climate Intelligence</strong>
          <span>Farm registration and boundary capture</span>
        </div>
        <span className="topbar-status">Sprint 1 modular monolith</span>
      </header>

      <section className="workspace">
        <aside className="panel form-panel">
          <div className="panel-header">
            <h1>Register Farm</h1>
            <p>Capture the core crop and boundary data needed before climate analysis starts.</p>
          </div>

          <form className="farm-form" onSubmit={submit}>
            <div className="field">
              <label htmlFor="name">Farm name</label>
              <input
                id="name"
                required
                value={form.name}
                onChange={(event) => updateField("name", event.target.value)}
                placeholder="Field A"
              />
            </div>

            <div className="field">
              <label htmlFor="crop">Crop</label>
              <input
                id="crop"
                required
                value={form.crop}
                onChange={(event) => updateField("crop", event.target.value)}
              />
            </div>

            <div className="field">
              <label htmlFor="plantingDate">Planting date</label>
              <input
                id="plantingDate"
                type="date"
                value={form.plantingDate}
                onChange={(event) => updateField("plantingDate", event.target.value)}
              />
            </div>

            <div className="field">
              <label htmlFor="irrigationType">Irrigation</label>
              <select
                id="irrigationType"
                value={form.irrigationType}
                onChange={(event) => updateField("irrigationType", event.target.value)}
              >
                <option value="rainfed">Rainfed</option>
                <option value="partial">Partial</option>
                <option value="full">Full</option>
                <option value="none">None</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="notes">Notes</label>
              <textarea
                id="notes"
                value={form.notes}
                onChange={(event) => updateField("notes", event.target.value)}
                placeholder="Soil condition, access constraints, farmer observations"
              />
            </div>

            <div className="submit-row">
              <button className="primary-button" type="submit" disabled={!boundary || mutation.isPending}>
                <Save size={17} aria-hidden />
                {mutation.isPending ? "Saving" : "Save farm"}
              </button>
              <span className="status-text">
                {boundary ? "Boundary ready" : "Draw a boundary first"}
              </span>
            </div>

            {mutation.isError ? (
              <p className="status-text error">{(mutation.error as Error).message}</p>
            ) : null}
            {mutation.isSuccess ? (
              <p className="status-text success">
                Saved {mutation.data.farm.name} ({mutation.data.farm.area_hectares} ha)
              </p>
            ) : null}

            {mutation.isSuccess ? (
              <button
                className="primary-button"
                type="button"
                disabled={analysisMutation.isPending}
                onClick={() => analysisMutation.mutate(mutation.data.farm.id)}
              >
                Run analysis
              </button>
            ) : null}

            {analysisMutation.isError ? (
              <p className="status-text error">{(analysisMutation.error as Error).message}</p>
            ) : null}

            {analysisQuery.data ? (
              <div className="analysis-result">
                <strong>Farm health report</strong>
                <span>Status: {analysisQuery.data.status}</span>
                <span>NDVI: {analysisQuery.data.ndvi ?? "pending"}</span>
                <span>Vegetation: {analysisQuery.data.vegetation_health ?? "pending"}</span>
                <span>Water stress: {analysisQuery.data.water_stress ?? "pending"}</span>
                <span>
                  Rainfall: {analysisQuery.data.rainfall_this_season_mm ?? "pending"} mm
                </span>
                <span>
                  Rainfall anomaly: {analysisQuery.data.rainfall_anomaly_percent ?? "pending"}%
                </span>
                <span>
                  Temperature anomaly: {analysisQuery.data.temperature_anomaly_c ?? "pending"} C
                </span>
                <span>Climate signal: {analysisQuery.data.climate_signal ?? "pending"}</span>
                <span>
                  Drought risk: {analysisQuery.data.drought_level ?? "pending"} (
                  {analysisQuery.data.drought_score ?? "pending"})
                </span>
                <span>
                  Flood risk: {analysisQuery.data.flood_level ?? "pending"} (
                  {analysisQuery.data.flood_score ?? "pending"})
                </span>
                <span>
                  Heat risk: {analysisQuery.data.heat_level ?? "pending"} (
                  {analysisQuery.data.heat_score ?? "pending"})
                </span>
                <span>Overall risk: {analysisQuery.data.overall_risk_level ?? "pending"}</span>
              </div>
            ) : null}

            {analysisQuery.data?.status === "completed" ? (
              <button
                className="primary-button"
                type="button"
                disabled={recommendationMutation.isPending}
                onClick={() => recommendationMutation.mutate(analysisQuery.data.id)}
              >
                Generate recommendations
              </button>
            ) : null}

            {recommendationMutation.data ? (
              <div className="analysis-result">
                <strong>Adaptation plan</strong>
                <span>{recommendationMutation.data.output.summary}</span>
                {recommendationMutation.data.output.actions.map((action) => (
                  <span key={action.priority}>
                    {action.priority}. {action.action}: {action.reason}
                  </span>
                ))}
              </div>
            ) : null}
          </form>
        </aside>

        <section className="panel map-panel">
          <div className="map-header">
            <h2>Boundary</h2>
            <span className="map-meta">Draw one polygon</span>
          </div>
          <div className="map-wrap">
            <BoundaryMap boundary={boundary} onBoundaryChange={setBoundary} />
          </div>
          {boundary ? (
            <pre className="boundary-preview">{boundaryPreview}</pre>
          ) : (
            <p className="empty-boundary">Use the polygon tool on the map to outline the farm.</p>
          )}
        </section>
      </section>
    </main>
  );
}
