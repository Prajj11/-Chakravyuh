"use client";
import { useMemo, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  Fingerprint,
  Globe2,
  Network,
  Plus,
  Radio,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useWorkbench } from "@/lib/use-workbench";
import { label, privateText, score } from "@/lib/privacy";
import type { GraphEdge } from "@/types/chakravyuh";
import { GraphPanel } from "./graph/graph-panel";
import { Inspector } from "./graph/inspector";
import { GeoPanel } from "./map/geo-panel";
import { MediaPanel } from "./forensics/media-panel";
import { ClaimPanel } from "./claims/claim-panel";
import { TimelinePanel } from "./timeline/timeline-panel";
import { Assessment } from "./alerts/assessment";
import { ExportDialog, InjectDialog, Modal } from "./alerts/dialogs";
const tabs = ["Graph", "Geography", "Media", "Claims"] as const;
export function Workbench() {
  const work = useWorkbench();
  const [tokenInput, setTokenInput] = useState(""),
    [connecting, setConnecting] = useState(false),
    [tab, setTab] = useState<(typeof tabs)[number]>("Graph");
  const [scenario, setScenario] = useState("cmp_electoral_01"),
    [seed, setSeed] = useState(42),
    [speed, setSpeed] = useState(100),
    [reset, setReset] = useState(true),
    [confirmReset, setConfirmReset] = useState(false);
  const [dialog, setDialog] = useState<"inject" | "export" | null>(null),
    [privacy, setPrivacy] = useState(true),
    [selectedNode, setSelectedNode] = useState(""),
    [edge, setEdge] = useState<GraphEdge | null>(null),
    [cell, setCell] = useState(""),
    [cursor, setCursor] = useState<number | null>(null);
  const [postLimit, setPostLimit] = useState(100);
  const detail =
    work.detail?.campaign_id === work.selected ? work.detail : null;
  const highlight = useMemo(() => {
    const ids = new Set<string>();
    if (!detail) return ids;
    if (selectedNode) ids.add(selectedNode);
    if (edge) {
      ids.add(edge.source);
      ids.add(edge.target);
    }
    if (cell)
      for (const event of detail.sample_posts) {
        const report = detail.geo_anomalies.find(
          (report) => report.h3_index === cell,
        );
        if (
          event.geospatial.target_h3_index === cell ||
          (report?.region_name &&
            event.text.toLowerCase().includes(report.region_name.toLowerCase()))
        )
          ids.add(event.account.account_id);
      }
    return ids;
  }, [detail, selectedNode, edge, cell]);
  const clear = () => {
    setSelectedNode("");
    setEdge(null);
    setCell("");
    setCursor(null);
    setPostLimit(100);
  };
  const start = async () => {
    setConfirmReset(false);
    clear();
    try {
      await work.run(
        "/api/v1/simulate/scenario",
        {
          scenario_id: scenario,
          reset_state: reset,
          seed,
          speed_multiplier: speed,
        },
        "Replay",
      );
    } catch {
      /* Shared job error is rendered below. */
    }
  };
  const posts =
    detail?.sample_posts.filter(
      (event) =>
        (!highlight.size || highlight.has(event.account.account_id)) &&
        (cursor == null || Date.parse(event.timestamp_utc) <= cursor),
    ) ?? [];
  const authorize = async (event: React.FormEvent) => {
    event.preventDefault();
    setConnecting(true);
    try {
      await work.authorize(tokenInput);
      setTokenInput("");
    } catch (e) {
      work.setError(
        e instanceof Error ? e.message : "Session authorization failed",
      );
    } finally {
      setConnecting(false);
    }
  };
  return (
    <>
      <a className="skip-link" href="#investigation">
        Skip to investigation
      </a>
      <header className="topbar">
        <div className="brand">
          <div className="brand-symbol">
            <Fingerprint size={28} />
          </div>
          <div>
            <h1>CHAKRAVYUH</h1>
            <span>Evidence & coordination workbench</span>
          </div>
        </div>
        <div className="stream-status">
          <i
            className={
              work.stream === "Stream connected" ? "live-dot" : "idle-dot"
            }
          />
          {work.stream}
        </div>
        <div className="top-actions">
          <button
            disabled={!work.token || !!work.busy}
            onClick={() => setDialog("inject")}
          >
            <Plus size={15} />
            Inject event
          </button>
          <button
            disabled={!detail || !!work.busy}
            onClick={() => setDialog("export")}
          >
            <ArrowDownToLine size={15} />
            Export dossier
          </button>
          <button
            aria-label="Refresh snapshots"
            onClick={() => void work.refresh()}
          >
            <RefreshCw size={15} />
          </button>
        </div>
      </header>
      <div className="telemetry">
        <span>
          <Activity size={13} />
          {work.health?.status ?? "Checking backend"}
        </span>
        <span>
          {work.health?.active_campaigns_count ?? "—"} active narratives
        </span>
        <span>{work.health?.total_ingested_events ?? "—"} retained events</span>
        <span>CPU · local · frozen lexical fallback</span>
        <span className="mono">
          PIPELINE {work.health?.pipeline_version ?? "2.1.0"}
        </span>
      </div>
      {!work.token ? (
        <main className="welcome">
          <div className="welcome-copy">
            <span className="eyebrow">LOCAL-FIRST INVESTIGATION</span>
            <h2>
              Follow the evidence.
              <br />
              <em>Keep uncertainty visible.</em>
            </h2>
            <p>
              Inspect repeated amplification, observed networks, media
              compression anomalies and geographic context. Claim verification
              remains a separate human review.
            </p>
            <div className="welcome-icons">
              <Network />
              <Globe2 />
              <ShieldCheck />
            </div>
          </div>
          <section className="session-card">
            <h2>Connect your local session</h2>
            <p>
              The backend saves a fresh token in{" "}
              <code>.runtime/local-session-token</code>. Read it locally and
              paste it below.
            </p>
            <form onSubmit={authorize}>
              <label>
                Local session token
                <input
                  autoComplete="off"
                  type="password"
                  required
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder="Paste the current launch token"
                />
              </label>
              <button className="primary-button" disabled={connecting}>
                {connecting ? "Validating…" : "Connect session"}
              </button>
            </form>
            <p className="subtle">
              The token stays in memory for this tab and is cleared from the
              input after authorization.
            </p>
            {work.error && (
              <p role="alert" className="error">
                {work.error}
              </p>
            )}
          </section>
        </main>
      ) : (
        <>
          <div className="replay-controls">
            <span className="eyebrow">
              <Radio size={14} /> RAW REPLAY
            </span>
            <label>
              Scenario
              <select
                aria-label="Scenario"
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
              >
                <option value="cmp_electoral_01">
                  Electoral amplification
                </option>
                <option value="cmp_geo_astroturf_02">
                  Geographic mismatch
                </option>
                <option value="cmp_organic_03">Natural discussion</option>
                <option value="all">All three scenarios</option>
              </select>
            </label>
            <label>
              Seed
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
              />
            </label>
            <label>
              Speed
              <select
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
              >
                {[1, 10, 25, 50, 100].map((value) => (
                  <option key={value} value={value}>
                    {value}× event time
                  </option>
                ))}
              </select>
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={reset}
                onChange={(e) => setReset(e.target.checked)}
              />
              Reset active replay
            </label>
            <button
              className="primary-button"
              disabled={!!work.busy}
              onClick={() =>
                reset &&
                work.campaigns.some((c) => c.data_origin === "SYNTHETIC_REPLAY")
                  ? setConfirmReset(true)
                  : void start()
              }
            >
              Load raw scenario
            </button>
            <label className="check privacy-check">
              <input
                type="checkbox"
                checked={privacy}
                onChange={(e) => setPrivacy(e.target.checked)}
              />
              Mask low-indicator / unclassified identities
            </label>
          </div>
          {(work.busy || work.error || work.notice) && (
            <div
              className={work.error ? "status-banner error" : "status-banner"}
              role={work.error ? "alert" : "status"}
            >
              {work.error || work.busy || work.notice}
              {work.lastJob?.status === "SUCCEEDED" &&
                work.lastJob.artifact_download_url && (
                  <button
                    onClick={() =>
                      void work.download(work.lastJob!.artifact_download_url!)
                    }
                  >
                    Download completed package
                  </button>
                )}
            </div>
          )}
          <div className="workspace">
            <aside className="campaign-feed">
              <div className="panel-heading">
                <span className="eyebrow">NARRATIVE FEED</span>
                <span>{work.campaigns.length}</span>
              </div>
              {!work.campaigns.length && (
                <div className="empty">
                  No active campaigns. Load a raw replay or inject an event to
                  begin.
                </div>
              )}
              {work.campaigns.map((campaign) => (
                <button
                  key={campaign.campaign_id}
                  className={`campaign-card ${work.selected === campaign.campaign_id ? "active" : ""}`}
                  onClick={() => {
                    clear();
                    work.setSelected(campaign.campaign_id);
                  }}
                >
                  <div>
                    <span
                      className={`tier ${campaign.cti_assessment.threat_level?.toLowerCase() ?? "unknown"}`}
                    >
                      {campaign.cti_assessment.threat_level ?? "INSUFFICIENT"}
                    </span>
                    <b>{score(campaign.cti_assessment.cti_score)}</b>
                  </div>
                  <h3>
                    {detail?.campaign_id === campaign.campaign_id
                      ? privateText(campaign.title, detail, privacy)
                      : campaign.title.replace(
                          /@[\p{L}\p{N}_]+/gu,
                          "[participant]",
                        )}
                  </h3>
                  <span className="origin-badge">
                    {campaign.data_origin.replaceAll("_", " ")}
                  </span>
                  <small>
                    {campaign.total_posts} posts · {campaign.total_accounts}{" "}
                    accounts
                  </small>
                  <small>
                    Sync {score(campaign.coordination_assessment.sync_score, 3)}{" "}
                    · rev {campaign.snapshot_revision}
                  </small>
                </button>
              ))}
            </aside>
            <main id="investigation" className="investigation" tabIndex={-1}>
              {detail ? (
                <>
                  <div className="campaign-header">
                    <div className="badge-row">
                      <span className="origin-badge">
                        {detail.data_origin.replaceAll("_", " ")}
                      </span>
                      <span className="chip">
                        {detail.languages.join(" / ")}
                      </span>
                      <span className="chip">
                        Snapshot {detail.snapshot_revision}
                      </span>
                    </div>
                    <h2>{privateText(detail.title, detail, privacy)}</h2>
                    <p className="mono subtle">
                      {detail.first_detected_utc} → {detail.last_updated_utc}{" "}
                      UTC
                    </p>
                    <p className="subtle">
                      {detail.collection_window.coverage_completeness_note}
                    </p>
                  </div>
                  <Assessment detail={detail} />
                  <div
                    className="view-tabs"
                    role="tablist"
                    aria-label="Investigation views"
                  >
                    {tabs.map((name, index) => (
                      <button
                        role="tab"
                        id={`tab-${name}`}
                        aria-selected={tab === name}
                        aria-controls="active-panel"
                        tabIndex={tab === name ? 0 : -1}
                        key={name}
                        onClick={() => setTab(name)}
                        onKeyDown={(e) => {
                          if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                            e.preventDefault();
                            const next =
                              tabs[
                                (index +
                                  (e.key === "ArrowRight"
                                    ? 1
                                    : tabs.length - 1)) %
                                  tabs.length
                              ];
                            setTab(next);
                            document.getElementById(`tab-${next}`)?.focus();
                          }
                        }}
                      >
                        {name}
                      </button>
                    ))}
                  </div>
                  <div
                    className="active-panel"
                    role="tabpanel"
                    id="active-panel"
                    aria-labelledby={`tab-${tab}`}
                  >
                    {tab === "Graph" && (
                      <GraphPanel
                        detail={detail}
                        privacy={privacy}
                        selected={selectedNode}
                        onSelect={setSelectedNode}
                        onEdge={setEdge}
                        cursor={cursor}
                        highlight={highlight}
                      />
                    )}
                    {tab === "Geography" && (
                      <GeoPanel
                        detail={detail}
                        selected={cell}
                        onSelect={setCell}
                      />
                    )}
                    {tab === "Media" && (
                      <MediaPanel detail={detail} token={work.token} />
                    )}
                    {tab === "Claims" && (
                      <ClaimPanel
                        key={detail.campaign_id}
                        detail={detail}
                        token={work.token}
                        privacy={privacy}
                        onRefresh={work.refresh}
                      />
                    )}
                  </div>
                  <TimelinePanel
                    detail={detail}
                    cursor={cursor}
                    onCursor={setCursor}
                    highlight={highlight}
                  />
                  <section className="observations">
                    <div className="panel-heading">
                      <h2>Linked observations</h2>
                      <button onClick={clear}>Clear cross-filters</button>
                    </div>
                    <p className="subtle">
                      {posts.length} of {detail.total_posts} retained
                      observations · exact evidence text, with optional
                      participant masking
                    </p>
                    <div className="post-list">
                      {posts.slice(0, postLimit).map((event) => {
                        const node = detail.nodes.find(
                          (node) => node.id === event.account.account_id,
                        );
                        return (
                          <article key={event.event_id}>
                            <div>
                              <strong>
                                {node
                                  ? label(node, privacy)
                                  : "Observed account"}
                              </strong>
                              <time>{event.timestamp_utc}</time>
                            </div>
                            <p>{privateText(event.text, detail, privacy)}</p>
                            <details>
                              <summary>
                                Evidence hashes and capture lineage
                              </summary>
                              <code className="hash">
                                Raw SHA-256: {event.raw_payload_sha256}
                              </code>
                              <code className="hash">
                                Canonical SHA-256:{" "}
                                {event.canonical_event_sha256}
                              </code>
                              <p>
                                Captured {event.collection_timestamp_utc} ·{" "}
                                {event.collector_id} ·{" "}
                                {event.raw_capture_format}
                              </p>
                            </details>
                          </article>
                        );
                      })}
                    </div>
                    {posts.length > postLimit && (
                      <button
                        onClick={() => setPostLimit((limit) => limit + 100)}
                      >
                        Show next {Math.min(100, posts.length - postLimit)}{" "}
                        observations ({Math.min(postLimit, posts.length)} shown)
                      </button>
                    )}
                  </section>
                </>
              ) : (
                <div className="empty large-empty">
                  {work.campaigns.length
                    ? "Loading one coherent campaign snapshot…"
                    : "Load a scenario to compute the first narrative snapshots. Results are derived from retained inputs."}
                </div>
              )}
            </main>
            {detail ? (
              <Inspector
                detail={detail}
                selected={selectedNode}
                edge={edge}
                privacy={privacy}
                onClear={clear}
              />
            ) : (
              <aside className="inspector">
                <span className="eyebrow">EVIDENCE, BEFORE ATTRIBUTION</span>
                <p className="subtle">
                  Synchrony does not establish automation, intent or claim
                  falsity. Missing measurements remain unavailable.
                </p>
              </aside>
            )}
          </div>
        </>
      )}
      <footer>
        Chakravyuh · local computed indicators · evidence stays on this machine
        · no external dispatch
      </footer>
      {dialog === "inject" && (
        <InjectDialog
          token={work.token}
          run={work.run}
          onClose={() => setDialog(null)}
        />
      )}
      {dialog === "export" && detail && (
        <ExportDialog
          detail={detail}
          run={work.run}
          download={work.download}
          onClose={() => setDialog(null)}
        />
      )}
      {confirmReset && (
        <Modal
          title="Replace active replay state?"
          onClose={() => setConfirmReset(false)}
        >
          <p>
            Existing replay jobs will fail with GENERATION_RESET. Retained
            evidence and injected/public partitions remain available.
          </p>
          <button className="primary-button" onClick={() => void start()}>
            Reset replay and load scenario
          </button>
        </Modal>
      )}
    </>
  );
}
