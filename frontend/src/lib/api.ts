import { z } from "zod";
import type { HealthStatusResponse } from "@/types/chakravyuh";

const healthSchema = z
  .object({
    status: z.enum(["healthy", "degraded"]),
    pipeline_version: z.string(),
    active_campaigns_count: z.number().int().nonnegative(),
    total_ingested_events: z.number().int().nonnegative(),
    layer_status: z.record(
      z.string(),
      z.enum([
        "AVAILABLE",
        "INSUFFICIENT_DATA",
        "UNSUPPORTED",
        "FAILED",
        "PENDING",
      ]),
    ),
    execution_mode: z.literal("local_computed"),
  })
  .strict();

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8001";

export async function getHealth(
  signal: AbortSignal,
): Promise<HealthStatusResponse> {
  const response = await fetch(`${apiUrl}/api/v1/health`, {
    signal,
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Backend health check failed");
  const data: unknown = await response.json();
  return healthSchema.parse(data);
}

export async function connectSession(token: string): Promise<void> {
  const response = await fetch(`${apiUrl}/api/v1/campaigns`, {
    headers: { Authorization: `Bearer ${token}` },
    signal: AbortSignal.timeout(5000),
    cache: "no-store",
  });
  if (response.status === 401)
    throw new Error("Token did not match the current backend launch.");
  if (!response.ok) throw new Error("Could not authorize this local session.");
  const data: unknown = await response.json();
  z.array(
    z.object({ campaign_id: z.string(), title: z.string() }).passthrough(),
  ).parse(data);
}
