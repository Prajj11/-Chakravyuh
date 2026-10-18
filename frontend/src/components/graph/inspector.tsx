import type { GraphEdge, NarrativeCampaignDetail } from "@/types/chakravyuh";
import {
  label,
  privateText,
  restricted,
  roleLabel,
  score,
} from "@/lib/privacy";
type Props = {
  detail: NarrativeCampaignDetail;
  selected: string;
  edge: GraphEdge | null;
  privacy: boolean;
  onClear: () => void;
};
export function Inspector({ detail, selected, edge, privacy, onClear }: Props) {
  const node = detail.nodes.find((node) => node.id === selected);
  return (
    <aside className="inspector">
      <div className="panel-heading">
        <span className="eyebrow">EVIDENCE INSPECTOR</span>
        {(node || edge) && <button onClick={onClear}>Clear</button>}
      </div>
      {edge ? (
        <>
          <h2>{edge.interaction_type.replaceAll("_", " ")}</h2>
          <p>
            {detail.nodes.find((node) => node.id === edge.source) &&
              label(
                detail.nodes.find((node) => node.id === edge.source)!,
                privacy,
              )}{" "}
            →{" "}
            {detail.nodes.find((node) => node.id === edge.target) &&
              label(
                detail.nodes.find((node) => node.id === edge.target)!,
                privacy,
              )}
          </p>
          <dl className="facts">
            <dt>Normalized synchronization weight</dt>
            <dd>{score(edge.sync_weight, 3)}</dd>
            <dt>Mean / observed delta</dt>
            <dd>{score(edge.time_delta_sec, 2)} s</dd>
            <dt>Method</dt>
            <dd>{edge.computation_mode}</dd>
          </dl>
          <ul className="reasons">
            {edge.evidence_reasons.map((reason) => (
              <li key={reason}>{privateText(reason, detail, privacy)}</li>
            ))}
          </ul>
          <h3>Exact matched event IDs</h3>
          {edge.matched_event_ids.map((id) => (
            <code className="hash" key={id}>
              {id}
            </code>
          ))}
        </>
      ) : node ? (
        <>
          <h2>{label(node, privacy)}</h2>
          <span className="chip">{roleLabel(node.role)}</span>
          <p className="subtle">
            {node.role === "EARLIEST_OBSERVED_SEED"
              ? "Earliest observed in collected data; global origin is not established."
              : "Role reflects available observations in this snapshot."}
          </p>
          <div className="inspector-score">
            <strong>{score(node.bot_assessment.bot_indicator_score)}</strong>
            <span>/100 bot indicator</span>
          </div>
          <p className="subtle">
            {node.bot_assessment.computation_mode} · not a probability
          </p>
          <dl className="facts">
            <dt>Account synchronization</dt>
            <dd>{score(node.sync_assessment.sync_score, 3)}</dd>
            <dt>Bot feature coverage</dt>
            <dd>{(node.bot_assessment.coverage_ratio * 100).toFixed(0)}%</dd>
            <dt>Posts / span</dt>
            <dd>
              {node.posts_in_campaign} /{" "}
              {node.bot_assessment.observation_seconds.toFixed(0)} seconds
            </dd>
            <dt>Matched peers / repeated buckets</dt>
            <dd>
              {node.sync_assessment.matched_peer_count} /{" "}
              {node.sync_assessment.repeated_bucket_count}
            </dd>
            <dt>First observed UTC</dt>
            <dd>{node.first_observed_utc}</dd>
            <dt>Community / directed reach</dt>
            <dd>
              {node.community_id} / {node.cascade_out_degree}
            </dd>
            <dt>Betweenness centrality</dt>
            <dd>{node.betweenness_centrality.toFixed(5)}</dd>
            <dt>Declared profile</dt>
            <dd>
              {privacy && restricted(node)
                ? "Masked by privacy view"
                : (node.region ?? "Unavailable")}
            </dd>
          </dl>
          <h3>Additive bot feature contributions</h3>
          {Object.entries(node.bot_assessment.feature_contributions).map(
            ([key, value]) => (
              <div className="contribution" key={key}>
                <span>{key.replaceAll("_", " ")}</span>
                <b>{value.toFixed(2)}</b>
              </div>
            ),
          )}
          <details>
            <summary>
              Synchronization contributions & available base weights
            </summary>
            <h3>Additive sync peer contributions</h3>
            {Object.entries(node.sync_assessment.feature_contributions).map(
              ([peer, value]) => (
                <div className="contribution" key={peer}>
                  <span>{privateText(peer, detail, privacy)}</span>
                  <b>{value.toFixed(4)}</b>
                </div>
              ),
            )}
            <h3>Available bot base weights</h3>
            {Object.entries(node.bot_assessment.available_feature_weights).map(
              ([feature, weight]) => (
                <div className="contribution" key={feature}>
                  <span>{feature.replaceAll("_", " ")}</span>
                  <b>{weight.toFixed(2)}</b>
                </div>
              ),
            )}
          </details>
          <h3>Missing evidence</h3>
          <p>
            {node.bot_assessment.missing_signals
              .join(", ")
              .replaceAll("_", " ") || "No missing bot features"}
          </p>
          <ul className="reasons">
            {node.evidence_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </>
      ) : (
        <div className="empty">
          Select a node or edge, or use the searchable account list to inspect
          its observations and contributions.
        </div>
      )}
    </aside>
  );
}
