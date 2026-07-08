/**
 * script.js — Talking Rabbitt BI Dashboard
 * Connects analytics.html to the FastAPI backend.
 */

// ─────────────────────────────────────────────────────────────────────────────
// 1. BACKEND URL
// ─────────────────────────────────────────────────────────────────────────────

const BACKEND_URL = "http://localhost:8000";

// ─────────────────────────────────────────────────────────────────────────────
// 2. INJECT UPLOAD BUTTON — runs inside DOMContentLoaded only
// ─────────────────────────────────────────────────────────────────────────────

function injectUploadUI() {
  // Guard: don't inject twice
  if (document.getElementById("upload-btn")) return;

  // Hidden file input
  const fileInput = document.createElement("input");
  fileInput.type    = "file";
  fileInput.id      = "file-input";
  fileInput.accept  = ".csv,.xlsx,.xls";
  fileInput.style.display = "none";
  document.body.appendChild(fileInput);

  // Visible button
  const uploadBtn = document.createElement("button");
  uploadBtn.id        = "upload-btn";
  uploadBtn.textContent = "Upload Data";
  uploadBtn.style.cssText =
    "padding:6px 12px; font-size:13px; font-weight:600; " +
    "background:#a855f7; color:#fff; border:none; border-radius:8px; " +
    "cursor:pointer; transition:background 0.2s;";
  uploadBtn.onmouseenter = () => (uploadBtn.style.background = "#9333ea");
  uploadBtn.onmouseleave = () => (uploadBtn.style.background = "#a855f7");

  // The header has two divs matching ".flex.items-center.gap-3"
  // — the logo div (first) and the nav-buttons div (second).
  // We want the SECOND one (contains Dashboard, Insights, select, refresh-btn).
  // We find it reliably by looking for the element that contains refresh-btn.
  const refreshBtn = document.getElementById("refresh-btn");
  const targetDiv  = refreshBtn ? refreshBtn.parentElement : null;

  if (targetDiv) {
    // Insert Upload button BEFORE the refresh button
    targetDiv.insertBefore(uploadBtn, refreshBtn);
  } else {
    // Fallback: append to header
    const header = document.querySelector("header");
    if (header) header.appendChild(uploadBtn);
  }

  // Wire: button → open file picker
  uploadBtn.addEventListener("click", () => fileInput.click());

  // Wire: file chosen → upload
  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) handleFileUpload(file);
    fileInput.value = ""; // reset so same file can be re-selected
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. UPLOAD HANDLER — POST /upload
// ─────────────────────────────────────────────────────────────────────────────

async function handleFileUpload(file) {
  const uploadBtn = document.getElementById("upload-btn");
  uploadBtn.textContent = "Uploading…";
  uploadBtn.disabled    = true;

  try {
    const formData = new FormData();
    formData.append("file", file); // must match FastAPI param name

    const response = await fetch(`${BACKEND_URL}/upload`, {
      method: "POST",
      body:   formData,
    });

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try { detail = (await response.json()).detail ?? detail; } catch (_) {}
      throw new Error(detail);
    }

    const data = await response.json();

    if (!data.success) throw new Error("Backend returned success: false");

    // Store session globally
    window.SESSION_ID = data.session_id;

    // Update header
    document.getElementById("current-filename").textContent = file.name;
    document.getElementById("last-updated").textContent =
      "Last updated: " + new Date().toLocaleTimeString([], {
        hour: "2-digit", minute: "2-digit",
      });

    // Fill KPI cards
    updateDashboardFromProfile(data.profile);

    // Welcome message in chat
    const p = data.profile;
    appendChatBubble(
      "ai",
      `✅ <strong>${escapeHtml(file.name)}</strong> uploaded! ` +
      `<strong>${p.row_count} rows</strong> × ` +
      `<strong>${p.column_count} columns</strong> ` +
      `(${p.numeric_columns.length} numeric, ` +
      `${p.categorical_columns.length} categorical). ` +
      `Ask me anything about your data.`
    );

    uploadBtn.textContent = "Re-upload";

  } catch (error) {
    console.error("[upload]", error);
    appendChatBubble("ai",
      `❌ Upload failed: ${escapeHtml(error.message)}`
    );
    uploadBtn.textContent = "Upload Data";
  } finally {
    uploadBtn.disabled = false;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. UPDATE KPI CARDS FROM PROFILE
// ─────────────────────────────────────────────────────────────────────────────

// Profile shape from services/cleaning.py:
//   row_count, column_count, numeric_columns[], categorical_columns[],
//   stats{ col: { count, mean, sum, min, max, std } },
//   missing_values{ col: count }, date_column, duplicate_rows_removed

function updateDashboardFromProfile(profile) {
  if (!profile) return;

  const {
    numeric_columns   = [],
    categorical_columns = [],
    stats             = {},
    row_count         = 0,
    column_count      = 0,
    missing_values    = {},
    date_column       = null,
    duplicate_rows_removed = 0,
  } = profile;

  // ── Revenue card ────────────────────────────────────────────────────
  const revenueCol = findColByKeywords(numeric_columns,
    ["revenue","sales","amount","total","income","price","value","gmv"]);

  if (revenueCol && stats[revenueCol]?.sum != null) {
    updateKPI("kpi-rev-val", "kpi-rev-change", {
      val:      formatMoney(stats[revenueCol].sum),
      change:   `${row_count} rows`,
      positive: true,
    });
  } else {
    updateKPI("kpi-rev-val", "kpi-rev-change", {
      val:      row_count.toLocaleString(),
      change:   "Total Rows",
      positive: true,
    });
  }

  // ── Growth Rate card ─────────────────────────────────────────────────
  updateKPI("kpi-growth-val", "kpi-growth-change", {
    val:      `${column_count} cols`,
    change:   `${numeric_columns.length} numeric`,
    positive: true,
  });

  // ── Top Category card ────────────────────────────────────────────────
  const catCol = categorical_columns[0] ?? null;
  updateKPI("kpi-cat-val", "kpi-cat-change", {
    val:      catCol ? truncate(catCol, 16) : "--",
    change:   catCol ? "category col" : "--",
    positive: true,
  });

  // ── Top Region card ──────────────────────────────────────────────────
  const regionCol = findColByKeywords(categorical_columns,
    ["region","country","location","area","territory","market","city","state"]);
  const regionDisplay = regionCol ?? categorical_columns[1] ?? null;
  updateKPI("kpi-reg-val", "kpi-reg-change", {
    val:      regionDisplay ? truncate(regionDisplay, 16) : "--",
    change:   regionDisplay ? "region col" : "--",
    positive: true,
  });

  // ── Anomalies card ───────────────────────────────────────────────────
  const colsWithMissing = Object.values(missing_values).filter(c => c > 0).length;
  document.getElementById("kpi-anom-val").textContent = colsWithMissing;

  // ── AI Insights list ─────────────────────────────────────────────────
  renderList("ai-insights-list", [
    `Dataset: ${row_count} rows × ${column_count} columns.`,
    `Numeric columns: ${numeric_columns.join(", ") || "none"}.`,
    `Categorical columns: ${categorical_columns.join(", ") || "none"}.`,
    date_column
      ? `Date column detected: "${date_column}".`
      : "No date column detected.",
    duplicate_rows_removed > 0
      ? `${duplicate_rows_removed} duplicate rows removed during cleaning.`
      : "No duplicates found.",
  ], true);

  // ── Recommendations list ─────────────────────────────────────────────
  renderList("ai-recommendations-list", [
    "Ask the AI for trends, comparisons or forecasts.",
    'Try: "What are the top 5 categories by revenue?"',
    'Try: "Show me a chart of sales by region."',
    'Try: "Which month had the highest growth?"',
  ], false);
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. REWIRE CHAT BUTTON
// ─────────────────────────────────────────────────────────────────────────────

function rewireChat() {
  // Clone removes all listeners added by the inline script
  const oldBtn = document.getElementById("chat-send-btn");
  if (!oldBtn) return;
  const newBtn = oldBtn.cloneNode(true);
  oldBtn.parentNode.replaceChild(newBtn, oldBtn);
  newBtn.addEventListener("click", handleChatSend);

  const oldInput = document.getElementById("chat-input");
  if (!oldInput) return;
  const newInput = oldInput.cloneNode(true);
  oldInput.parentNode.replaceChild(newInput, oldInput);
  newInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleChatSend();
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// 6. CHAT HANDLER — POST /chat
// ─────────────────────────────────────────────────────────────────────────────

// Backend returns:
// { answer, recommendation, charts:[{type,title,xKey,yKey,data[]}], follow_up_questions[] }

async function handleChatSend() {
  const chatInput = document.getElementById("chat-input");
  const question  = chatInput.value.trim();
  if (!question) return;

  if (!window.SESSION_ID) {
    appendChatBubble("ai",
      "⚠️ Please upload a CSV or XLSX file first, then ask your question."
    );
    return;
  }

  chatInput.value = "";
  appendChatBubble("user", question);

  const loadingId = "loading-" + Date.now();
  appendChatBubble("ai", "Thinking…", loadingId);

  try {
    const response = await fetch(`${BACKEND_URL}/chat`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        session_id: window.SESSION_ID,
        question,
      }),
    });

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try { detail = (await response.json()).detail ?? detail; } catch (_) {}
      throw new Error(detail);
    }

    const data = await response.json();
    // data = { answer, recommendation, charts[], follow_up_questions[] }

    // Build bubble HTML
    let html = `<p>${escapeHtml(data.answer ?? "")}</p>`;

    // Recommendation box
    if (data.recommendation) {
      html += `
        <div style="margin-top:10px;padding:8px;background:rgba(168,85,247,0.1);
          border:1px solid rgba(168,85,247,0.3);border-radius:8px;font-size:12px;color:#d4d4d4;">
          <span style="color:#a855f7;font-weight:600;font-size:10px;text-transform:uppercase;
            letter-spacing:.05em;">Recommendation</span>
          <p style="margin-top:4px;">${escapeHtml(data.recommendation)}</p>
        </div>`;
    }

    // Charts — backend always sends an array
    const charts = Array.isArray(data.charts) ? data.charts : [];
    const chartRenderList = [];

    charts.forEach((chart, i) => {
      if (!chart.data || chart.data.length === 0) return;
      const canvasId = `chat-chart-${Date.now()}-${i}`;
      chartRenderList.push({ canvasId, chart });

      if (chart.title) {
        html += `<p style="margin-top:10px;margin-bottom:4px;font-size:12px;
          color:#a3a3a3;font-weight:500;">${escapeHtml(chart.title)}</p>`;
      }
      html += `
        <div style="position:relative;height:200px;width:100%;margin-top:6px;">
          <canvas id="${canvasId}"></canvas>
        </div>`;
    });

    // Write HTML first, then draw charts (canvas must exist in DOM first)
    const bubble = document.getElementById(loadingId);
    if (bubble) {
      bubble.innerHTML = html;
      chartRenderList.forEach(({ canvasId, chart }) =>
        renderChatChart(canvasId, chart)
      );
      const chatHistory = document.getElementById("chat-history");
      if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;
    }

  } catch (error) {
    console.error("[chat]", error);
    const bubble = document.getElementById(loadingId);
    if (bubble) {
      bubble.innerHTML =
        `<p style="color:#f87171;">❌ ${escapeHtml(error.message)}</p>`;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. RENDER CHART INSIDE CHAT BUBBLE
// ─────────────────────────────────────────────────────────────────────────────

function renderChatChart(canvasId, chart) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const labels = chart.data.map(item =>
    String(item[chart.xKey] ?? item.label ?? "")
  );
  const values = chart.data.map(item =>
    Number(item[chart.yKey] ?? item.value ?? 0)
  );

  const PALETTE = [
    "#a855f7","#8b5cf6","#6d28d9","#4c1d95",
    "#7c3aed","#c084fc","#e879f9","#d946ef",
  ];

  const isPie = chart.type === "pie" || chart.type === "doughnut";

  new Chart(canvas.getContext("2d"), {
    type: chart.type ?? "bar",
    data: {
      labels,
      datasets: [{
        label:           chart.yKey ?? "Value",
        data:            values,
        backgroundColor: isPie
          ? PALETTE.slice(0, labels.length)
          : "rgba(168,85,247,0.75)",
        borderColor:     chart.type === "line" ? "#a855f7" : "transparent",
        borderWidth:     chart.type === "line" ? 2 : 0,
        borderRadius:    chart.type === "bar"  ? 4 : 0,
        fill:            chart.type === "line",
        tension:         0.4,
        pointBackgroundColor: "#a855f7",
      }],
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: isPie,
          labels:  { boxWidth: 10, font: { size: 10 }, color: "#a3a3a3" },
        },
      },
      scales: isPie ? {} : {
        y: {
          beginAtZero: true,
          grid:  { color: "#262626" },
          ticks: { color: "#a3a3a3" },
        },
        x: {
          grid:  { display: false },
          ticks: { color: "#a3a3a3" },
        },
      },
    },
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. HELPERS
// ─────────────────────────────────────────────────────────────────────────────

function findColByKeywords(columns, keywords) {
  return columns.find(col =>
    keywords.some(kw => col.toLowerCase().includes(kw))
  ) ?? null;
}

function formatMoney(n) {
  if (n == null || isNaN(n)) return "--";
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000)     return `$${(n / 1_000).toFixed(1)}K`;
  return String(Math.round(n));
}

function truncate(str, maxLen) {
  return str.length > maxLen ? str.slice(0, maxLen) + "…" : str;
}

function escapeHtml(text) {
  if (typeof text !== "string") return String(text ?? "");
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ─────────────────────────────────────────────────────────────────────────────
// 9. BOOT
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  injectUploadUI();  // adds Upload button next to the refresh icon
  rewireChat();      // replaces inline chat listeners with our handler
  console.log("[script.js] Ready. Backend:", BACKEND_URL);
});
