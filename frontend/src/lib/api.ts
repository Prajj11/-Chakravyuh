import { z } from "zod";
import { contract } from "./contracts";
import type {
  HealthStatusResponse,
  NarrativeCampaignDetail,
  NarrativeCampaignSummary,
  JobAccepted,
  JobStatusResponse,
  MediaUploadResponse,
  ClaimVerificationAssessment,
  WebSocketStreamMessage,
} from "@/types/chakravyuh";

export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8001";
export async function request<T>(
  path: string,
  token: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init?.body && !(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch(API + path, {
    ...init,
    headers,
    cache: "no-store",
  });
  const body: unknown = await response.json();
  if (!response.ok) {
    const error = contract<{
      code: string;
      message: string;
      request_id: string;
    }>("APIError").safeParse(body);
    throw new Error(
      error.success
        ? `${error.data.code}: ${error.data.message}`
        : `Request failed (${response.status})`,
    );
  }
  const parsed = schema.safeParse(body);
  if (!parsed.success)
    throw new Error(
      "Backend data does not match this workbench version. Refresh after updating both services.",
    );
  return parsed.data;
}
export const getHealth = () =>
  request(
    "/api/v1/health",
    "",
    contract<HealthStatusResponse>("HealthStatusResponse"),
  );
export const getCampaigns = (token: string) =>
  request(
    "/api/v1/campaigns",
    token,
    z.array(contract<NarrativeCampaignSummary>("NarrativeCampaignSummary")),
  );
export const getCampaign = (id: string, token: string) =>
  request(
    `/api/v1/campaigns/${encodeURIComponent(id)}`,
    token,
    contract<NarrativeCampaignDetail>("NarrativeCampaignDetail"),
  );
export const getJob = async (id: string, token: string) => {
  const job = await request(
    `/api/v1/jobs/${id}`,
    token,
    contract<JobStatusResponse>("JobStatusResponse"),
  );
  if (job.status === "SUCCEEDED") {
    const name = {
      SCENARIO: "ScenarioSwitchResponse",
      INJECT: "UnifiedSocialEventEnriched",
      FORENSICS: "ForensicMediaReport",
      EXPORT: "EvidenceDossierBundle",
    }[job.job_type];
    contract(name).parse(job.result);
  }
  return job;
};
export const queueJob = (path: string, body: unknown, token: string) =>
  request(path, token, contract<JobAccepted>("JobAccepted"), {
    method: "POST",
    body: JSON.stringify(body),
  });
export const review = (id: string, body: unknown, token: string) =>
  request(
    `/api/v1/campaigns/${id}/claim-review`,
    token,
    contract<ClaimVerificationAssessment>("ClaimVerificationAssessment"),
    { method: "PUT", body: JSON.stringify(body) },
  );
export async function upload(file: File, token: string) {
  const form = new FormData();
  form.set("file", file);
  return request(
    "/api/v1/media",
    token,
    contract<MediaUploadResponse>("MediaUploadResponse"),
    { method: "POST", body: form },
  );
}
export async function artifact(idOrPath: string, token: string): Promise<Blob> {
  const path = idOrPath.startsWith("/")
    ? idOrPath
    : `/api/v1/artifacts/${idOrPath}/download`;
  if (!/^\/api\/v1\/artifacts\/[a-f0-9]+\/download$/.test(path))
    throw new Error("Invalid artifact path");
  const response = await fetch(API + path, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok)
    throw new Error(`Artifact unavailable (${response.status})`);
  return response.blob();
}
export function streamMessage(value: unknown): WebSocketStreamMessage {
  const envelope = contract<WebSocketStreamMessage>(
    "WebSocketStreamMessage",
  ).parse(value);
  const payloadType = {
    NEW_EVENT: "UnifiedSocialEventEnriched",
    CTI_ALERT: "CampaignAlert",
    SCENARIO_RESET: "ScenarioSwitchResponse",
    JOB_UPDATED: "JobNotification",
  }[envelope.message_type];
  contract(payloadType).parse(envelope.payload);
  return envelope;
}
