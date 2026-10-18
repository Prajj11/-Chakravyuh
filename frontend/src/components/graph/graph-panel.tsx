"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from "d3-force";
import type {
  AccountRole,
  GraphEdge,
  NarrativeCampaignDetail,
} from "@/types/chakravyuh";
import { label, roleLabel } from "@/lib/privacy";

export const roleColors: Record<AccountRole, string> = {
  EARLIEST_OBSERVED_SEED: "#ef4444",
  BOT_AMPLIFIER: "#f59e0b",
  BRIDGE_INFLUENCER: "#a855f7",
  ORGANIC_USER: "#10b981",
  UNCLASSIFIED: "#94a3b8",
};
type Dot = SimulationNodeDatum & {
  id: string;
  role: AccountRole;
  community: number;
};
type Link = SimulationLinkDatum<Dot> & { edge: GraphEdge };
type Props = {
  detail: NarrativeCampaignDetail;
  privacy: boolean;
  selected: string;
  onSelect: (id: string) => void;
  onEdge: (edge: GraphEdge | null) => void;
  cursor: number | null;
  highlight: Set<string>;
};
export function GraphPanel({
  detail,
  privacy,
  selected,
  onSelect,
  onEdge,
  cursor,
  highlight,
}: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const host = useRef<HTMLDivElement>(null);
  const geometry = useRef<{ dots: Dot[]; links: Link[] }>({
    dots: [],
    links: [],
  });
  const [threshold, setThreshold] = useState(0.65);
  const [roles, setRoles] = useState<Set<AccountRole>>(
    new Set(Object.keys(roleColors) as AccountRole[]),
  );
  const [lens, setLens] = useState("all"),
    [search, setSearch] = useState("");
  const visible = useMemo(
    () =>
      detail.nodes.filter(
        (node) =>
          roles.has(node.role) &&
          (cursor == null || Date.parse(node.first_observed_utc) <= cursor),
      ),
    [detail, roles, cursor],
  );
  useEffect(() => {
    if (!canvas.current || !host.current) return;
    const surface = canvas.current,
      container = host.current;
    const draw = () => {
      const width = container.clientWidth,
        height = 420,
        ratio = window.devicePixelRatio || 1;
      surface.width = width * ratio;
      surface.height = height * ratio;
      surface.style.height = `${height}px`;
      const ctx = surface.getContext("2d");
      if (!ctx) return;
      ctx.scale(ratio, ratio);
      const dots: Dot[] = visible.map((node, i) => ({
        id: node.id,
        role: node.role,
        community: node.community_id,
        x: width / 2 + Math.cos(i * 2.399) * Math.sqrt(i + 1) * 16,
        y: height / 2 + Math.sin(i * 2.399) * Math.sqrt(i + 1) * 16,
      }));
      const ids = new Set(dots.map((n) => n.id));
      const links: Link[] = detail.edges
        .filter(
          (edge) =>
            ids.has(edge.source) &&
            ids.has(edge.target) &&
            (edge.interaction_type !== "CO_POST_SYNC" ||
              (lens !== "cascade" && (edge.sync_weight ?? 0) >= threshold)) &&
            (lens !== "coordinated" ||
              edge.interaction_type === "CO_POST_SYNC"),
        )
        .map((edge) => ({ source: edge.source, target: edge.target, edge }));
      const simulation = forceSimulation(dots)
        .force(
          "link",
          forceLink<Dot, Link>(links)
            .id((node) => node.id)
            .distance(68)
            .strength(0.13),
        )
        .force("charge", forceManyBody().strength(-95))
        .force("center", forceCenter(width / 2, height / 2))
        .force("collide", forceCollide(13))
        .stop();
      simulation.tick(Math.min(150, Math.max(35, 220 - dots.length / 3)));
      for (const dot of dots) {
        dot.x = Math.max(24, Math.min(width - 24, dot.x ?? 0));
        dot.y = Math.max(24, Math.min(height - 24, dot.y ?? 0));
      }
      ctx.clearRect(0, 0, width, height);
      for (const community of new Set(dots.map((dot) => dot.community))) {
        const group = dots.filter((dot) => dot.community === community);
        if (group.length < 3) continue;
        const xs = group.map((n) => n.x ?? 0),
          ys = group.map((n) => n.y ?? 0);
        ctx.fillStyle = "#38bdf809";
        ctx.strokeStyle = "#38bdf81c";
        const cx = (Math.min(...xs) + Math.max(...xs)) / 2,
          cy = (Math.min(...ys) + Math.max(...ys)) / 2;
        const hull = convexHull(
          group.map((dot) => {
            const dx = (dot.x ?? 0) - cx,
              dy = (dot.y ?? 0) - cy,
              length = Math.hypot(dx, dy) || 1;
            return [
              (dot.x ?? 0) + (dx / length) * 15,
              (dot.y ?? 0) + (dy / length) * 15,
            ] as [number, number];
          }),
        );
        ctx.beginPath();
        hull.forEach(([x, y], index) =>
          index ? ctx.lineTo(x, y) : ctx.moveTo(x, y),
        );
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      }
      for (const link of links) {
        if (typeof link.source !== "object" || typeof link.target !== "object")
          continue;
        const a = link.source,
          b = link.target;
        ctx.strokeStyle =
          link.edge.interaction_type === "CO_POST_SYNC"
            ? "#2b769555"
            : "#a8b9dc88";
        ctx.setLineDash(
          link.edge.interaction_type === "CO_POST_SYNC" ? [3, 4] : [],
        );
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(a.x ?? 0, a.y ?? 0);
        ctx.lineTo(b.x ?? 0, b.y ?? 0);
        ctx.stroke();
        if (link.edge.interaction_type !== "CO_POST_SYNC") {
          const angle = Math.atan2(
            (b.y ?? 0) - (a.y ?? 0),
            (b.x ?? 0) - (a.x ?? 0),
          );
          const x = (b.x ?? 0) - Math.cos(angle) * 10,
            y = (b.y ?? 0) - Math.sin(angle) * 10;
          ctx.setLineDash([]);
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.lineTo(
            x - Math.cos(angle - 0.5) * 7,
            y - Math.sin(angle - 0.5) * 7,
          );
          ctx.lineTo(
            x - Math.cos(angle + 0.5) * 7,
            y - Math.sin(angle + 0.5) * 7,
          );
          ctx.closePath();
          ctx.fillStyle = "#a8b9dc";
          ctx.fill();
        }
      }
      ctx.setLineDash([]);
      for (const dot of dots) {
        ctx.globalAlpha = highlight.size && !highlight.has(dot.id) ? 0.25 : 1;
        ctx.beginPath();
        ctx.arc(
          dot.x ?? 0,
          dot.y ?? 0,
          dot.id === selected
            ? 8
            : dot.role === "EARLIEST_OBSERVED_SEED"
              ? 7
              : 5,
          0,
          Math.PI * 2,
        );
        ctx.fillStyle = roleColors[dot.role];
        ctx.fill();
        if (dot.id === selected) {
          ctx.strokeStyle = "#fff";
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;
      simulation.stop();
      geometry.current = { dots, links };
    };
    const observer = new ResizeObserver(draw);
    observer.observe(container);
    draw();
    return () => observer.disconnect();
  }, [detail, visible, threshold, lens, selected, highlight]);
  const pick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const box = event.currentTarget.getBoundingClientRect(),
      x = event.clientX - box.left,
      y = event.clientY - box.top;
    const dot = geometry.current.dots.find(
      (n) => Math.hypot((n.x ?? 0) - x, (n.y ?? 0) - y) < 13,
    );
    if (dot) {
      onSelect(dot.id);
      onEdge(null);
      return;
    }
    const found = geometry.current.links.find((link) => {
      if (typeof link.source !== "object" || typeof link.target !== "object")
        return false;
      const ax = link.source.x ?? 0,
        ay = link.source.y ?? 0,
        bx = link.target.x ?? 0,
        by = link.target.y ?? 0;
      const t = Math.max(
        0,
        Math.min(
          1,
          ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) /
            ((bx - ax) ** 2 + (by - ay) ** 2 || 1),
        ),
      );
      return Math.hypot(x - ax - t * (bx - ax), y - ay - t * (by - ay)) < 4;
    });
    onEdge(found?.edge ?? null);
  };
  return (
    <section>
      <div className="panel-heading">
        <div>
          <span className="eyebrow">OBSERVED ACCOUNT NETWORK</span>
          <h2>Coordination graph</h2>
        </div>
        <span className="chip">
          {visible.length} nodes · revision {detail.snapshot_revision}
        </span>
      </div>
      <div className="graph-controls">
        <label>
          Sync edge threshold <output>{threshold.toFixed(2)}</output>
          <input
            aria-label="Sync edge threshold"
            type="range"
            min=".2"
            max=".95"
            step=".01"
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
          />
        </label>
        <select
          aria-label="Graph lens"
          value={lens}
          onChange={(e) => setLens(e.target.value)}
        >
          <option value="all">Full discourse</option>
          <option value="coordinated">Sync projection</option>
          <option value="cascade">Observed cascade</option>
        </select>
        <button
          onClick={() => {
            setThreshold(0.65);
            setRoles(new Set(Object.keys(roleColors) as AccountRole[]));
            setLens("all");
          }}
        >
          Reset filters
        </button>
      </div>
      <div className="role-legend">
        {(Object.keys(roleColors) as AccountRole[]).map((role) => (
          <label key={role}>
            <input
              type="checkbox"
              checked={roles.has(role)}
              onChange={() =>
                setRoles((prev) => {
                  const next = new Set(prev);
                  if (next.has(role)) next.delete(role);
                  else next.add(role);
                  return next;
                })
              }
            />
            <i style={{ background: roleColors[role] }} />
            {roleLabel(role)}
          </label>
        ))}
      </div>
      <div className="graph-surface" ref={host}>
        <canvas
          ref={canvas}
          onClick={pick}
          onMouseMove={(event) => {
            const box = event.currentTarget.getBoundingClientRect();
            const dot = geometry.current.dots.find(
              (dot) =>
                Math.hypot(
                  (dot.x ?? 0) - (event.clientX - box.left),
                  (dot.y ?? 0) - (event.clientY - box.top),
                ) < 12,
            );
            const node = detail.nodes.find((node) => node.id === dot?.id);
            event.currentTarget.title = node
              ? `${label(node, privacy)} · ${roleLabel(node.role)} · first observed ${node.first_observed_utc} · bot ${node.bot_assessment.bot_indicator_score ?? "unavailable"} /100 · sync ${node.sync_assessment.sync_score ?? "unavailable"}`
              : "Use the searchable account list for keyboard inspection";
          }}
          aria-label="Observed account network; use the searchable node list for keyboard inspection"
          role="img"
        />
        {visible.length === 0 && (
          <p className="canvas-empty">
            No accounts match these filters. Reset filters to restore the graph.
          </p>
        )}
        <span className="canvas-caption">
          Dashed: symmetric sync · arrows: observed interactions · hulls:
          communities
        </span>
      </div>
      <div className="node-search">
        <input
          aria-label="Search accounts"
          placeholder="Search visible accounts or roles…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <span>{detail.edges.length} retained edges</span>
      </div>
      <div className="node-list" aria-label="Accessible account list">
        {visible
          .filter((node) =>
            `${label(node, privacy)} ${roleLabel(node.role)}`
              .toLowerCase()
              .includes(search.toLowerCase()),
          )
          .map((node) => (
            <button
              className={node.id === selected ? "selected" : ""}
              key={node.id}
              onClick={() => {
                onSelect(node.id);
                onEdge(null);
              }}
            >
              <i style={{ background: roleColors[node.role] }} />
              {label(node, privacy)}
              <small>{roleLabel(node.role)}</small>
            </button>
          ))}
      </div>
    </section>
  );
}

function convexHull(points: [number, number][]): [number, number][] {
  const sorted = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (
    a: [number, number],
    b: [number, number],
    c: [number, number],
  ) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
  const half = (items: [number, number][]) => {
    const result: [number, number][] = [];
    for (const point of items) {
      while (
        result.length > 1 &&
        cross(result[result.length - 2], result[result.length - 1], point) <= 0
      )
        result.pop();
      result.push(point);
    }
    return result.slice(0, -1);
  };
  return [...half(sorted), ...half([...sorted].reverse())];
}
