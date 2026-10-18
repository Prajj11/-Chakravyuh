"use client";
import { useState } from "react";
import { ArrowUpRight, Search, ShieldCheck } from "lucide-react";
import type {
  NarrativeCampaignDetail,
  NarrativeCampaignSummary,
} from "@/types/chakravyuh";
import { privateText, score } from "@/lib/privacy";

type Props = {
  campaigns: NarrativeCampaignSummary[];
  detail: NarrativeCampaignDetail | null;
  selected: string;
  privacy: boolean;
  onSelect: (id: string) => void;
};
export function CampaignFeed({
  campaigns,
  detail,
  selected,
  privacy,
  onSelect,
}: Props) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const title = (campaign: NarrativeCampaignSummary) =>
    detail?.campaign_id === campaign.campaign_id
      ? privateText(campaign.title, detail, privacy)
      : campaign.title.replace(/@[\p{L}\p{N}_]+/gu, "[participant]");
  const visible = campaigns.filter(
    (campaign) =>
      `${title(campaign)} ${campaign.languages.join(" ")} ${campaign.data_origin}`
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (filter !== "warnings" || campaign.cti_assessment.alert_eligible) &&
      (filter !== "unverified" ||
        campaign.claim_verification.status === "UNVERIFIED"),
  );
  return (
    <aside className="campaign-feed" aria-label="Campaign browser">
      <div className="feed-heading">
        <span className="eyebrow">INVESTIGATION QUEUE</span>
        <span className="count-badge">{campaigns.length}</span>
      </div>
      <h2>
        Active narratives<span>.</span>
      </h2>
      <div className="feed-search">
        <Search size={15} />
        <input
          type="search"
          aria-label="Search campaigns"
          placeholder="Find a narrative…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>
      <div className="feed-filters" aria-label="Campaign filters">
        {[
          ["all", "All cases"],
          ["warnings", "Warnings"],
          ["unverified", "Unverified"],
        ].map(([value, text]) => (
          <button
            key={value}
            aria-pressed={filter === value}
            onClick={() => setFilter(value)}
          >
            {text}
          </button>
        ))}
      </div>
      <span className="feed-results" role="status">
        {visible.length} {visible.length === 1 ? "case" : "cases"} · prioritized
        by CTI
      </span>
      <div className="campaign-list">
        {visible.map((campaign) => (
          <button
            key={campaign.campaign_id}
            className={`campaign-card ${selected === campaign.campaign_id ? "active" : ""}`}
            aria-current={
              selected === campaign.campaign_id ? "true" : undefined
            }
            onClick={() => onSelect(campaign.campaign_id)}
          >
            <div className="case-card-top">
              <span
                className={`tier ${campaign.cti_assessment.threat_level?.toLowerCase() ?? "unknown"}`}
              >
                {campaign.cti_assessment.threat_level ?? "INSUFFICIENT"}
              </span>
              <span className="card-cti">
                <b
                  aria-label={
                    campaign.cti_assessment.cti_score == null
                      ? "CTI insufficient data"
                      : undefined
                  }
                >
                  {campaign.cti_assessment.cti_score == null
                    ? "—"
                    : score(campaign.cti_assessment.cti_score)}
                </b>
                <small>CTI</small>
              </span>
            </div>
            <h3>{title(campaign)}</h3>
            <span className="origin-badge">
              {campaign.data_origin.replaceAll("_", " ")}
            </span>
            <div className="case-card-bottom">
              <span>
                {campaign.total_posts} posts <i>·</i> {campaign.total_accounts}{" "}
                accounts
              </span>
              <ArrowUpRight size={15} />
            </div>
          </button>
        ))}
        {!visible.length && (
          <div className="empty">
            {campaigns.length
              ? "No narratives match these filters."
              : "Your next investigation starts here. Open Scenario studio or inject an observation."}
            {campaigns.length > 0 && (
              <button
                onClick={() => {
                  setQuery("");
                  setFilter("all");
                }}
              >
                Clear campaign filters
              </button>
            )}
          </div>
        )}
      </div>
      <div className="feed-footnote">
        <ShieldCheck size={17} />
        <div>
          <strong>Evidence stays local</strong>
          <p>Computed indicators. Human-reviewed claims.</p>
        </div>
      </div>
    </aside>
  );
}
