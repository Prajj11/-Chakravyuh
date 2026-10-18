"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  Check,
  ChevronRight,
  Database,
  FileCheck2,
  Fingerprint,
  GitBranch,
  Globe2,
  Image,
  Layers3,
  LockKeyhole,
  Network,
  Plus,
  Radio,
  RefreshCw,
  Search,
  ShieldCheck,
  Terminal,
  Waypoints,
} from "lucide-react";
import { connectSession, getHealth } from "@/lib/api";
import type { HealthStatusResponse } from "@/types/chakravyuh";

const tabs = [
  {
    label: "Coordination",
    icon: Network,
    detail:
      "Repeated content-linked activity will appear here after the coordination engine is implemented.",
  },
  {
    label: "Geography",
    icon: Globe2,
    detail:
      "Source geography, collection coverage and scoped historical baselines are planned. No locations have been inferred.",
  },
  {
    label: "Media",
    icon: Image,
    detail:
      "Image uploads are available through the API. Computed ELA, pHash and provenance inspection are planned.",
  },
  {
    label: "Claims",
    icon: FileCheck2,
    detail:
      "Candidate references and contextual analyst review are planned. No claim has been verified.",
  },
] as const;

const layers = [
  {
    id: "ingestion",
    name: "Evidence & ingestion",
    note: "Exact bytes · SHA-256 · audit chain",
  },
  {
    id: "nlp_engine",
    name: "Narrative analytics",
    note: "Clustering & reference retrieval",
  },
  {
    id: "coordination",
    name: "Coordination",
    note: "Repeated pairs & bot indicators",
  },
  {
    id: "graph_engine",
    name: "Graph investigation",
    note: "Communities & observed roles",
  },
  {
    id: "geo_engine",
    name: "Geographic context",
    note: "Source coverage & baselines",
  },
  {
    id: "media_forensics",
    name: "Media indicators",
    note: "Computed ELA & perceptual hashes",
  },
  {
    id: "reporting",
    name: "CTI & dossiers",
    note: "Coverage gates & verified exports",
  },
];

export function Workbench() {
  const [health, setHealth] = useState<HealthStatusResponse | null>(null);
  const [connection, setConnection] = useState<
    "checking" | "connected" | "offline"
  >("checking");
  const [activeTab, setActiveTab] = useState(0);
  const [token, setToken] = useState("");
  const [authorized, setAuthorized] = useState(false);
  const [authorizing, setAuthorizing] = useState(false);
  const [sessionError, setSessionError] = useState("");
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const update = async () => {
      try {
        const result = await getHealth(
          AbortSignal.any([controller.signal, AbortSignal.timeout(5000)]),
        );
        if (!controller.signal.aborted) {
          setHealth(result);
          setConnection("connected");
        }
      } catch {
        if (!controller.signal.aborted) {
          setHealth(null);
          setConnection("offline");
        }
      }
    };
    void update();
    const timer = setInterval(() => void update(), 10000);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [refresh]);

  const authorize = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setAuthorizing(true);
      setSessionError("");
      try {
        await connectSession(token);
        setAuthorized(true);
        setToken("");
      } catch (error: unknown) {
        setSessionError(
          error instanceof Error ? error.message : "Session connection failed.",
        );
      } finally {
        setAuthorizing(false);
      }
    },
    [token],
  );

  const available = Object.values(health?.layer_status ?? {}).filter(
    (status) => status === "AVAILABLE",
  ).length;
  const selected = tabs[activeTab];

  return (
    <div className="workbench">
      <a href="#main-content" className="skip-link">
        Skip to investigation
      </a>
      <header className="topbar">
        <a className="brand" href="/" aria-label="Chakravyuh home">
          <span className="brand-mark">
            <Waypoints size={25} />
          </span>
          <span>
            CHAKRAVYUH<small>INVESTIGATION WORKBENCH</small>
          </span>
        </a>
        <div className="topbar-divider" />
        <span className="preview-label">
          FOUNDATION PREVIEW <span>v0.1</span>
        </span>
        <div className="header-actions">
          <span className="local-label">
            <LockKeyhole size={13} /> Local workspace
          </span>
          <button disabled title="Scenario replay is planned in Sprint 2">
            <Radio size={15} /> Scenarios
          </button>
          <button disabled title="Queued injection is not implemented yet">
            <Plus size={15} /> Inject
          </button>
          <button
            disabled
            title="Verified dossier exports are not implemented yet"
          >
            <ArrowDownToLine size={15} /> Export
          </button>
        </div>
      </header>

      <div className="workspace-body">
        <aside className="campaign-sidebar" aria-label="Campaign feed">
          <div className="sidebar-heading">
            <span>CAMPAIGNS</span>
            <span className="count">
              {health?.active_campaigns_count ?? "—"}
            </span>
          </div>
          <div className="search-placeholder">
            <Search size={14} /> Search available after analytics
          </div>
          <div className="feed-label">
            <span className="status-dot muted" /> NO ACTIVE COLLECTION
          </div>
          <div className="feed-empty">
            <Layers3 size={25} strokeWidth={1.3} />
            <strong>No campaigns yet</strong>
            <p>
              Captured evidence will become investigable campaigns as the
              analytical pipeline comes online.
            </p>
          </div>
          <div className="sidebar-note">
            <ShieldCheck size={18} />
            <p>
              Evidence first.
              <br />
              <span>
                Indicators support investigation. They do not establish intent
                or claim truth.
              </span>
            </p>
          </div>
          <div className="workspace-footer">
            <Database size={13} /> SQLite · local evidence store
          </div>
        </aside>

        <main id="main-content" className="main-panel">
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <span>Overview</span>
            <span className="origin-tag">LOCAL / OFFLINE CAPABLE</span>
          </div>
          <div className="page-heading">
            <div>
              <p className="eyebrow">OBSERVE. TRACE. VERIFY.</p>
              <h1>Your investigation starts with evidence.</h1>
              <p className="subtitle">
                A local foundation for examining coordinated activity, media and
                context.
              </p>
            </div>
            <div className="version-stamp">
              CONTRACT<span>2.1.0</span>
            </div>
          </div>

          <div className="telemetry" aria-label="Live backend telemetry">
            <div>
              <span className="metric-label">
                <Activity size={14} /> API CONNECTION
              </span>
              <strong
                className={
                  connection === "connected" ? "text-success" : "text-muted"
                }
              >
                {connection === "connected"
                  ? "Connected"
                  : connection === "checking"
                    ? "Checking…"
                    : "Offline"}
              </strong>
              <span>
                {connection === "connected"
                  ? "Loopback · native asyncio"
                  : "Start the backend on port 8001"}
              </span>
            </div>
            <div>
              <span className="metric-label">
                <Database size={14} /> RETAINED EVENTS
              </span>
              <strong className="numeric">
                {health?.total_ingested_events.toLocaleString() ?? "—"}
              </strong>
              <span>Immutable source evidence</span>
            </div>
            <div>
              <span className="metric-label">
                <GitBranch size={14} /> PIPELINE READINESS
              </span>
              <strong className="numeric">
                {health ? `${available}` : "—"}
                <em> / 7 layers</em>
              </strong>
              <span>Analytical engines pending</span>
            </div>
            <button
              className="refresh-button"
              onClick={() => setRefresh((value) => value + 1)}
              aria-label="Refresh backend status"
            >
              <RefreshCw size={16} />
            </button>
          </div>

          <section
            className="investigation-surface"
            aria-label="Investigation views"
          >
            <div
              className="view-tabs"
              role="tablist"
              aria-label="Investigation view"
            >
              {tabs.map((tab, index) => (
                <button
                  key={tab.label}
                  role="tab"
                  id={`tab-${index}`}
                  aria-selected={activeTab === index}
                  aria-controls="view-panel"
                  tabIndex={activeTab === index ? 0 : -1}
                  onKeyDown={(event) => {
                    const next =
                      event.key === "ArrowRight"
                        ? (index + 1) % tabs.length
                        : event.key === "ArrowLeft"
                          ? (index + tabs.length - 1) % tabs.length
                          : event.key === "Home"
                            ? 0
                            : event.key === "End"
                              ? tabs.length - 1
                              : null;
                    if (next !== null) {
                      event.preventDefault();
                      setActiveTab(next);
                      document.getElementById(`tab-${next}`)?.focus();
                    }
                  }}
                  onClick={() => setActiveTab(index)}
                >
                  <tab.icon size={16} />
                  {tab.label}
                </button>
              ))}
              <span className="no-snapshot">NO SNAPSHOT</span>
            </div>
            <div
              className="view-empty"
              role="tabpanel"
              id="view-panel"
              aria-labelledby={`tab-${activeTab}`}
              tabIndex={0}
            >
              <div className="empty-orbit">
                <span />
                <span />
                <Fingerprint size={38} strokeWidth={1.1} />
              </div>
              <span className="outlined-label">EVIDENCE FOUNDATION</span>
              <h2>
                {activeTab === 0
                  ? "Ready to retain. Built to verify."
                  : `${selected.label} is awaiting implementation.`}
              </h2>
              <p>{selected.detail}</p>
              <div className="evidence-flow">
                <span>
                  <Database size={14} /> Raw capture
                </span>
                <ArrowRight size={13} />
                <span>
                  <Fingerprint size={14} /> Canonical event
                </span>
                <ArrowRight size={13} />
                <span>
                  <ShieldCheck size={14} /> Chained audit
                </span>
              </div>
              <div className="empty-footnote">
                No calculated scores or inferred findings are displayed in this
                preview.
              </div>
            </div>
          </section>

          <section className="getting-started">
            <div className="section-title">
              <Terminal size={16} />
              <h2>Capture your first local event</h2>
              <span>DEVELOPER WORKFLOW</span>
            </div>
            <p>
              From the repository root, with the Python environment installed:
            </p>
            <code>
              .venv\Scripts\python.exe -m app.cli ingest
              sample_data/raw/local-example.json
            </code>
            <div className="command-note">
              <Check size={13} /> Retains raw input and canonical bytes, then
              appends an INGEST audit entry.
            </div>
          </section>
          <footer className="main-footer">
            <span>
              Coordination ≠ intent. Media anomalies ≠ verified manipulation.
            </span>
            <span>CHAKRAVYUH / LOCAL FIRST</span>
          </footer>
        </main>

        <aside
          className="readiness-sidebar"
          aria-label="Pipeline status and session"
        >
          <div className="sidebar-heading">
            <span>PIPELINE STATUS</span>
            <span className="status-dot" />
          </div>
          <p className="readiness-intro">
            A testable foundation.
            <br />
            <span>One layer at a time.</span>
          </p>
          <ol className="layer-list">
            {layers.map((layer, index) => {
              const ready = health?.layer_status[layer.id] === "AVAILABLE";
              return (
                <li key={layer.id}>
                  <span className={`layer-number ${ready ? "ready" : ""}`}>
                    {ready ? (
                      <Check size={13} />
                    ) : (
                      String(index + 1).padStart(2, "0")
                    )}
                  </span>
                  <div>
                    <strong>{layer.name}</strong>
                    <p>{layer.note}</p>
                    <span className={ready ? "layer-ready" : "layer-pending"}>
                      {ready
                        ? "AVAILABLE"
                        : health
                          ? "PENDING"
                          : "AWAITING API"}
                    </span>
                  </div>
                </li>
              );
            })}
          </ol>
          <section className="session-panel">
            <LockKeyhole size={18} />
            <h2>Local session</h2>
            <p>
              {authorized
                ? "Session authorized for this backend launch."
                : "Use the token in .runtime/local-session-token to authorize this browser."}
            </p>
            {authorized ? (
              <span className="session-connected">
                <Check size={13} /> AUTHORIZED
              </span>
            ) : (
              <form onSubmit={(event) => void authorize(event)}>
                <label htmlFor="session-token">Session token</label>
                <input
                  id="session-token"
                  type="password"
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                  autoComplete="off"
                  placeholder="Paste local token"
                  required
                  minLength={32}
                />
                <button
                  className="connect-button"
                  disabled={authorizing || !token}
                  type="submit"
                >
                  {authorizing ? "Connecting…" : "Connect session"}
                  <ArrowRight size={14} />
                </button>
              </form>
            )}
            <p className="session-error" role="alert">
              {sessionError}
            </p>
          </section>
        </aside>
      </div>
      <div className="statusbar">
        <span>
          <span
            className={`status-dot ${connection === "connected" ? "" : "muted"}`}
          />
          {connection === "connected"
            ? "API connected"
            : connection === "checking"
              ? "Checking API"
              : "API offline"}
          <span className="status-separator">/</span>Analytical stream not
          implemented
        </span>
        <span>
          CPU READY<span className="status-separator">/</span>NO CLOUD REQUIRED
        </span>
      </div>
    </div>
  );
}
