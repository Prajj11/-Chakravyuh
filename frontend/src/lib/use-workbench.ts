"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  API,
  artifact,
  getCampaign,
  getCampaigns,
  getHealth,
  getJob,
  queueJob,
  streamMessage,
} from "./api";
import type {
  HealthStatusResponse,
  JobStatusResponse,
  NarrativeCampaignDetail,
  NarrativeCampaignSummary,
} from "@/types/chakravyuh";

export function useWorkbench() {
  const [token, setToken] = useState("");
  const [health, setHealth] = useState<HealthStatusResponse | null>(null);
  const [campaigns, setCampaigns] = useState<NarrativeCampaignSummary[]>([]);
  const [selected, setSelected] = useState("");
  const [detail, setDetail] = useState<NarrativeCampaignDetail | null>(null);
  const [error, setError] = useState("");
  const [stream, setStream] = useState("Session disconnected");
  const [busy, setBusy] = useState("");
  const [lastJob, setLastJob] = useState<JobStatusResponse | null>(null);
  const [notice, setNotice] = useState("");
  const [markers, setMarkers] = useState<
    Array<{ campaignId: string; time: string; cti: number }>
  >([]);
  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  const serial = useRef(0);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      serial.current += 1;
    };
  }, []);
  const refresh = useCallback(async () => {
    const revision = ++serial.current;
    try {
      const current = await getHealth();
      setHealth(current);
      if (!token) return;
      const list = await getCampaigns(token);
      if (revision !== serial.current) return;
      setCampaigns(list);
      const id = list.some((c) => c.campaign_id === selectedRef.current)
        ? selectedRef.current
        : (list[0]?.campaign_id ?? "");
      if (id !== selectedRef.current) {
        selectedRef.current = id;
        setSelected(id);
      }
      if (!id) {
        setDetail(null);
        return;
      }
      const snapshot = await getCampaign(id, token);
      if (revision === serial.current && selectedRef.current === id) {
        setDetail((prev) =>
          prev?.campaign_id === id &&
          prev.snapshot_revision > snapshot.snapshot_revision
            ? prev
            : snapshot,
        );
        setError("");
      }
    } catch (e) {
      if (revision === serial.current)
        setError(
          e instanceof Error ? e.message : "Unable to refresh snapshots",
        );
    }
  }, [token]);
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 3000);
    return () => clearInterval(timer);
  }, [refresh]);
  useEffect(() => {
    setDetail(null);
    void refreshRef.current();
  }, [selected]);
  useEffect(() => {
    if (!token) return;
    let stopped = false,
      sequence = 0,
      attempt = 0;
    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let pending: ReturnType<typeof setTimeout> | undefined;
    const connect = () => {
      if (stopped) return;
      setStream("Connecting stream");
      socket = new WebSocket(
        `${API.replace(/^http/, "ws")}/ws/stream?last_sequence=${sequence}`,
        ["chakravyuh.v1", token],
      );
      socket.onopen = () => {
        attempt = 0;
        setStream("Stream connected");
      };
      socket.onmessage = (event) => {
        try {
          const message = streamMessage(JSON.parse(String(event.data)));
          if (
            message.message_type !== "SCENARIO_RESET" &&
            message.sequence <= sequence
          )
            return;
          sequence = message.sequence;
          if (message.message_type === "SCENARIO_RESET") {
            setNotice("Replay/stream reset: resynchronizing snapshots");
            setMarkers((previous) =>
              previous.filter((marker) =>
                message.payload.loaded_campaign_ids.includes(marker.campaignId),
              ),
            );
          }
          if (message.message_type === "CTI_ALERT") {
            setNotice(`Gated warning: ${message.campaign_id}`);
            const cti = message.payload.assessment.cti_score;
            if (cti != null)
              setMarkers((previous) =>
                [
                  ...previous,
                  {
                    campaignId: message.payload.campaign_id,
                    time: message.timestamp_utc,
                    cti,
                  },
                ].slice(-1000),
              );
          }
          if (!pending)
            pending = setTimeout(() => {
              pending = undefined;
              void refreshRef.current();
            }, 150);
        } catch {
          setError("Invalid stream contract; refreshing through REST");
          void refreshRef.current();
        }
      };
      socket.onclose = (event) => {
        if (stopped) return;
        if (event.code === 4401 || event.code === 4403) {
          setToken("");
          setCampaigns([]);
          setDetail(null);
          setSelected("");
          setStream("Session expired: reconnect with current local token");
          return;
        }
        const wait = Math.min(2 ** attempt++, 30);
        setStream(`Reconnecting in ${wait}s · REST polling every 3s`);
        retry = setTimeout(connect, wait * 1000);
      };
      socket.onerror = () =>
        setStream("Stream interrupted · REST polling active");
    };
    connect();
    return () => {
      stopped = true;
      socket?.close();
      clearTimeout(retry);
      clearTimeout(pending);
    };
  }, [token]);
  const authorize = async (value: string) => {
    await getCampaigns(value);
    setToken(value);
    setError("");
  };
  const run = async (path: string, body: unknown, label: string) => {
    setBusy(`${label}: queued`);
    setError("");
    setLastJob(null);
    try {
      const accepted = await queueJob(path, body, token);
      for (;;) {
        if (!mounted.current)
          throw new Error(
            "View closed; the queued job continues in the backend.",
          );
        const job = await getJob(accepted.job_id, token);
        setLastJob(job);
        setBusy(`${label}: ${job.status.toLowerCase()}`);
        if (job.status === "FAILED") throw new Error(job.error_code);
        if (job.status === "SUCCEEDED") {
          const target =
            job.job_type === "SCENARIO"
              ? job.result.loaded_campaign_ids[0]
              : job.job_type === "INJECT"
                ? job.result.assigned_campaign_id
                : undefined;
          if (target) {
            selectedRef.current = target;
            setSelected(target);
          }
          setNotice(`${label} completed`);
          await refresh();
          return job;
        }
        await new Promise((resolve) => setTimeout(resolve, 350));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Job failed");
      throw e;
    } finally {
      setBusy("");
    }
  };
  const download = async (path: string) => {
    const blob = await artifact(path, token),
      url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "chakravyuh-dossier.zip";
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return {
    token,
    health,
    campaigns,
    selected,
    setSelected,
    detail,
    error,
    setError,
    stream,
    busy,
    lastJob,
    notice,
    markers,
    authorize,
    refresh,
    run,
    download,
  };
}
