import type {
  AnalysisQueuedResponse,
  AnalysisRead,
  FarmCreatePayload,
  FarmCreatedResponse,
  RecommendationRead
} from "@/lib/types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function createFarm(
  payload: FarmCreatePayload,
  userId: string
): Promise<FarmCreatedResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/farms`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": userId
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => null);
    throw new Error(errorPayload?.detail ?? "Could not save farm");
  }

  return response.json();
}

export async function startAnalysis(
  farmId: string,
  userId: string
): Promise<AnalysisQueuedResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/farms/${farmId}/analyses`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": userId
    }
  });

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => null);
    throw new Error(errorPayload?.detail ?? "Could not start analysis");
  }

  return response.json();
}

export async function getAnalysis(analysisId: string, userId: string): Promise<AnalysisRead> {
  const response = await fetch(`${apiBaseUrl}/api/v1/analyses/${analysisId}`, {
    headers: {
      "X-User-Id": userId
    }
  });

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => null);
    throw new Error(errorPayload?.detail ?? "Could not load analysis");
  }

  return response.json();
}

export async function generateRecommendations(
  analysisId: string,
  userId: string
): Promise<RecommendationRead> {
  const response = await fetch(`${apiBaseUrl}/api/v1/analyses/${analysisId}/recommendations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": userId
    }
  });

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => null);
    throw new Error(errorPayload?.detail ?? "Could not generate recommendations");
  }

  return response.json();
}
