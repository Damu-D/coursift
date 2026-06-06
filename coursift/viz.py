"""
HTML visualization — generates an interactive D3.js graph you can open in any browser.
"""

import json

VIZ_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Coursift — Knowledge Graph</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d0d0d; color: #e8e8e8; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; overflow: hidden; }
  #canvas { width: 100vw; height: 100vh; }
  #sidebar { position: fixed; top: 0; right: 0; width: 320px; height: 100vh; background: rgba(18,18,18,0.95); border-left: 1px solid #2a2a2a; padding: 20px; overflow-y: auto; transform: translateX(100%); transition: transform .25s ease; }
  #sidebar.open { transform: translateX(0); }
  #sidebar h2 { font-size: 14px; font-weight: 600; color: #a78bfa; margin-bottom: 12px; text-transform: uppercase; letter-spacing: .05em; }
  #sidebar p { font-size: 13px; color: #9ca3af; line-height: 1.6; margin-bottom: 8px; }
  #sidebar .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; margin: 2px; }
  .badge-file { background: #1e3a5f; color: #60a5fa; }
  .badge-function { background: #1a3326; color: #34d399; }
  .badge-class { background: #2d1b4e; color: #c084fc; }
  .badge-import { background: #2d2a1e; color: #fbbf24; }
  .badge-session { background: #1e2d3d; color: #38bdf8; }
  .badge-concept { background: #2d1e1e; color: #f87171; }
  #toolbar { position: fixed; top: 16px; left: 16px; display: flex; gap: 8px; align-items: center; z-index: 10; }
  #search { background: rgba(30,30,30,0.9); border: 1px solid #333; color: #e8e8e8; padding: 8px 14px; border-radius: 8px; font-size: 13px; width: 220px; outline: none; }
  #search:focus { border-color: #a78bfa; }
  #stats { position: fixed; bottom: 16px; left: 16px; font-size: 12px; color: #555; }
  .close-btn { position: absolute; top: 12px; right: 12px; background: none; border: none; color: #555; cursor: pointer; font-size: 18px; }
  .close-btn:hover { color: #e8e8e8; }
  #legend { position: fixed; bottom: 16px; right: 16px; background: rgba(18,18,18,0.9); border: 1px solid #2a2a2a; border-radius: 8px; padding: 12px; font-size: 12px; }
  #legend div { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
  #legend span { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
  .cross-badge { font-size: 10px; color: #f59e0b; background: #2d2000; padding: 1px 6px; border-radius: 8px; margin-left: 4px; }
</style>
</head>
<body>
<div id="toolbar">
  <input id="search" type="text" placeholder="Search nodes..." />
</div>
<svg id="canvas"></svg>
<div id="sidebar">
  <button class="close-btn" onclick="closeSidebar()">✕</button>
  <h2 id="sb-kind">Node</h2>
  <div id="sb-content"></div>
</div>
<div id="stats"></div>
<div id="legend">
  <div><span style="background:#60a5fa"></span> File</div>
  <div><span style="background:#34d399"></span> Function</div>
  <div><span style="background:#c084fc"></span> Class</div>
  <div><span style="background:#fbbf24"></span> Import</div>
  <div><span style="background:#38bdf8"></span> Session</div>
  <div><span style="background:#f87171"></span> Concept</div>
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const GRAPH = __GRAPH_DATA__;

const COLOR = {
  file: "#60a5fa", function: "#34d399", class: "#c084fc",
  import: "#fbbf24", session: "#38bdf8", concept: "#f87171",
};

const svg = d3.select("#canvas");
const w = window.innerWidth, h = window.innerHeight;
svg.attr("viewBox", [0, 0, w, h]);

const g = svg.append("g");

svg.call(d3.zoom().scaleExtent([0.1, 6]).on("zoom", e => g.attr("transform", e.transform)));

const idMap = {};
GRAPH.nodes.forEach(n => idMap[n.id] = n);

const links = GRAPH.edges
  .filter(e => idMap[e.source] && idMap[e.target])
  .map(e => ({ ...e, source: e.source, target: e.target }));

const nodes = GRAPH.nodes;

document.getElementById("stats").textContent =
  `${nodes.length} nodes · ${links.length} edges · ${GRAPH.stats?.projects?.join(", ") || ""}`;

const sim = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(d => d.relation === "shared_dependency" ? 200 : 60).strength(0.4))
  .force("charge", d3.forceManyBody().strength(-120))
  .force("center", d3.forceCenter(w / 2, h / 2))
  .force("collision", d3.forceCollide(18));

const link = g.append("g").selectAll("line").data(links).join("line")
  .attr("stroke", d => d.relation === "shared_dependency" ? "#f59e0b" : "#2a2a2a")
  .attr("stroke-width", d => d.relation === "shared_dependency" ? 2 : 0.8)
  .attr("stroke-dasharray", d => d.relation === "shared_dependency" ? "4 2" : null)
  .attr("opacity", 0.7);

const node = g.append("g").selectAll("circle").data(nodes).join("circle")
  .attr("r", d => d.god_node ? 14 : d.kind === "file" ? 8 : d.kind === "session" ? 10 : 6)
  .attr("fill", d => COLOR[d.kind] || "#888")
  .attr("stroke", d => d.god_node ? "#fff" : d.cross_project ? "#f59e0b" : "transparent")
  .attr("stroke-width", d => d.god_node ? 2 : 1.5)
  .attr("cursor", "pointer")
  .call(d3.drag()
    .on("start", (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
    .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
    .on("end", (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
  )
  .on("click", (e, d) => { e.stopPropagation(); openSidebar(d); });

const label = g.append("g").selectAll("text").data(nodes.filter(n => n.god_node || n.kind === "session")).join("text")
  .text(d => d.label)
  .attr("font-size", 10)
  .attr("fill", "#ccc")
  .attr("dx", 14)
  .attr("dy", 4)
  .attr("pointer-events", "none");

sim.on("tick", () => {
  link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("cx", d => d.x).attr("cy", d => d.y);
  label.attr("x", d => d.x).attr("y", d => d.y);
});

function openSidebar(d) {
  document.getElementById("sb-kind").textContent = d.kind.toUpperCase();
  let html = `<span class="badge badge-${d.kind}">${d.kind}</span>`;
  if (d.god_node) html += `<span class="badge" style="background:#1a1a1a;color:#fff">⭐ god node</span>`;
  if (d.cross_project) html += `<span class="cross-badge">⬡ cross-project</span>`;
  html += `<p style="margin-top:12px;font-size:15px;font-weight:600;color:#e8e8e8">${d.label}</p>`;
  if (d.project) html += `<p>Project: <strong>${d.project}</strong></p>`;
  if (d.file) html += `<p style="word-break:break-all;font-size:11px;color:#666">${d.file}${d.line ? ":" + d.line : ""}</p>`;
  if (d.docstring) html += `<p style="margin-top:8px;font-style:italic;color:#9ca3af">"${d.docstring}"</p>`;
  if (d.shared_by) html += `<p>Shared by: ${d.shared_by.join(", ")}</p>`;
  if (d.decisions?.length) {
    html += `<h2 style="margin-top:12px">Decisions</h2>`;
    d.decisions.forEach(dec => html += `<p>• ${dec}</p>`);
  }
  if (d.concepts?.length) {
    html += `<h2 style="margin-top:12px">Concepts</h2>`;
    d.concepts.forEach(c => html += `<span class="badge badge-concept">${c}</span>`);
  }
  document.getElementById("sb-content").innerHTML = html;
  document.getElementById("sidebar").classList.add("open");
}

function closeSidebar() {
  document.getElementById("sidebar").classList.remove("open");
}

svg.on("click", closeSidebar);

document.getElementById("search").addEventListener("input", function () {
  const q = this.value.toLowerCase();
  node.attr("opacity", d => !q || d.label.toLowerCase().includes(q) || d.project?.toLowerCase().includes(q) ? 1 : 0.1);
  link.attr("opacity", !q ? 0.7 : 0.05);
});
</script>
</body>
</html>
"""


def generate_html(graph: dict, output_path) -> None:
    graph_json = json.dumps(graph)
    html = VIZ_TEMPLATE.replace("__GRAPH_DATA__", graph_json)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
