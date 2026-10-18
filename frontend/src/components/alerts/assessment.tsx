import type { NarrativeCampaignDetail } from "@/types/chakravyuh";
import { score } from "@/lib/privacy";
export function Assessment({ detail }: { detail: NarrativeCampaignDetail }) {
  const cti = detail.cti_assessment;
  return (
    <section className="assessment">
      <div className="assessment-top">
        <div>
          <span className="eyebrow">COMPOSITE PRIORITIZATION</span>
          <div className="cti-value">
            {score(cti.cti_score)}
            <small>{cti.cti_score != null && "/100"}</small>
            <span
              className={`tier ${cti.threat_level?.toLowerCase() ?? "unknown"}`}
            >
              {cti.threat_level ?? "INSUFFICIENT DATA"}
            </span>
          </div>
        </div>
        <div className="assessment-secondary">
          <span>
            Coordination sync{" "}
            <b>{score(detail.coordination_assessment.sync_score, 3)}</b>
          </span>
          <span>
            Component coverage <b>{(cti.coverage_ratio * 100).toFixed(0)}%</b>
          </span>
          <span>
            Claim <b>{detail.claim_verification.status}</b>
          </span>
        </div>
      </div>
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
      <p className={cti.alert_eligible ? "notice alert" : "notice"}>
        {cti.alert_eligible
          ? "All evidence gates pass for a local warning. Cooldown/rearm still governs dispatch."
          : `Alert suppressed: ${cti.alert_suppression_reasons.join(", ").replaceAll("_", " ")}`}
      </p>
      <p className="subtle">
        Missing components: {cti.missing_signals.join(", ") || "none"}.
        Heuristic indicators are not calibrated probabilities or proof of
        falsity.
      </p>
    </section>
  );
}
