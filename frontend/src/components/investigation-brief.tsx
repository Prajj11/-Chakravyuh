import {
  ArrowRight,
  Crosshair,
  FileCheck2,
  GitBranch,
  ScanLine,
} from "lucide-react";
import type { GraphEdge, NarrativeCampaignDetail } from "@/types/chakravyuh";
import { label, score } from "@/lib/privacy";

export type InvestigationView = "Graph" | "Geography" | "Media" | "Claims";
type Props = {
  detail: NarrativeCampaignDetail;
  privacy: boolean;
  onNode: (id: string) => void;
  onEdge: (edge: GraphEdge) => void;
  onView: (view: InvestigationView) => void;
};
export function InvestigationBrief({
  detail,
  privacy,
  onNode,
  onEdge,
  onView,
}: Props) {
  const seed = detail.nodes.find(
    (node) => node.role === "EARLIEST_OBSERVED_SEED",
  );
  const strongest = detail.edges
    .filter(
      (edge) =>
        edge.interaction_type === "CO_POST_SYNC" && edge.sync_weight != null,
    )
    .reduce<GraphEdge | null>(
      (best, edge) =>
        !best || (edge.sync_weight ?? 0) > (best.sync_weight ?? 0)
          ? edge
          : best,
      null,
    );
  const availableMedia = detail.media_reports.filter(
    (report) => report.analysis_status === "AVAILABLE",
  ).length;
  return (
    <div className="investigation-brief">
      <div className="brief-title">
        <span className="eyebrow">YOUR NEXT MOVE</span>
        <span className="brief-live-dot" />
      </div>
      <h2>Investigation brief</h2>
      <p className="brief-intro">
        A route through the evidence in this snapshot.
      </p>
      <div className="brief-finding">
        <span className="finding-icon">
          <GitBranch size={17} />
        </span>
        <div>
          <span className="eyebrow">01 / CONNECTIONS</span>
          <h3>
            {detail.coordination_assessment.eligible_pair_count} repeated
            co-post pairs
          </h3>
          <p>
            Inspect timestamps and linked observations before attributing
            coordination.
          </p>
          {strongest ? (
            <button className="text-action" onClick={() => onEdge(strongest)}>
              Inspect strongest link <ArrowRight size={13} />
            </button>
          ) : (
            <span className="subtle">
              No eligible co-post edge in this snapshot.
            </span>
          )}
        </div>
      </div>
      <div className="brief-finding">
        <span className="finding-icon">
          <Crosshair size={17} />
        </span>
        <div>
          <span className="eyebrow">02 / FIRST OBSERVED</span>
          <h3>{seed ? label(seed, privacy) : "No observed seed"}</h3>
          <p>
            The first collected account, bounded by this observation window.
          </p>
          {seed && (
            <button className="text-action" onClick={() => onNode(seed.id)}>
              Open account evidence <ArrowRight size={13} />
            </button>
          )}
        </div>
      </div>
      <div className="brief-finding">
        <span className="finding-icon">
          <ScanLine size={17} />
        </span>
        <div>
          <span className="eyebrow">03 / MEDIA CONTEXT</span>
          <h3>
            {availableMedia} computed media{" "}
            {availableMedia === 1 ? "report" : "reports"}
          </h3>
          <p>
            {detail.media_reports.length
              ? "Compare the retained original with its forensic indicators."
              : "No media report is attached to this case."}
          </p>
          {detail.media_reports.length > 0 && (
            <button className="text-action" onClick={() => onView("Media")}>
              Inspect media <ArrowRight size={13} />
            </button>
          )}
        </div>
      </div>
      <div className="brief-next">
        <FileCheck2 size={19} />
        <h3>
          {detail.claim_verification.status === "UNVERIFIED"
            ? "The claim still needs context."
            : "A review is on record."}
        </h3>
        <p>
          Coordination and media indicators do not establish whether a claim is
          true.
        </p>
        <button onClick={() => onView("Claims")}>
          Review claim evidence <ArrowRight size={14} />
        </button>
      </div>
      <div className="brief-provenance">
        <span>Snapshot {detail.snapshot_revision}</span>
        <span>
          {score(detail.cti_assessment.coverage_ratio * 100, 0)}% signal
          coverage
        </span>
        <p>
          Generated from retained snapshot fields. No inferred or invented
          findings.
        </p>
      </div>
    </div>
  );
}
