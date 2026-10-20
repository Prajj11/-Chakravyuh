"use client";
import { useEffect, useState } from "react";
import { z } from "zod";
import { request } from "@/lib/api";

const feedsSchema = z.record(
  z.string(),
  z.object({
    platform: z.string(),
    state: z.string(),
    coverage: z.string(),
    events_seen: z.number(),
    last_success: z.string().optional(),
    error: z.string().nullable().optional(),
  }),
);
const deliverySchema = z.object({
  enabled: z.boolean(),
  counts: z.record(z.string(), z.number()),
});

export function CollectionStatus() {
  const [feeds, setFeeds] = useState<z.infer<typeof feedsSchema>>({});
  const [delivery, setDelivery] = useState<z.infer<
    typeof deliverySchema
  > | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const update = async () => {
      try {
        const [feeds, delivery] = await Promise.all([
          request("/api/v1/collectors", feedsSchema),
          request("/api/v1/alerts/delivery", deliverySchema),
        ]);
        if (active) {
          setFeeds(feeds);
          setDelivery(delivery);
          setError("");
        }
      } catch {
        if (active)
          setError(
            "Collection status unavailable. Check the backend connection.",
          );
      }
    };
    void update();
    const timer = setInterval(() => void update(), 10000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);
  return (
    <details className="collection-status">
      <summary>
        Public collection · {Object.keys(feeds).length} configured feeds
      </summary>
      {error && <p role="alert">{error}</p>}
      {!Object.keys(feeds).length && (
        <p>
          Live collection is off. Use start-live.bat to enable the configured
          public feeds.
        </p>
      )}
      {Object.entries(feeds).map(([id, feed]) => (
        <p key={id}>
          <strong>{id}</strong> · {feed.platform} · {feed.state} ·{" "}
          {feed.events_seen} new observations this session
          {feed.last_success && (
            <>
              {" "}
              · Last successful poll:{" "}
              {new Date(feed.last_success).toLocaleString()}
            </>
          )}
          {feed.error && <> · {feed.error}: retrying with backoff</>}
        </p>
      ))}
      {!!Object.keys(feeds).length && (
        <p>
          Polling covers a bounded sample of newest results. It does not
          establish complete platform coverage or author locations.
        </p>
      )}
      {delivery && (
        <p>
          Webhook delivery: {delivery.enabled ? "enabled" : "off"} · Pending:{" "}
          {delivery.counts.PENDING ?? 0} · Delivered:{" "}
          {delivery.counts.DELIVERED ?? 0} · Failed:{" "}
          {delivery.counts.FAILED ?? 0}
        </p>
      )}
    </details>
  );
}
