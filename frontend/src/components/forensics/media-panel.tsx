"use client";
import { useEffect, useState } from "react";
import { artifact } from "@/lib/api";
import { score } from "@/lib/privacy";
import type {
  ForensicMediaReport,
  NarrativeCampaignDetail,
} from "@/types/chakravyuh";
type Props = { detail: NarrativeCampaignDetail; token: string };
export function MediaPanel({ detail, token }: Props) {
  const [selected, setSelected] = useState(""),
    [split, setSplit] = useState(50),
    [boxes, setBoxes] = useState(true);
  const [original, setOriginal] = useState(""),
    [heat, setHeat] = useState(""),
    [error, setError] = useState("");
  const report =
    detail.media_reports.find((item) => item.media_id === selected) ??
    detail.media_reports[0];
  useEffect(() => {
    let active = true;
    const urls: string[] = [];
    setOriginal("");
    setHeat("");
    setError("");
    if (report?.analysis_status === "AVAILABLE") {
      const load = async () => {
        try {
          const original = URL.createObjectURL(
            await artifact(report.media_id, token),
          );
          urls.push(original);
          if (active) setOriginal(original);
          if (report.heatmap_artifact_ref) {
            const overlay = URL.createObjectURL(
              await artifact(report.heatmap_artifact_ref, token),
            );
            urls.push(overlay);
            if (active) setHeat(overlay);
          }
        } catch (e) {
          if (active)
            setError(
              e instanceof Error ? e.message : "Evidence image unavailable",
            );
        }
      };
      void load();
    }
    return () => {
      active = false;
      urls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [
    report?.media_id,
    report?.analysis_status,
    report?.heatmap_artifact_ref,
    token,
  ]);
  if (!detail.media_reports.length)
    return (
      <section>
        <h2>Media evidence</h2>
        <div className="empty">
          No collected media in this narrative. CTI treats verified absence as a
          measured zero; missing or unsupported media is unavailable.
        </div>
      </section>
    );
  const attachment = detail.sample_posts
    .flatMap((event) => event.media_attachments)
    .find((media) => media.evidence_ref === report.media_id);
  return (
    <section>
      <div className="panel-heading">
        <div>
          <span className="eyebrow">COMPUTED FROM RETAINED BYTES</span>
          <h2>Media forensics</h2>
        </div>
        <span className="chip">{report.computation_mode}</span>
      </div>
      <select
        aria-label="Media evidence"
        value={report.media_id}
        onChange={(e) => setSelected(e.target.value)}
      >
        {detail.media_reports.map((item) => (
          <option key={item.media_id} value={item.media_id}>
            {item.media_type} · {item.media_id.slice(0, 12)} ·{" "}
            {item.analysis_status}
          </option>
        ))}
      </select>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {report.analysis_status === "AVAILABLE" ? (
        <>
          <div className="comparison">
            <div className="image-stage">
              {original && (
                <img src={original} alt="Retained original evidence" />
              )}
              {heat && (
                <img
                  src={heat}
                  alt="Computed ELA heatmap"
                  style={{ clipPath: `inset(0 ${100 - split}% 0 0)` }}
                />
              )}
              {boxes &&
                report.heatmap_regions.map((box, index) => (
                  <div
                    className="heat-box"
                    key={index}
                    title={box.label}
                    style={{
                      left: `${box.x * 100}%`,
                      top: `${box.y * 100}%`,
                      width: `${box.w * 100}%`,
                      height: `${box.h * 100}%`,
                    }}
                  />
                ))}
              <span className="image-tag">ELA overlay ← | → original</span>
            </div>
          </div>
          <label className="slider-label">
            Original / computed ELA comparison
            <input
              type="range"
              aria-label="ELA comparison split"
              min="0"
              max="100"
              value={split}
              onChange={(e) => setSplit(Number(e.target.value))}
            />
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={boxes}
              onChange={(e) => setBoxes(e.target.checked)}
            />
            Show computed anomaly boxes
          </label>
        </>
      ) : (
        <div className="empty">
          {report.analysis_status}: {report.media_type} analysis has no computed
          manipulation score.
        </div>
      )}
      <div className="metric-grid">
        <div>
          <small>ELA anomaly indicator</small>
          <strong>
            {score(report.ela_anomaly_score)}
            {report.ela_anomaly_score != null && " /100"}
          </strong>
        </div>
        <div>
          <small>Related pHash candidates</small>
          <strong>{report.duplicate_matches_count}</strong>
          <span>Self matches excluded · Hamming ≤10</span>
        </div>
        <div>
          <small>Deepfake model</small>
          <strong>
            {report.deepfake_visual_score == null
              ? "Unsupported"
              : score(report.deepfake_visual_score)}
          </strong>
          <span>No calibrated inference adapter</span>
        </div>
      </div>
      <div className="badge-row">
        <span className="chip">
          EXIF:{" "}
          {report.exif_present == null
            ? "unavailable"
            : report.exif_present
              ? "present"
              : "absent"}
        </span>
        <span className="chip">C2PA: {report.c2pa_status}</span>
        <span className="chip">{report.analysis_status}</span>
      </div>
      <dl className="facts">
        <dt>Exact-byte SHA-256</dt>
        <dd className="hash">
          {attachment?.sha256_hash ?? "Unavailable"}{" "}
          {attachment?.sha256_hash && (
            <button
              onClick={() =>
                void navigator.clipboard.writeText(attachment.sha256_hash ?? "")
              }
            >
              Copy
            </button>
          )}
        </dd>
        <dt>64-bit DCT pHash</dt>
        <dd className="mono">{report.phash ?? "Unavailable"}</dd>
        <dt>Parameter set</dt>
        <dd className="hash">{report.parameter_set_id}</dd>
      </dl>
      <Reasons report={report} />
      <table>
        <caption>Computed related-media candidates</caption>
        <thead>
          <tr>
            <th>Media</th>
            <th>pHash</th>
            <th>Hamming distance</th>
          </tr>
        </thead>
        <tbody>
          {detail.media_reports
            .filter(
              (item) =>
                item.media_id !== report.media_id && item.phash && report.phash,
            )
            .map((item) => (
              <tr key={item.media_id}>
                <td>{item.media_id.slice(0, 12)}</td>
                <td className="mono">{item.phash}</td>
                <td>{distance(report.phash ?? "0", item.phash ?? "0")}</td>
              </tr>
            ))}
        </tbody>
      </table>
    </section>
  );
}
function distance(a: string, b: string) {
  let bits = BigInt(`0x${a}`) ^ BigInt(`0x${b}`),
    count = 0;
  while (bits) {
    count += Number(bits & BigInt(1));
    bits >>= BigInt(1);
  }
  return count;
}
function Reasons({ report }: { report: ForensicMediaReport }) {
  return (
    <ul className="reasons">
      {report.evidence_reasons.map((reason) => (
        <li key={reason}>{reason}</li>
      ))}
    </ul>
  );
}
