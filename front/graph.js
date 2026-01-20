const API_BASE = "http://127.0.0.1:8000";
async function fetchWithTimeout(url, ms = 12000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);

  try {
    const resp = await fetch(url, { signal: controller.signal });
    return resp;
  } finally {
    clearTimeout(timer);
  }
}




// palette simple (communities)
function colorForCommunity(c) {
  const colors = ["#0d6efd", "#198754", "#dc3545", "#fd7e14", "#6f42c1", "#20c997", "#0dcaf0", "#6c757d"];
  return colors[Math.abs(c) % colors.length];
}

function setStatus(msg) {
  const el = document.getElementById("graphStatus");
  if (el) el.textContent = msg || "";
}

function escapeHtml(s) {
  return String(s || "").replace(/[&<>"']/g, (m) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[m]));
}


function setStatus(msg) {
  const el = document.getElementById("graphStatus");
  if (el) el.textContent = msg || "";
}

function buildCytoscapeElements(payload) {
  const nodes = (payload?.nodes || []).map(n => ({
    data: { id: n.id, label: n.label || n.id }
  }));

  const edges = (payload?.edges || []).map((e, idx) => ({
    data: {
      id: `e${idx}`,
      source: e.source,
      target: e.target,
      label: e.label || ""
    }
  }));

  return [...nodes, ...edges];
}

function renderGraph(elements) {
  if (!cy) {
    cy = cytoscape({
      container: document.getElementById("cy"),
      elements,
      style: [
        {
          selector: "node",
          style: {
            "label": "data(label)",
            "font-size": 10,
            "text-wrap": "wrap",
            "text-max-width": 120,
            "text-valign": "center",
            "text-halign": "center",
            "background-color": "#0d6efd",
            "color": "#111",
            "width": 28,
            "height": 28
          }
        },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "line-color": "#bbb",
            "target-arrow-color": "#bbb",
            "width": 1,
            "label": "data(label)",
            "font-size": 8,
            "text-rotation": "autorotate",
            "text-margin-y": -6,
            "color": "#666"
          }
        },
        {
          selector: "node:selected",
          style: {
            "background-color": "#198754",
            "width": 34,
            "height": 34
          }
        }
      ]
    });

    // Interaction : clic -> recadrer
    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      cy.animate({ center: { eles: node }, zoom: 1.2 }, { duration: 250 });
    });

    // Double clic -> recharger en seed sur ce noeud
    let lastTap = 0;
    cy.on("tap", "node", (evt) => {
      const now = Date.now();
      if (now - lastTap < 300) {
        const node = evt.target;
        document.getElementById("seedInput").value = node.id();
        loadGraph();
      }
      lastTap = now;
    });
  } else {
    cy.elements().remove();
    cy.add(elements);
  }

  cy.layout({ name: "cose", animate: true, animationDuration: 400 }).run();
  cy.fit(undefined, 30);
}

let cy = null;

async function loadGraph() {
  const seed = (document.getElementById("seedInput")?.value || "").trim();
  const depth = document.getElementById("depthSelect")?.value || "1";

  if (!seed.startsWith("http")) {
    setStatus("Seed invalide : colle une URI DBpedia http(s).");
    return;
  }

  setStatus("Chargement… (DBpedia peut être lente)");
  const graphUrl = `${API_BASE}/graph?seed=${encodeURIComponent(seed)}&depth=${encodeURIComponent(depth)}&limit=80&mode=foot`;
  const metricsUrl = `${API_BASE}/graph/metrics?seed=${encodeURIComponent(seed)}&depth=${encodeURIComponent(depth)}&limit=80`;

  try {
    const [gResp, mResp] = await Promise.all([fetch(graphUrl), fetch(metricsUrl)]);

    if (!gResp.ok) {
      setStatus(`Erreur graphe: HTTP ${gResp.status}`);
      return;
    }
    if (!mResp.ok) {
      setStatus(`Erreur metrics: HTTP ${mResp.status} (le graphe peut quand même s’afficher)`);
    }

    const graphData = await gResp.json();
    const metricsData = mResp.ok ? await mResp.json() : null;

    renderInsights(metricsData);
    renderGraph(graphData, metricsData);

    const nNodes = graphData?.nodes?.length || 0;
    const nEdges = graphData?.edges?.length || 0;
    setStatus(`OK — ${nNodes} noeuds, ${nEdges} liens (depth=${depth})`);
    lastGraphData = graphData;
    lastMetricsData = metricsData; 

  } catch (e) {
    console.error(e);
    setStatus("Erreur réseau (backend joignable ?)");
  }
}


document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("loadGraphBtn")?.addEventListener("click", loadGraph);
  document.getElementById("seedInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") loadGraph();
  });
  

  // auto-load au démarrage
  loadGraph();
  document.getElementById("explainBtn")?.addEventListener("click", explainCurrentGraph);

});
function renderInsights(metrics) {
  const row = document.getElementById("insightsRow");
  if (!row) return;

  if (!metrics) {
    row.style.display = "none";
    return;
  }
  row.style.display = "";

  const renderList = (arr) => {
    if (!arr?.length) return `<div class="text-muted">Aucune donnée</div>`;
    return `
      <ol class="mb-0 ps-3">
        ${arr.slice(0, 6).map(x => `
          <li class="mb-1">
            <span class="fw-semibold">${escapeHtml(x.label)}</span>
            <span class="text-muted">(${Number(x.score).toFixed(4)})</span>
          </li>
        `).join("")}
      </ol>
    `;
  };

  document.getElementById("insight-degree").innerHTML = renderList(metrics.top_degree);
  document.getElementById("insight-pagerank").innerHTML = renderList(metrics.top_pagerank);
  document.getElementById("insight-betweenness").innerHTML = renderList(metrics.top_betweenness);
}
function buildCytoscapeElements(graphData, metricsData) {
  const comm = metricsData?.communities || {};
  const pr = metricsData?.pagerank || {};

  const nodes = (graphData?.nodes || []).map(n => ({
    data: {
      id: n.id,
      label: n.label || n.id,
      community: comm[n.id] ?? -1,
      rank: pr[n.id] ?? 0
    }
  }));

  const edges = (graphData?.edges || []).map((e, idx) => ({
    data: {
      id: `e${idx}`,
      source: e.source,
      target: e.target,
      label: e.label || ""
    }
  }));

  return [...nodes, ...edges];
}

function renderGraph(graphData, metricsData) {
  const elements = buildCytoscapeElements(graphData, metricsData);

  const ranks = elements.filter(x => x.data && x.data.rank !== undefined).map(x => x.data.rank);
  const rMin = ranks.length ? Math.min(...ranks) : 0;
  const rMax = ranks.length ? Math.max(...ranks) : 1;

  if (!cy) {
    cy = cytoscape({
      container: document.getElementById("cy"),
      elements,
      style: [
        {
          selector: "node",
          style: {
            "label": "data(label)",
            "font-size": 10,
            "text-wrap": "wrap",
            "text-max-width": 120,
            "text-valign": "center",
            "text-halign": "center",

            // Couleur par communauté
            "background-color": (ele) => colorForCommunity(ele.data("community")),

            // Taille par PageRank
            "width": (ele) => {
              const v = ele.data("rank") || 0;
              if (rMax <= rMin) return 30;
              const t = (v - rMin) / (rMax - rMin);
              return 24 + t * 40; // 24..64
            },
            "height": (ele) => {
              const v = ele.data("rank") || 0;
              if (rMax <= rMin) return 30;
              const t = (v - rMin) / (rMax - rMin);
              return 24 + t * 40;
            },
            "color": "#111",
          }
        },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "line-color": "#bbb",
            "target-arrow-color": "#bbb",
            "width": 1
            // IMPORTANT: pas de label sur edge (sinon illisible)
          }
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 3,
            "border-color": "#111"
          }
        }
      ]
    });

    // click -> focus
    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      cy.animate({ center: { eles: node }, zoom: 1.2 }, { duration: 200 });
    });

    // double-click -> re-seed
    let lastTap = 0;
    cy.on("tap", "node", (evt) => {
      const now = Date.now();
      if (now - lastTap < 300) {
        const node = evt.target;
        document.getElementById("seedInput").value = node.id();
        loadGraph();
      }
      lastTap = now;
    });
  } else {
    cy.elements().remove();
    cy.add(elements);
  }

  cy.layout({ name: "cose", animate: true, animationDuration: 400 }).run();
  cy.fit(undefined, 30);
}
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("loadGraphBtn")?.addEventListener("click", loadGraph);
  document.getElementById("seedInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") loadGraph();
  });
  loadGraph();
});
let lastGraphData = null;
let lastMetricsData = null;

async function explainCurrentGraph() {
  const card = document.getElementById("explainCard");
  if (!card) return;

  // nouveaux IDs (graph.html propre)
  const titleEl = document.getElementById("explainTitle");
  const summaryEl = document.getElementById("explainSummary");
  const providerEl = document.getElementById("explainProvider");
  const insightsEl = document.getElementById("explainInsights");
  const limitsEl = document.getElementById("explainLimits");
  const stepsEl = document.getElementById("explainNextSteps");

  if (!titleEl || !summaryEl || !providerEl || !insightsEl || !limitsEl || !stepsEl) return;

  // helper loader UI
  const setLoading = (providerText = "ollama") => {
    card.style.display = "";
    providerEl.textContent = providerText;
    titleEl.textContent = "Analyse en cours…";
    summaryEl.textContent = "Le modèle génère une interprétation structurée.";
    insightsEl.innerHTML = `<li class="text-muted">Chargement…</li>`;
    limitsEl.innerHTML = `<li class="text-muted">Chargement…</li>`;
    stepsEl.innerHTML = `<span class="badge text-bg-light border">…</span>`;
  };

  // Si pas de graphe/metrics
  if (!lastMetricsData || !lastGraphData) {
    card.style.display = "";
    providerEl.textContent = "";
    titleEl.textContent = "Interprétation";
    summaryEl.textContent = "Charge un graphe d’abord 🙂";
    insightsEl.innerHTML = "";
    limitsEl.innerHTML = "";
    stepsEl.innerHTML = "";
    return;
  }

  setLoading("ollama");

  const payload = {
    seed_uri: lastMetricsData.seed_uri || "",
    metrics: lastMetricsData,
    lang: "fr"
  };

  try {
    const resp = await fetch(`${API_BASE}/graph/explain`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      card.style.display = "";
      providerEl.textContent = "";
      titleEl.textContent = "Erreur";
      summaryEl.textContent = `Erreur explication (HTTP ${resp.status}).`;
      insightsEl.innerHTML = "";
      limitsEl.innerHTML = "";
      stepsEl.innerHTML = "";
      return;
    }

    const data = await resp.json();

    // 1) ✅ Cas idéal : backend renvoie { provider, data: {...} }
    if (data && data.data && typeof data.data === "object") {
      providerEl.textContent = data.provider || "ollama";
      renderExplain(data.data);
      return;
    }

    // 2) ✅ Cas courant : backend renvoie { provider, explanation: "{...json...}" }
    if (data && typeof data.explanation === "string") {
      providerEl.textContent = data.provider || "ollama";

      // Nettoyer ```json ... ``` si jamais
      const cleaned = data.explanation
        .replace(/```json/gi, "")
        .replace(/```/g, "")
        .trim();

      try {
        const obj = JSON.parse(cleaned);
        renderExplain(obj);
        return;
      } catch (e) {
        // si ce n'est pas du JSON, on retombe sur l'affichage texte
        console.warn("explanation is not JSON:", e);
      }

      // fallback texte (au cas où)
      titleEl.textContent = "Interprétation";
      summaryEl.textContent = cleaned.slice(0, 180);
      insightsEl.innerHTML = "";
      limitsEl.innerHTML = "";
      stepsEl.innerHTML = "";
      return;
    }

    // 3) ❌ Rien d'exploitable
    providerEl.textContent = data?.provider || "ollama";
    titleEl.textContent = "Interprétation";
    summaryEl.textContent = "Réponse inattendue du backend.";
    insightsEl.innerHTML = "";
    limitsEl.innerHTML = "";
    stepsEl.innerHTML = "";
  } catch (e) {
    console.error("Erreur lors de l'explication:", e);
    card.style.display = "";
    providerEl.textContent = "";
    titleEl.textContent = "Erreur";
    summaryEl.textContent = "Erreur lors de la récupération de l'explication.";
    insightsEl.innerHTML = "";
    limitsEl.innerHTML = "";
    stepsEl.innerHTML = "";
  }
}
function renderExplain(data) {
  const card = document.getElementById("explainCard");
  if (!card) return;
  card.style.display = "";

  document.getElementById("explainTitle").textContent = data.title || "Interprétation";
  document.getElementById("explainSummary").textContent = data.summary || "";
  
  const insightsEl = document.getElementById("explainInsights");
  insightsEl.innerHTML = (data.insights || []).slice(0,3)
    .map(x => `<li>${escapeHtml(x)}</li>`).join("");

  const limitsEl = document.getElementById("explainLimits");
  limitsEl.innerHTML = (data.limits || []).slice(0,2)
    .map(x => `<li>${escapeHtml(x)}</li>`).join("");

  const stepsEl = document.getElementById("explainNextSteps");
  stepsEl.innerHTML = (data.next_steps || []).slice(0,2)
    .map(x => `<span class="badge text-bg-light border">${escapeHtml(x)}</span>`).join("");
}
