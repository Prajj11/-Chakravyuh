"use client";
import { useMemo, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  ChevronRight,
  FileCheck2,
  ScanLine,
  SlidersHorizontal,
  Users,
  MessagesSquare,
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
import { BrandMark, SignalIllustration } from "./brand-mark";
import demoCases from "@/lib/scenario-catalogue.json";
import { CampaignFeed } from "./campaign-feed";
import { ExportDialog, InjectDialog, Modal } from "./alerts/dialogs";
const tabs = ["Graph", "Geography", "Media", "Claims"] as const;
const tabIcons = {
  Graph: Network,
  Geography: Globe2,
  Media: ScanLine,
  Claims: FileCheck2,
};
const utcLabel = (value: string) =>
  new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
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
  const [showReplay, setShowReplay] = useState(false);
  const [batchMode, setBatchMode] = useState(false);
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
          playback_mode: batchMode ? "BATCH" : "TIMED",
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
            <BrandMark />
          </div>
          <div>
            <h1>CHAKRAVYUH</h1>
            <span>INTELLIGENCE WORKSPACE</span>
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
          {work.token && (
            <button
              aria-label="Mask low-indicator and unclassified identities"
              aria-pressed={privacy}
              title="Mask low-indicator and unclassified identities"
              onClick={() => setPrivacy(!privacy)}
            >
              <ShieldCheck size={15} />
              Privacy {privacy ? "on" : "off"}
            </button>
          )}
          {work.token && (
            <button
              className="studio-toggle"
              aria-expanded={showReplay}
              aria-controls="scenario-studio"
              onClick={() => setShowReplay(!showReplay)}
            >
              <SlidersHorizontal size={15} />
              Scenario studio
            </button>
          )}
          <button
            disabled={!work.token || !!work.busy}
            onClick={() => setDialog("inject")}
          >
            <Plus size={15} />
            Inject event
          </button>
          <button
            className="primary-button"
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
        <span>
          CPU · local ·{" "}
          {work.detail
            ? work.detail.claim_verification.computation_mode ===
              "MODEL_INFERENCE"
              ? "cached multilingual model"
              : "frozen lexical fallback"
            : "text pipeline ready"}
        </span>
        <span className="mono">
          PIPELINE {work.health?.pipeline_version ?? "2.1.0"}
        </span>
      </div>
      {!work.token ? (
        <main className="welcome">
          <div className="welcome-copy">
            <span className="eyebrow welcome-kicker">
              <span className="live-dot" /> OBSERVE. CONNECT. VERIFY.
            </span>
            <h2>
              Find the pattern.
              <br />
              <em>Follow the evidence.</em>
            </h2>
            <p>
              See how narratives travel, who amplifies them, and what the
              evidence actually supports. One workspace for a complete
              investigation.
            </p>
            <SignalIllustration />
          </div>
          <section className="session-card">
            <div className="session-icon">
              <ShieldCheck size={23} />
            </div>
            <span className="eyebrow">YOUR SECURE WORKSPACE</span>
            <h2>Start investigating</h2>
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
          <div
            className="replay-controls"
            id="scenario-studio"
            hidden={!showReplay}
          >
            <span className="eyebrow">
              <Radio size={14} /> SCENARIO STUDIO
            </span>
            <label>
              Scenario
              <select
                aria-label="Scenario"
                value={scenario}
                onChange={(e) => {
                  setScenario(e.target.value);
                  setBatchMode(
                    e.target.value === "expanded" ||
                      e.target.value.startsWith("demo_"),
                  );
                }}
              >
                <option value="cmp_electoral_01">
                  Electoral amplification
                </option>
                <option value="cmp_geo_astroturf_02">
                  Geographic mismatch
                </option>
                <option value="cmp_organic_03">Natural discussion</option>
                <option value="all">All three scenarios</option>
                <option value="expanded">25 diverse cases · 7,500 posts</option>
                <optgroup label="Diverse synthetic cases · 300 posts each">
                  {demoCases.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.city} — {item.title}
                    </option>
                  ))}
                </optgroup>
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
                disabled={batchMode}
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
                checked={batchMode}
                onChange={(e) => setBatchMode(e.target.checked)}
              />
              Fast batch load (skip playback delays)
            </label>
            <span className="subtle">
              {scenario === "expanded"
                ? "25 fictional cases · 7,500 posts · 1,500 accounts. "
                : ""}
              {batchMode
                ? "Scores are computed per case; intermediate warning times are not replayed."
                : "Timed playback uses original event timestamps."}
            </span>
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
            <CampaignFeed
              campaigns={work.campaigns}
              detail={detail}
              selected={work.selected}
              privacy={privacy}
              onSelect={(id) => {
                clear();
                work.setSelected(id);
              }}
            />
            <main id="investigation" className="investigation" tabIndex={-1}>
              {detail ? (
                <>
                  <div className="campaign-header">
                    <div className="case-breadcrumb">
                      <span>Investigations</span>
                      <ChevronRight size={13} />
                      <span>Active case</span>
                      <span className="case-revision">
                        SNAPSHOT {detail.snapshot_revision}
                      </span>
                    </div>
                    <div className="badge-row">
                      <span className="origin-badge">
                        {detail.data_origin.replaceAll("_", " ")}
                      </span>
                      <span className="chip">
                        {detail.languages.join(" / ")}
                      </span>
                      <span className="case-time">
                        {utcLabel(detail.first_detected_utc)} UTC
                      </span>
                    </div>
                    <h2>{privateText(detail.title, detail, privacy)}</h2>
                    <div className="case-stats">
                      <span>
                        <MessagesSquare size={14} />
                        <b>{detail.total_posts.toLocaleString()}</b>{" "}
                        observations
                      </span>
                      <span>
                        <Users size={14} />
                        <b>{detail.total_accounts.toLocaleString()}</b> accounts
                      </span>
                      <span>
                        <Network size={14} />
                        <b>{detail.edges.length.toLocaleString()}</b> observed
                        links
                      </span>
                      <span>
                        <ScanLine size={14} />
                        <b>{detail.media_reports.length}</b> media reports
                      </span>
                    </div>
                    <details className="collection-details">
                      <summary>Collection window & attribution limits</summary>
                      <p>
                        {detail.first_detected_utc} → {detail.last_updated_utc}{" "}
                        UTC
                      </p>
                      <p>
                        {detail.collection_window.coverage_completeness_note}
                      </p>
                    </details>
                  </div>
                  <Assessment detail={detail} />
                  <div
                    className="view-tabs"
                    role="tablist"
                    aria-label="Investigation views"
                  >
                    {tabs.map((name, index) => {
                      const Icon = tabIcons[name];
                      return (
                        <button
                          role="tab"
                          id={`tab-${name}`}
                          aria-selected={tab === name}
                          aria-controls="active-panel"
                          tabIndex={tab === name ? 0 : -1}
                          key={name}
                          onClick={() => setTab(name)}
                          onKeyDown={(e) => {
                            if (
                              e.key === "ArrowRight" ||
                              e.key === "ArrowLeft"
                            ) {
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
                          <Icon size={16} />
                          {name}
                        </button>
                      );
                    })}
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
                    markers={work.markers.filter(
                      (marker) => marker.campaignId === detail.campaign_id,
                    )}
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
                  <BrandMark large />
                  <span className="eyebrow">READY WHEN YOU ARE</span>
                  <h2>
                    {work.campaigns.length
                      ? "Opening your investigation…"
                      : "Every investigation starts with a signal."}
                  </h2>
                  <p>
                    {work.campaigns.length
                      ? "Loading one coherent evidence snapshot."
                      : "Explore a computed scenario, or bring an observation of your own."}
                  </p>
                  {!work.campaigns.length && (
                    <button
                      className="primary-button"
                      onClick={() => setShowReplay(true)}
                    >
                      <Radio size={15} />
                      Open Scenario studio
                    </button>
                  )}
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
                onNode={(id) => {
                  clear();
                  setSelectedNode(id);
                  setTab("Graph");
                }}
                onEdge={(selectedEdge) => {
                  clear();
                  setEdge(selectedEdge);
                  setTab("Graph");
                }}
                onView={(view) => {
                  setTab(view);
                  document.getElementById(`tab-${view}`)?.focus();
                }}
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
        Chakravyuh · Evidence-led intelligence{" "}
        <span>Local workspace · Human-reviewed claims</span>
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
