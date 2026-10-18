import type { NarrativeCampaignDetail } from "@/types/chakravyuh";
import { score } from "@/lib/privacy";
import {
  ChevronDown,
  FileCheck2,
  Network,
  ScanLine,
  ShieldAlert,
} from "lucide-react";
export function Assessment({ detail }: { detail: NarrativeCampaignDetail }) {
  const cti = detail.cti_assessment;
  const media = detail.media_reports.filter(
    (report) =>
      report.analysis_status === "AVAILABLE" &&
      report.manipulation_indicator_score != null,
  );
  const mediaScore = media.length
    ? Math.max(...media.map((report) => report.manipulation_indicator_score!))
    : null;
  return (
    <section className="assessment">
      <div className="signal-cards">
        <div
          className={`signal-card cti-card ${cti.threat_level?.toLowerCase() ?? "unknown"}`}
        >
          <div className="signal-label">
            <ShieldAlert size={15} />
            <span>Campaign priority</span>
          </div>
          <div className="cti-card-main">
            <div className="priority-dial">
              <svg viewBox="0 0 80 80" aria-hidden="true">
                <circle cx="40" cy="40" r="33" className="dial-track" />
                <circle
                  cx="40"
                  cy="40"
                  r="33"
                  className="dial-value"
                  pathLength="100"
                  strokeDasharray={`${cti.cti_score ?? 0} 100`}
                  transform="rotate(-90 40 40)"
                />
              </svg>
              <strong>
                {cti.cti_score == null ? "—" : score(cti.cti_score)}
              </strong>
            </div>
            <div>
              <span
                className={`tier ${cti.threat_level?.toLowerCase() ?? "unknown"}`}
              >
                {cti.threat_level ?? "INSUFFICIENT"}
              </span>
              <small>CTI · 0–100 index</small>
            </div>
          </div>
        </div>
        <div className="signal-card">
          <div className="signal-label">
            <Network size={15} />
            <span>Coordination</span>
          </div>
          <strong className="signal-number">
            {detail.coordination_assessment.sync_score == null
              ? "—"
              : score(detail.coordination_assessment.sync_score, 3)}
          </strong>
          <small>
            {detail.coordination_assessment.sync_score == null
              ? "Insufficient observations"
              : "Observed synchronization"}
          </small>
          <span className="signal-context">
            {detail.coordination_assessment.eligible_pair_count} eligible pairs
          </span>
        </div>
        <div className="signal-card">
          <div className="signal-label">
            <ScanLine size={15} />
            <span>Media indicators</span>
          </div>
          <strong className="signal-number">
            {mediaScore == null ? "—" : score(mediaScore)}
            {mediaScore != null && <small>/100</small>}
          </strong>
          <small>
            {!detail.media_reports.length
              ? "No media attached"
              : mediaScore == null
                ? "No available analysis"
                : "Highest measured indicator"}
          </small>
          <span className="signal-context">
            {media.length} available {media.length === 1 ? "report" : "reports"}
          </span>
        </div>
        <div className="signal-card claim-signal">
          <div className="signal-label">
            <FileCheck2 size={15} />
            <span>Claim verification</span>
          </div>
          <strong className="claim-state">
            {detail.claim_verification.status
              .replaceAll("_", " ")
              .toLowerCase()}
          </strong>
          <small>
            {detail.claim_verification.status === "UNVERIFIED"
              ? "Human review required"
              : "Contextual review recorded"}
          </small>
          <span className="signal-context">Separate from coordination</span>
        </div>
      </div>
      <details className="assessment-explanation">
        <summary>
          <span>
            <ChevronDown size={14} />
            Why this assessment?
          </span>
          <span>
            {(cti.coverage_ratio * 100).toFixed(0)}% component coverage
          </span>
        </summary>
        <div className="component-bars">
          {Object.entries(cti.effective_weights).map(([name, weight]) => (
            <div key={name}>
              <div>
                <span>{name.replaceAll("_", " ")}</span>
                <span>
                  {score(cti.feature_contributions[name])} weighted points ·{" "}
                  {(weight * 100).toFixed(1)}%
                </span>
              </div>
              <meter
                min={0}
                max={100}
                value={cti.feature_contributions[name] ?? 0}
              />
            </div>
          ))}
        </div>
        <p className="subtle">
          Missing components: {cti.missing_signals.join(", ") || "none"}.
          Heuristic indicators are not calibrated probabilities or proof of
          falsity.
        </p>
      </details>
      <p className={cti.alert_eligible ? "notice alert" : "notice"}>
        <ShieldAlert size={15} />
        <span>
          {cti.alert_eligible
            ? "All evidence gates pass for a local warning. Cooldown/rearm still governs dispatch."
            : `Alert suppressed: ${cti.alert_suppression_reasons.join(", ").replaceAll("_", " ")}`}
        </span>
      </p>
    </section>
  );
}
