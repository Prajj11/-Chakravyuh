"use client";
import { useEffect, useRef, useState } from "react";
import { upload } from "@/lib/api";
import type {
  JobStatusResponse,
  NarrativeCampaignDetail,
} from "@/types/chakravyuh";
type Run = (
  path: string,
  body: unknown,
  label: string,
) => Promise<JobStatusResponse>;
export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement;
    ref.current?.showModal();
    return () => {
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, []);
  return (
    <dialog ref={ref} onCancel={onClose} onClose={onClose}>
      <div className="dialog-heading">
        <h2>{title}</h2>
        <button aria-label="Close dialog" onClick={() => ref.current?.close()}>
          ✕
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function InjectDialog({
  run,
  onClose,
}: {
  run: Run;
  onClose: () => void;
}) {
  const [text, setText] = useState(""),
    [handle, setHandle] = useState("@Custom_Test_Account"),
    [language, setLanguage] = useState("und"),
    [location, setLocation] = useState(""),
    [target, setTarget] = useState(""),
    [accountId, setAccountId] = useState(""),
    [timestamp, setTimestamp] = useState(""),
    [latitude, setLatitude] = useState(""),
    [longitude, setLongitude] = useState(""),
    [file, setFile] = useState<File | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    try {
      if ((latitude === "") !== (longitude === ""))
        throw new Error(
          "Provide both latitude and longitude, or leave both unknown.",
        );
      const ids = [];
      if (file) {
        if (file.size > 25 * 1024 * 1024)
          throw new Error("File exceeds 25 MiB");
        ids.push((await upload(file)).media_artifact_id);
      }
      await run(
        "/api/v1/events/inject",
        {
          text,
          handle,
          language,
          account_id: accountId || null,
          timestamp_utc: timestamp || null,
          source_lat: latitude === "" ? null : Number(latitude),
          source_lon: longitude === "" ? null : Number(longitude),
          profile_location: location || null,
          target_region_name: target || null,
          media_artifact_ids: ids,
        },
        "Injection",
      );
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Injection failed");
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title="Inject an observed event" onClose={onClose}>
      <p className="notice">
        USER_INJECTED · isolated from public data and replay. Source location
        defaults to unknown.
      </p>
      <form onSubmit={submit}>
        <label>
          Observed text
          <textarea
            required
            maxLength={20000}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste exact observed text…"
          />
        </label>
        <div className="form-grid">
          <label>
            Stable injected actor ID (optional)
            <input
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              placeholder="Server assigns simulator platform"
            />
          </label>
          <label>
            Observed event time (UTC, optional)
            <input
              value={timestamp}
              onChange={(e) => setTimestamp(e.target.value)}
              placeholder="2026-10-18T12:00:00Z"
            />
          </label>
          <label>
            Handle
            <input
              value={handle}
              required
              onChange={(e) => setHandle(e.target.value)}
            />
          </label>
          <label>
            Language
            <select
              aria-label="Language"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option value="und">Unknown</option>
              <option value="en">English</option>
              <option value="hi">Hindi / bilingual</option>
              <option value="hinglish">Hinglish</option>
            </select>
          </label>
          <label>
            Declared profile location (optional)
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
          </label>
          <label>
            Mentioned target region (optional)
            <input value={target} onChange={(e) => setTarget(e.target.value)} />
          </label>
          <label>
            Explicit source latitude (optional)
            <input
              type="number"
              step="any"
              min="-90"
              max="90"
              value={latitude}
              onChange={(e) => setLatitude(e.target.value)}
            />
          </label>
          <label>
            Explicit source longitude (optional)
            <input
              type="number"
              step="any"
              min="-180"
              max="180"
              value={longitude}
              onChange={(e) => setLongitude(e.target.value)}
            />
          </label>
        </div>
        <label>
          Retained media (JPEG/PNG/WebP/WAV · ≤25 MiB)
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp,audio/wav,video/mp4"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="primary-button" disabled={busy || !text.trim()}>
          {busy ? "Uploading / analyzing…" : "Queue injection"}
        </button>
      </form>
    </Modal>
  );
}
export function ExportDialog({
  detail,
  run,
  download,
  onClose,
}: {
  detail: NarrativeCampaignDetail;
  run: Run;
  download: (path: string) => Promise<void>;
  onClose: () => void;
}) {
  const [format, setFormat] = useState("bundle"),
    [redact, setRedact] = useState(true),
    [busy, setBusy] = useState(false),
    [url, setUrl] = useState(""),
    [error, setError] = useState("");
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    try {
      const job = await run(
        `/api/v1/campaigns/${detail.campaign_id}/export`,
        { format, redact_pii: redact },
        "Integrity-verified export",
      );
      if (job.status === "SUCCEEDED" && job.artifact_download_url)
        setUrl(job.artifact_download_url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title="Tamper-evident investigative dossier" onClose={onClose}>
      <p className="subtle">
        Raw, canonical, media, report and audit hashes are verified before
        packaging. Integrity mismatch blocks this export.
      </p>
      <form onSubmit={submit}>
        <label>
          Package contents
          <select
            value={format}
            onChange={(e) => {
              setFormat(e.target.value);
              setUrl("");
            }}
          >
            <option value="bundle">
              Complete ZIP · JSON, HTML, PDF, STIX + manifest
            </option>
            <option value="pdf">PDF + manifest ZIP</option>
            <option value="html">HTML + manifest ZIP</option>
            <option value="stix">STIX 2.1 + manifest ZIP</option>
          </select>
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={redact}
            onChange={(e) => {
              setRedact(e.target.checked);
              setUrl("");
            }}
          />
          Redact low-indicator and unclassified participants
        </label>
        <p className="notice">
          {redact
            ? "Restricted originals are omitted. Sanitized derivatives retain hash linkage to the originals."
            : "Restricted originals will be included. This package may contain identifying information."}
        </p>
        <p className="subtle">
          Local hashes establish neither content truth nor legal admissibility.
          This creates a local download.
        </p>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button className="primary-button" disabled={busy}>
          {busy ? "Verifying and packaging…" : "Queue verified export"}
        </button>
      </form>
      {url && (
        <button
          className="download-button"
          onClick={() => void download(url).catch((e) => setError(String(e)))}
        >
          Download completed ZIP
        </button>
      )}
    </Modal>
  );
}
