import React, { useState, useMemo, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { hierarchy, tree } from "d3-hierarchy";
import { linkHorizontal } from "d3-shape";
import { getAnomalyList, getDynamicTree } from "../api/api";

// Color by domain
const COLORS = {
  "Volt-related": "#f59e0b",
  "Temp-related": "#10b981",
  "Pressure-related": "#ef4444",
  "Cross-domain": "#3b82f6",
};

// Extended color palette for additional domains
const EXTENDED_COLORS = [
  "#8b5cf6", // purple
  "#ec4899", // pink
  "#14b8a6", // teal
  "#f97316", // orange
  "#06b6d4", // cyan
  "#84cc16", // lime
  "#a855f7", // violet
  "#ef4444", // red
  "#22c55e", // green
  "#6366f1", // indigo
];

/**
 * Generate a consistent color for a domain based on its name
 * Uses hash function to ensure same domain always gets same color
 */
function getDomainColor(domain) {
  // Check if domain has a predefined color
  if (COLORS[domain]) {
    return COLORS[domain];
  }
  
  // Generate color based on domain name hash
  let hash = 0;
  for (let i = 0; i < domain.length; i++) {
    hash = domain.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  // Use hash to select from extended color palette
  const colorIndex = Math.abs(hash) % EXTENDED_COLORS.length;
  return EXTENDED_COLORS[colorIndex];
}

/**
 * Classification display rule:
 * - "Volt-related" → "Volt-related"
 * - "Volt-related - DominantVoltPeaks" → "Volt-related"
 * - "Volt-related - DominantVoltPeaks-StrongDominantPeaks" → "DominantVoltPeaks"
 */
function displayClassification(path = "") {
  const raw = String(path || "").trim();
  if (!raw) return "";
  const parts = raw.split(" - ").map((s) => s.trim());
  const top = parts[0] || raw;
  if (parts.length < 2) return top;
  const child = parts[1];
  const sub = child.split("-").map((s) => s.trim());
  if (sub.length >= 2) {
    // "Volt-related - DominantVoltPeaks-StrongDominantPeaks" → "DominantVoltPeaks"
    return sub[0];
  }
  // "Volt-related - DominantVoltPeaks" → "Volt-related"
  return top;
}

/**
 * normalizeText / tokenize / jaccard / findBestRowForTemplate:
 * Used so: click a gray template node in Graph → open drawer with
 * the best matching anomaly row (pi00..pi06).
 */
function normalizeText(s = "") {
  const t = String(s).toLowerCase();
  const out = [];
  let word = "";
  for (let i = 0; i < t.length; i++) {
    const ch = t[i];
    const isAlnum =
      (ch >= "a" && ch <= "z") || (ch >= "0" && ch <= "9");
    if (isAlnum) {
      word += ch;
    } else {
      if (word) {
        out.push(word);
        word = "";
      }
    }
  }
  if (word) out.push(word);
  return out.join(" ").trim();
}

function tokenize(s = "") {
  const out = new Set();
  const norm = normalizeText(s).split(" ");
  for (const w of norm) {
    if (w.length > 2) out.add(w);
  }
  return out;
}

function jaccard(aSet, bSet) {
  let inter = 0;
  for (const w of aSet) if (bSet.has(w)) inter++;
  const union = aSet.size + bSet.size - inter;
  return union === 0 ? 0 : inter / union;
}

function findBestRowForTemplate(rows, domain, templateText) {
  const normT = normalizeText(templateText);

  // 1) exact or substring
  let exact = rows.find((r) => {
    const t = normalizeText(r.template);
    return (
      t === normT || t.includes(normT) || normT.includes(t)
    );
  });
  if (exact) return { row: exact, reason: "exact" };

  // 2) similarity preferring rows in same top-level domain
  const topDomain = String(domain || "").split(" - ")[0];
  const pool = rows.filter((r) =>
    String(r.classification || "").startsWith(topDomain)
  );
  const tokT = tokenize(normT);
  const candidates = pool.length ? pool : rows;

  let best = null;
  let bestScore = -1;
  for (const r of candidates) {
    const score = jaccard(tokT, tokenize(r.template));
    if (score > bestScore) {
      bestScore = score;
      best = r;
    }
  }
  return {
    row: best || candidates[0] || null,
    reason: "similar",
    score: bestScore,
  };
}

/** ----------- minimal addition: API row → UI row mapper ----------- */
function mapApiRow(r = {}) {
  const contributions = {};
  for (const [k, v] of Object.entries(r)) {
    if (k.startsWith("contribution_")) {
      contributions[k.replace(/^contribution_/, "")] = v;
    }
  }
  return {
    device: r.device ?? r.dev ?? "",
    ts: r.ts ?? r.timestamp ?? "",
    classification: r.classification ?? "",
    score: r.overall_anomaly_score ?? r.score ?? null,
    template: r.template ?? "",
    contributions,
  };
}
/** ----------------------------------------------------------------- */

/**
 * Grab top N contributions for the bar chart.
 */
function getTop(contrib, n = 5) {
  return Object.entries(contrib || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([name, value]) => ({ name, value }));
}

/**
 * Convert TAXONOMY object to a hierarchy we can render in the Graph tab.
 */
function buildTreeRecursive(data, nodeName, topDomain) {
  // Arrays are leaf template lists
  if (Array.isArray(data)) {
    return {
      name: nodeName,
      domain: topDomain ?? nodeName,
      children: [],
      templates: data,
    };
  }

  // Objects are groups / categories
  if (typeof data === "object" && data !== null) {
    const domainForChildren = topDomain ?? nodeName;
    const node = {
      name: nodeName,
      domain: domainForChildren,
      children: [],
      templates: [],
    };
    for (const [childKey, childVal] of Object.entries(data)) {
      node.children.push(
        buildTreeRecursive(childVal, childKey, domainForChildren)
      );
    }
    return node;
  }

  // Fallback: raw string
  return {
    name: nodeName,
    domain: topDomain ?? nodeName,
    children: [],
    templates: [String(data)],
  };
}

function convertJsonToTree(taxonomy) {
  const root = { name: "root", children: [] };
  for (const [domainKey, domainVal] of Object.entries(taxonomy)) {
    root.children.push(
      buildTreeRecursive(domainVal, domainKey, domainKey)
    );
  }
  return root;
}

// shallow clone helper to avoid mutating original
function cloneNode(n) {
  return {
    name: n.name,
    domain: n.domain,
    templates: n.templates ? [...n.templates] : [],
    children: n.children ? n.children.map(cloneNode) : [],
  };
}

/**
 * buildExpandedTree:
 * If a node is "expanded", we take its templates (strings)
 * and turn each into its own clickable gray child node.
 */
function buildExpandedTree(root, expanded) {
  const copy = cloneNode(root);

  (function walk(n) {
    if (n.templates && n.templates.length > 0 && expanded[n.name]) {
      n.children = n.children || [];
      n.templates.forEach((t) =>
        n.children.push({
          name: t,
          domain: n.domain,
          templates: [],
          children: [],
          isTemplate: true, // mark leaf for click-to-open
        })
      );
    }

    (n.children || []).forEach(walk);
  })(copy);

  return copy;
}

/**
 * SVG Tree renderer for the Graph tab.
 * - Colored boxes for groups/categories
 * - Gray boxes for template sentences
 * - Clicking gray opens drawer
 * - Shift+Click filters List tab to that node text
 */
function GraphTree({ root, onNodeClick }) {
  const NODE_W = 160;
  const NODE_H = 40;

  const layout = useMemo(() => {
    const h = hierarchy(root, (d) => d.children);

    tree()
      .nodeSize([70, 240])
      .separation((a, b) => (a.parent === b.parent ? 1.2 : 1.6))(h);

    const nodes = h.descendants();
    const links = h.links();

    const minX = Math.min(...nodes.map((n) => n.x));
    const maxX = Math.max(...nodes.map((n) => n.x));
    const minY = Math.min(...nodes.map((n) => n.y));
    const maxY = Math.max(...nodes.map((n) => n.y));

    const margin = { top: 20, right: 40, bottom: 20, left: 40 };

    const width =
      maxY - minY + margin.left + margin.right + NODE_W + 24;
    const height =
      maxX - minX + margin.top + margin.bottom + NODE_H;

    const offsetX = margin.left - minY;
    const offsetY = margin.top - minX;

    return { nodes, links, width, height, offsetX, offsetY };
  }, [root]);

  const linkGen = useMemo(
    () =>
      linkHorizontal()
        .x((d) => d[0])
        .y((d) => d[1]),
    []
  );

  return (
    <svg
      style={{ minHeight: `${layout.height}px`, width: "100%" }}
      viewBox={`0 0 ${layout.width} ${layout.height}`}
    >
      {/* draw edges */}
      {layout.links.map((l, i) => {
        const d = linkGen({
          source: [
            l.source.y + layout.offsetX + NODE_W,
            l.source.x + layout.offsetY,
          ],
          target: [
            l.target.y + layout.offsetX,
            l.target.x + layout.offsetY,
          ],
        });
        return <path key={i} d={d} className="link" />;
      })}

      {/* draw nodes */}
      {layout.nodes.map((n, i) => {
        if (n.depth === 0) return null; // hide synthetic root
        const d = n.data;
        const x = n.y + layout.offsetX;
        const y = n.x + layout.offsetY - NODE_H / 2;

        const fill = d.isTemplate
          ? "#f3f4f6"
          : getDomainColor(d.domain);
        const textFill = d.isTemplate ? "#374151" : "#fff";

        return (
          <g
            key={i}
            transform={`translate(${x},${y})`}
            className="node"
            onClick={(e) => onNodeClick(d, e)}
          >
            <title>{d.name}</title>
            <rect
              width={NODE_W}
              height={NODE_H}
              rx={8}
              style={{ fill }}
            />
            <text
              x={NODE_W / 2}
              y={NODE_H / 2}
              alignmentBaseline="central"
              textAnchor="middle"
              style={{ fill: textFill, fontSize: 12 }}
            >
              {String(d.name).length > 28
                ? String(d.name).slice(0, 25) + "…"
                : d.name}
            </text>

            {/* show how many templates under a group */}
            {d.templates &&
              d.templates.length > 0 &&
              !d.isTemplate && (
                <text
                  x={NODE_W - 6}
                  y={11}
                  textAnchor="end"
                  fontSize="10"
                  style={{ fill: textFill }}
                >
                  {d.templates.length}
                </text>
              )}
          </g>
        );
      })}
    </svg>
  );
}

// Inline styles so this works even in isolation
const STYLES = `
:root {
  --bg:#f1f5f9;
  --txt:#0f172a;
  --card:#ffffff;
  --border:#e2e8f0;
  --blue:#3b82f6;
  --shadow:0 1px 2px rgba(0,0,0,.06);
}
.ae {
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
  color: var(--txt);
  background: var(--bg);
  padding: 16px;
}
.ae .row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.ae .spacer { flex: 1; }
.ae .btn {
  border: 1px solid var(--border);
  background: #fff;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}
.ae .btn.active {
  background: var(--blue);
  border-color: var(--blue);
  color: #fff;
}
.ae .input {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 14px;
  width: 320px;
}
.ae .card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: var(--shadow);
}
.ae .p-16 { padding: 16px; }
.ae table {
  width: 100%;
  border-collapse: collapse;
}
.ae th,
.ae td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
  text-align: left;
  vertical-align: top;
}
.ae thead th {
  background: #f8fafc;
  color: #64748b;
  font-weight: 600;
}
.ae tr:hover {
  background: #f8fafc;
}
.ae .link {
  stroke: #cbd5e1;
  fill: none;
}
.ae .node rect {
  stroke: #94a3b8;
}
.ae .node text {
  font-size: 12px;
}
.ae .overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.3);
}
.ae .drawer {
  position: fixed;
  top: 0;
  right: 0;
  width: 380px;
  max-width: 100%;
  height: 100%;
  background: #fff;
  border-left: 1px solid var(--border);
  box-shadow: -8px 0 16px rgba(0,0,0,.08);
  padding: 20px;
  overflow: auto;
}
.ae .drawer h2 {
  margin: 0;
  font-size: 18px;
  color: #0f172a;
}
.ae .close {
  background: none;
  border: none;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  color: #334155;
}
.ae .muted {
  color: #64748b;
  font-size: 12px;
}
`;

/**
 * Main AnomalyExplorer component.
 * - "List" tab: table of timestamps + "View ›"
 * - "Graph" tab: hierarchical view
 * - Drawer: details with Top Contributions chart
 */
export default function AnomalyExplorer({
  rows: initialRows = [],
  treeData: initialTree = {},
}) {
  // "list" | "graph"
  const [view, setView] = useState("list");

  // live data (fallback to initial props)
  const [rows, setRows] = useState(initialRows);
  const [treeData, setTreeData] = useState(initialTree);

  // filter text for list
  const [query, setQuery] = useState("");

  // row currently open in drawer
  const [selected, setSelected] = useState(null);

  // expansion state for graph nodes
  const [expanded, setExpanded] = useState({});

  // fetch live data once
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [listResp, treeResp] = await Promise.all([
          getAnomalyList(),
          getDynamicTree(),
        ]);

        const listRaw =
          listResp?.data?.anomaly_list ?? listResp?.data ?? listResp;
        const dyn = treeResp?.data ?? treeResp;

        const mapped = Array.isArray(listRaw) ? listRaw.map(mapApiRow) : [];
        if (alive && mapped.length) setRows(mapped);
        if (alive && dyn && typeof dyn === "object") setTreeData(dyn);
      } catch (e) {
        console.error("Error fetching anomalies/dynamic tree:", e);
        // keep fallbacks
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  // Build base tree once per treeData change
  const baseTree = useMemo(
    () => convertJsonToTree(treeData),
    [treeData]
  );

  // Create a version that explodes template sentences into clickable leaves
  const expandedTree = useMemo(
    () => buildExpandedTree(baseTree, expanded),
    [baseTree, expanded]
  );

  // Filtered rows for List tab
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) =>
      [r.device, r.ts, r.classification, r.template]
        .join(" ")
        .toLowerCase()
        .includes(q)
    );
  }, [rows, query]);

  /**
   * Handle clicks in the Graph:
   * - If it's a gray template leaf -> open drawer
   * - If it's a group with templates -> toggle expand/collapse
   * - Shift+Click any node -> filter the List tab and switch to List
   */
  const onGraphNodeClick = (node, evt) => {
    // Clicking a template sentence (gray leaf)
    if (node?.isTemplate) {
      const { row } = findBestRowForTemplate(
        rows,
        node.domain,
        node.name
      );

      if (row) {
        setSelected(row);
      } else {
        // Fallback if no direct match
        setSelected({
          ts: "N/A",
          classification: node.domain,
          template: node.name,
          contributions: {},
        });
      }
      return;
    }

    // Clicking a group node that has templates -> toggle expansion
    if (node.templates && node.templates.length > 0) {
      setExpanded((prev) => ({
        ...prev,
        [node.name]: !prev[node.name],
      }));
    }

    // Shift+Click any node -> filter List
    if (evt?.shiftKey) {
      setQuery(node.name);
      setView("list");
    }
  };

  // Tab button component
  const Btn = ({ mode, label }) => (
    <button
      className={"btn " + (view === mode ? "active" : "")}
      onClick={() => setView(mode)}
    >
      {label}
    </button>
  );

  return (
    <>
      {/* inline styles so this works anywhere */}
      <style>{STYLES}</style>

      <div className="ae">
        {/* top bar: tab buttons + search (only in List view) */}
        <div className="row">
          <Btn mode="list" label="List" />
          <Btn mode="graph" label="Graph" />

          {view === "list" && <span className="spacer" />}

          {view === "list" && (
            <input
              className="input"
              placeholder="Search…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          )}
        </div>

        {/* LIST VIEW */}
        {view === "list" && (
          <div
            className="card p-16"
            style={{ 
              marginTop: 12,
              maxHeight: "600px",
              overflowY: "auto",
              overflowX: "auto"
            }}
          >
            <table style={{ position: "relative" }}>
              <thead style={{ position: "sticky", top: 0, backgroundColor: "#f8fafc", zIndex: 10 }}>
                <tr>
                  <th>Timestamp</th>
                  <th>Classification</th>
                  <th style={{ textAlign: "right" }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row, i) => (
                  <tr key={i}>
                    <td>{row.ts}</td>
                    <td>
                      {displayClassification(
                        row.classification
                      )}
                    </td>
                    <td
                      style={{ textAlign: "right" }}
                    >
                      <button
                        className="btn"
                        onClick={() => setSelected(row)}
                      >
                        View ›
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* GRAPH VIEW */}
        {view === "graph" && (
          <div
            className="card p-16"
            style={{
              marginTop: 12,
              overflow: "auto",
            }}
          >
            <GraphTree
              root={expandedTree}
              onNodeClick={onGraphNodeClick}
            />

            <div
              className="muted"
              style={{ marginTop: 8 }}
            >
              Click a template node to open details.
              Shift+Click any node to filter the list.
            </div>
          </div>
        )}

        {/* DETAILS DRAWER */}
        {selected && (
          <>
            {/* overlay behind drawer */}
            <div
              className="overlay"
              onClick={() => setSelected(null)}
            />

            {/* slide-in drawer */}
            <div className="drawer">
              <div
                className="row"
                style={{
                  justifyContent: "space-between",
                }}
              >
                <h2>
                  {displayClassification(
                    selected.classification
                  )}
                </h2>

                <button
                  className="close"
                  onClick={() => setSelected(null)}
                >
                  ×
                </button>
              </div>

              <div
                className="muted"
                style={{
                  margin: "6px 0 12px",
                }}
              >
                {selected.ts}
              </div>

              {/* Template sentence */}
              <div
                style={{ marginBottom: 12 }}
              >
                <div
                  style={{
                    fontWeight: 600,
                    marginBottom: 4,
                  }}
                >
                  Template
                </div>
                <div>{selected.template}</div>
              </div>

              {/* Top Contributions chart */}
              <div
                style={{ marginBottom: 12 }}
              >
                <div
                  style={{
                    fontWeight: 600,
                    marginBottom: 4,
                  }}
                >
                  Top Contributions
                </div>

                <div
                  style={{
                    width: "100%",
                    height: 180,
                  }}
                >
                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <BarChart
                      data={getTop(
                        selected.contributions,
                        5
                      )}
                      layout="vertical"
                      margin={{
                        left: 20,
                        right: 10,
                        top: 10,
                        bottom: 10,
                      }}
                    >
                      <XAxis
                        type="number"
                        hide
                        domain={[0, "dataMax"]}
                      />
                      <YAxis
                        dataKey="name"
                        type="category"
                        width={160}
                      />
                      <Tooltip
                        formatter={(v) =>
                          Number(v).toFixed(3)
                        }
                      />
                      <Bar
                        dataKey="value"
                        barSize={14}
                        fill={
                          getDomainColor(
                            selected.classification?.split(
                              " - "
                            )[0] || ""
                          )
                        }
                      >
                        {getTop(
                          selected.contributions,
                          5
                        ).map((_, i) => {
                          const domainColor = getDomainColor(
                            selected.classification?.split(
                              " - "
                            )[0] || ""
                          );
                          return (
                            <Cell
                              key={i}
                              fill={domainColor}
                            />
                          );
                        })}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* All contributions list */}
              <div>
                <div
                  style={{
                    fontWeight: 600,
                    marginBottom: 4,
                  }}
                >
                  All Contributions
                </div>

                <ul
                  style={{
                    listStyle: "none",
                    padding: 0,
                    margin: 0,
                  }}
                >
                  {Object.entries(
                    selected.contributions || {}
                  )
                    .sort(
                      (a, b) => b[1] - a[1]
                    )
                    .map(([k, v]) => (
                      <li
                        key={k}
                        style={{
                          display: "flex",
                          justifyContent:
                            "space-between",
                          fontSize: 14,
                          padding: "2px 0",
                        }}
                      >
                        <span
                          title={k}
                          style={{
                            maxWidth: "50%",
                            overflow: "hidden",
                            textOverflow:
                              "ellipsis",
                            whiteSpace:
                              "nowrap",
                          }}
                        >
                          {k}
                        </span>
                        <span className="muted">
                          {Number(v).toFixed(3)}
                        </span>
                      </li>
                    ))}
                </ul>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
