"use client";
import dynamic from "next/dynamic";
import { useState } from "react";
import { cellToBoundary } from "h3-js";
import type { NarrativeCampaignDetail } from "@/types/chakravyuh";
import { score } from "@/lib/privacy";
const WebGLMap = dynamic(() => import("./webgl-map"), {
  ssr: false,
  loading: () => <p>Preparing local map renderer…</p>,
});
type Props = {
  detail: NarrativeCampaignDetail;
  selected: string;
  onSelect: (cell: string) => void;
};
const project = (lat: number, lon: number): [number, number] => [
  (lon - 64) * 24,
  (39 - lat) * 19,
];
export function GeoPanel({ detail, selected, onSelect }: Props) {
  const [webgl, setWebgl] = useState(false);
  const reports = detail.geo_anomalies;
  const current =
    reports.find((report) => report.h3_index === selected) ?? reports[0];
  return (
    <section>
      <div className="panel-heading">
        <div>
          <span className="eyebrow">SOURCE ≠ MENTIONED SUBJECT</span>
          <h2>Geographic context</h2>
        </div>
        <button onClick={() => setWebgl(!webgl)}>
          {webgl ? "Use offline coordinate view" : "Use local WebGL map"}
        </button>
      </div>
      <p className="subtle">
        H3 resolution 5 · local geometry · no external tiles or map token
      </p>
      {webgl ? (
        <WebGLMap
          reports={reports}
          onSelect={onSelect}
          onFailure={() => setWebgl(false)}
        />
      ) : (
        <svg
          className="offline-map"
          viewBox="0 0 780 530"
          role="img"
          aria-label="Offline coordinate grid showing observed source-to-target arcs"
        >
          <defs>
            <pattern
              id="grid"
              width="120"
              height="95"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M120 0H0V95"
                fill="none"
                stroke="#25334c"
                strokeWidth="1"
              />
            </pattern>
          </defs>
          <rect width="780" height="530" fill="url(#grid)" />
          {[65, 70, 75, 80, 85, 90, 95].map((lon) => (
            <text
              key={lon}
              x={project(38, lon)[0]}
              y="18"
              fill="#8b9bb3"
              fontSize="11"
            >
              {lon}°E
            </text>
          ))}
          {[15, 20, 25, 30, 35].map((lat) => (
            <text
              key={lat}
              x="8"
              y={project(lat, 65)[1]}
              fill="#8b9bb3"
              fontSize="11"
            >
              {lat}°N
            </text>
          ))}
          <text x="28" y="505" fill="#91a4bc" fontSize="12">
            Schematic coordinate view. Arcs show declared/GPS observations, not
            verified physical origin.
          </text>
          {reports.map((report) => {
            const [x, y] = project(report.latitude, report.longitude);
            return (
              <g key={report.h3_index}>
                {report.top_source_origins.map((source) => {
                  const [a, b] = project(source.latitude, source.longitude);
                  return (
                    <g
                      key={
                        source.source_h3_index +
                        source.source_location_confidence
                      }
                    >
                      <path
                        d={`M${a},${b} Q${(a + x) / 2},${Math.min(b, y) - 60} ${x},${y}`}
                        fill="none"
                        stroke={
                          source.source_location_confidence === "EXPLICIT_GPS"
                            ? "#38bdf8"
                            : "#a78bfa"
                        }
                        strokeOpacity=".6"
                        strokeDasharray={
                          source.source_location_confidence ===
                          "PROFILE_DECLARED"
                            ? "5 5"
                            : undefined
                        }
                      />
                      <circle
                        cx={a}
                        cy={b}
                        r={4 + Math.min(source.post_count / 8, 5)}
                        fill="#38bdf8"
                      >
                        <title>
                          {source.source_region ?? "Observed source"}:{" "}
                          {source.post_count} posts ·{" "}
                          {source.source_location_confidence}
                        </title>
                      </circle>
                    </g>
                  );
                })}
                <polygon
                  points={cellToBoundary(report.h3_index)
                    .map(([lat, lon]) => project(lat, lon).join(","))
                    .join(" ")}
                  fill="#fb923c"
                  stroke="#fff"
                  strokeWidth="2"
                />
                <circle
                  cx={x}
                  cy={y}
                  r="18"
                  fill="#fb923c22"
                  stroke={selected === report.h3_index ? "white" : "#fb923c"}
                />
                <text x={x + 24} y={y + 5} fill="#f8fafc" fontSize="13">
                  {report.region_name ?? "Target cell"}
                </text>
              </g>
            );
          })}
        </svg>
      )}
      {!reports.length && (
        <div className="empty">
          No resolved target region. Mentioned places never supply author
          coordinates.
        </div>
      )}
      <div className="geo-cells">
        {reports.map((report) => (
          <button
            key={report.h3_index}
            className={current?.h3_index === report.h3_index ? "selected" : ""}
            onClick={() => onSelect(report.h3_index)}
          >
            {report.region_name ?? report.h3_index}
            <small>
              {report.target_campaign_posts_1hr} campaign posts / trailing hour
            </small>
          </button>
        ))}
      </div>
      {current && (
        <>
          <div className="metric-grid">
            <div>
              <small>External known-source ratio</small>
              <strong>{score(current.geospatial_mismatch_ratio, 3)}</strong>
              <span>
                {current.known_source_posts} known posts ·{" "}
                {current.known_source_accounts} authors
              </span>
            </div>
            <div>
              <small>Source coverage</small>
              <strong>
                {(current.source_location_coverage_ratio * 100).toFixed(1)}%
              </strong>
              <span>GPS or resolved declarations</span>
            </div>
            <div>
              <small>Regional Z-score</small>
              <strong>{score(current.z_score, 2)}</strong>
              <span>{current.baseline_bucket_count} valid hourly buckets</span>
            </div>
          </div>
          <div className="notice">
            {current.is_astroturfing_alert
              ? "Coordination-gated geographic mismatch indicator"
              : "Geographic mismatch alert suppressed"}{" "}
            ·{" "}
            {current.z_score != null && current.z_score >= 3
              ? "Regional spike measured"
              : "No qualifying regional spike"}
          </div>
          <dl className="facts">
            <dt>Regional velocity / campaign denominator</dt>
            <dd>
              {current.current_velocity_1hr} /{" "}
              {current.target_campaign_posts_1hr} posts per trailing hour
            </dd>
            <dt>Baseline</dt>
            <dd>
              {current.baseline_status} · mean{" "}
              {score(current.baseline_mean_1hr, 2)} · sample SD{" "}
              {score(current.baseline_std_1hr, 2)}
            </dd>
            <dt>Watermark (UTC)</dt>
            <dd>{current.window_end_utc}</dd>
            <dt>Baseline scope hash</dt>
            <dd className="hash">{current.baseline_scope_id}</dd>
          </dl>
          <ul className="reasons">
            {current.evidence_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
          <table>
            <caption>Observed source composition</caption>
            <thead>
              <tr>
                <th>Source</th>
                <th>Confidence type</th>
                <th>Posts</th>
              </tr>
            </thead>
            <tbody>
              {current.top_source_origins.map((source) => (
                <tr
                  key={
                    source.source_h3_index + source.source_location_confidence
                  }
                >
                  <td>{source.source_region ?? source.source_h3_index}</td>
                  <td>{source.source_location_confidence}</td>
                  <td>{source.post_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
