"use client";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { NarrativeCampaignDetail } from "@/types/chakravyuh";
import { score } from "@/lib/privacy";
type Props = {
  detail: NarrativeCampaignDetail;
  cursor: number | null;
  onCursor: (time: number | null) => void;
  highlight: Set<string>;
};
export function TimelinePanel({ detail, cursor, onCursor, highlight }: Props) {
  const first = Date.parse(detail.first_detected_utc),
    last = Date.parse(detail.last_updated_utc);
  const data = detail.timeline.map((bucket) => ({
    ...bucket,
    time: Date.parse(bucket.timestamp_utc),
    label: new Date(bucket.timestamp_utc).toISOString().slice(11, 16),
  }));
  const related = detail.sample_posts.filter((event) =>
    highlight.has(event.account.account_id),
  ).length;
  return (
    <section className="timeline-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">EVENT TIME · UTC · ONE-MINUTE BINS</span>
          <h2>Narrative propagation</h2>
        </div>
        <span className="chip">
          Burst dispersion{" "}
          {score(detail.coordination_assessment.burst_index, 2)}
        </span>
      </div>
      <div className="timeline-chart">
        <ResponsiveContainer width="100%" height={190}>
          <BarChart
            data={data}
            onClick={(state) => {
              if (state?.activeLabel) {
                const item = data.find(
                  (bucket) => bucket.label === state.activeLabel,
                );
                if (item) onCursor(item.time + 59999);
              }
            }}
          >
            <XAxis
              dataKey="label"
              stroke="#94a3b8"
              fontSize={10}
              minTickGap={30}
            />
            <YAxis stroke="#94a3b8" fontSize={10} allowDecimals={false} />
            <Tooltip
              contentStyle={{
                background: "#142036",
                borderColor: "#334155",
                fontSize: 12,
              }}
            />
            <Bar
              dataKey="coordinated_volume"
              name="Candidate coordinated group"
              stackId="volume"
              fill="#f59e0b"
              isAnimationActive={false}
            />
            <Bar
              dataKey="low_indicator_volume"
              name="Low observed indicators"
              stackId="volume"
              fill="#10b981"
              isAnimationActive={false}
            />
            <Bar
              dataKey="unclassified_volume"
              name="Unclassified"
              stackId="volume"
              fill="#64748b"
              isAnimationActive={false}
            />
            {cursor != null && (
              <ReferenceLine
                x={new Date(cursor).toISOString().slice(11, 16)}
                stroke="#e2e8f0"
              />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="cursor-control">
        <label>
          Visual event-time cursor{" "}
          <input
            aria-label="Event-time cursor"
            type="range"
            min={first}
            max={Math.max(first + 1, last)}
            step="1000"
            value={cursor ?? last}
            onChange={(e) => onCursor(Number(e.target.value))}
          />
        </label>
        <span className="mono">
          {new Date(cursor ?? last).toISOString().slice(11, 19)} UTC
        </span>
        <button onClick={() => onCursor(null)}>Show full window</button>
      </div>
      <p className="subtle">
        Bars retain snapshot classifications and partition {detail.total_posts}{" "}
        posts exactly once.{" "}
        {highlight.size ? `${related} posts linked to your selection. ` : ""}
        Visual filters leave analytical scores unchanged. Hawkes fitting:
        UNSUPPORTED.
      </p>
    </section>
  );
}
