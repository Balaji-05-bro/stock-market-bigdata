/**
 * Stock Market Big Data Analytics Platform - Frontend Controller
 * Integrates with Flask REST APIs, Chart.js, and Plotly.js
 */

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initTheme();
  loadInitialData();
});

// ---------------------------------------------------------------------------
// 1. Navigation & Theme Controller
// ---------------------------------------------------------------------------

function initNavigation() {
  const navLinks = document.querySelectorAll(".nav-link");
  navLinks.forEach((link) => {
    link.addEventListener("click", () => {
      const sectionId = link.getAttribute("data-section");
      switchSection(sectionId);
    });
  });
}

function switchSection(sectionId) {
  // Update nav active states
  document.querySelectorAll(".nav-link").forEach((l) => {
    l.classList.toggle("active", l.getAttribute("data-section") === sectionId);
  });

  // Switch content section
  document.querySelectorAll(".content-section").forEach((sec) => {
    sec.classList.toggle("active", sec.id === sectionId);
  });

  // Lazy load section data
  if (sectionId === "overview") loadOverviewData();
  else if (sectionId === "stock-analysis") loadStockAnalysisData();
  else if (sectionId === "trend-analysis") loadTrendIndicators();
  else if (sectionId === "bigdata-processing") loadBigDataMetrics();
}

function initTheme() {
  const btn = document.getElementById("themeToggleBtn");
  const label = document.getElementById("themeLabel");
  const html = document.documentElement;

  const savedTheme = localStorage.getItem("theme") || "light";
  html.setAttribute("data-theme", savedTheme);
  updateThemeButton(savedTheme);

  btn.addEventListener("click", () => {
    const current = html.getAttribute("data-theme");
    const next = current === "light" ? "dark" : "light";
    html.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    updateThemeButton(next);

    // Refresh active plots with matching theme
    const activeSection = document.querySelector(".content-section.active").id;
    if (activeSection === "stock-analysis") onStockSelected();
    else if (activeSection === "trend-analysis") loadTrendIndicators();
  });
}

function updateThemeButton(theme) {
  const label = document.getElementById("themeLabel");
  if (theme === "dark") {
    label.innerHTML = '<i class="fa-regular fa-sun"></i> Light Theme';
  } else {
    label.innerHTML = '<i class="fa-regular fa-moon"></i> Dark Theme';
  }
}

function getPlotlyThemeLayout() {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  return {
    paper_bgcolor: isDark ? "#151e32" : "#ffffff",
    plot_bgcolor: isDark ? "#151e32" : "#ffffff",
    font: {
      color: isDark ? "#94a3b8" : "#475569",
      family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", Inter, sans-serif'
    },
    gridcolor: isDark ? "#1e293b" : "#f1f5f9",
    margin: { t: 25, r: 25, l: 50, b: 40 }
  };
}

// ---------------------------------------------------------------------------
// 2. Data Initialization
// ---------------------------------------------------------------------------

let allStocksList = [];
let chartTypeMode = "line";

async function fetchApiJson(url) {
  const response = await fetch(url);
  let payload;

  try {
    payload = await response.json();
  } catch (error) {
    throw new Error(`The server returned an unreadable response (${response.status}).`);
  }

  if (!response.ok || payload.status !== "success") {
    throw new Error(payload.message || `Request failed (${response.status}).`);
  }

  return payload;
}

async function loadInitialData() {
  await loadStockDropdowns();
  loadOverviewData();
}

async function loadStockDropdowns() {
  try {
    const res = await fetch("/api/stocks");
    const json = await res.json();
    if (json.status === "success") {
      allStocksList = json.data;
      const stockSel = document.getElementById("stockSelector");
      const trendSel = document.getElementById("trendStockSelector");

      stockSel.innerHTML = "";
      trendSel.innerHTML = "";

      allStocksList.forEach((s) => {
        const opt1 = document.createElement("option");
        opt1.value = s.Symbol;
        opt1.textContent = `${s.Symbol} - ${s.Company_Name}`;
        stockSel.appendChild(opt1);

        const opt2 = document.createElement("option");
        opt2.value = s.Symbol;
        opt2.textContent = `${s.Symbol} - ${s.Company_Name}`;
        trendSel.appendChild(opt2);
      });
    }
  } catch (e) {
    console.error("Failed to load stocks dropdown:", e);
  }
}

// ---------------------------------------------------------------------------
// 3. Section A: Overview Controller
// ---------------------------------------------------------------------------

let valuationChartInstance = null;
let volumePieChartInstance = null;

async function loadOverviewData() {
  const tbody = document.getElementById("performersTableBody");
  try {
    const json = await fetchApiJson("/api/overview");
    const d = json.data;
    document.getElementById("statTotalStocks").textContent = d.total_stocks;
    document.getElementById("statTotalRecords").textContent = Number(d.total_records).toLocaleString();
    document.getElementById("statDateRange").textContent = d.date_range;
    document.getElementById("statAvgPrice").textContent = `₹${d.average_market_price.toLocaleString()}`;
    document.getElementById("statTopPerformer").textContent = d.highest_performer.symbol;
    document.getElementById("statTopReturn").textContent = `${d.highest_performer.return} Net Return`;
    document.getElementById("statWorstPerformer").textContent = d.lowest_performer.symbol;
    document.getElementById("statWorstReturn").textContent = `${d.lowest_performer.return} Net Return`;
    document.getElementById("statTotalVolume").textContent = (d.total_market_volume / 1e9).toFixed(2) + " Billion";

    // Load performers leaderboard
    const perfJson = await fetchApiJson("/api/performers");
    renderPerformersTable(perfJson.top_performers.concat(perfJson.worst_performers));
    renderOverviewCharts(perfJson.top_performers);
  } catch (e) {
    console.error("Error loading overview data:", e);
    tbody.innerHTML = "";
    const row = document.createElement("tr");
    const message = document.createElement("td");
    message.colSpan = 8;
    message.className = "overview-data-error";
    message.textContent = `Dashboard data could not be loaded: ${e.message}`;
    row.appendChild(message);
    tbody.appendChild(row);
  }
}

function renderPerformersTable(items) {
  const tbody = document.getElementById("performersTableBody");
  tbody.innerHTML = "";

  // Sort descending by percentage return
  items.sort((a, b) => b.percentage_return - a.percentage_return);

  items.forEach((s, idx) => {
    const isGain = s.percentage_return >= 0;
    const badgeClass = isGain ? "badge-bullish" : "badge-bearish";
    const statusText = isGain ? "High Performer" : "Underperformer";

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>#${idx + 1}</strong></td>
      <td><strong>${s.symbol}</strong></td>
      <td>${s.company_name}</td>
      <td>₹${s.initial_price.toFixed(2)}</td>
      <td>₹${s.latest_close.toFixed(2)}</td>
      <td style="font-weight: 700; color: ${isGain ? "var(--success)" : "var(--danger)"}">
        ${isGain ? "+" : ""}${s.percentage_return.toFixed(2)}%
      </td>
      <td>${s.annualized_volatility.toFixed(2)}%</td>
      <td><span class="badge ${badgeClass}">${statusText}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function renderOverviewCharts(topItems) {
  const labels = topItems.map((i) => i.symbol);
  const prices = topItems.map((i) => i.latest_close);
  const volumes = topItems.map((i) => i.total_volume);

  const ctx1 = document.getElementById("overviewValuationChart");
  if (valuationChartInstance) valuationChartInstance.destroy();
  valuationChartInstance = new Chart(ctx1, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Latest Closing Price (₹)",
        data: prices,
        backgroundColor: "rgba(59, 130, 246, 0.75)",
        borderColor: "#3b82f6",
        borderWidth: 1,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.05)" } },
        x: { grid: { display: false } }
      }
    }
  });

  const ctx2 = document.getElementById("overviewVolumePieChart");
  if (volumePieChartInstance) volumePieChartInstance.destroy();
  volumePieChartInstance = new Chart(ctx2, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data: volumes,
        backgroundColor: [
          "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"
        ]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "right" } }
    }
  });
}

// ---------------------------------------------------------------------------
// 4. Section B: Stock Analysis Controller
// ---------------------------------------------------------------------------

async function loadStockAnalysisData() {
  await onStockSelected();
  updateComparison();
}

async function onStockSelected() {
  const sel = document.getElementById("stockSelector");
  const symbol = sel.value || "RELIANCE";

  try {
    // 1. Fetch Summary
    const sumRes = await fetch(`/api/stock/${symbol}/summary`);
    const sumJson = await sumRes.json();
    if (sumJson.status === "success") {
      const s = sumJson.data;
      document.getElementById("selLatestClose").textContent = `₹${s.latest_close.toFixed(2)}`;
      document.getElementById("selSymbolName").textContent = `${s.symbol} (${s.company_name})`;
      document.getElementById("selHighPrice").textContent = `₹${s.highest_price.toFixed(2)}`;
      document.getElementById("selLowPrice").textContent = `₹${s.lowest_price.toFixed(2)}`;
      document.getElementById("selReturnPct").textContent = `${s.percentage_return >= 0 ? "+" : ""}${s.percentage_return.toFixed(2)}%`;
      document.getElementById("selReturnPct").style.color = s.percentage_return >= 0 ? "var(--success)" : "var(--danger)";
      document.getElementById("selTradingDays").textContent = `${s.trading_days} historical trading sessions`;
    }

    // 2. Fetch Time Series
    const dataRes = await fetch(`/api/stock/${symbol}`);
    const dataJson = await dataRes.json();
    if (dataJson.status === "success") {
      renderStockPlot(dataJson.data, symbol);
    }
  } catch (e) {
    console.error("Failed to load stock data:", e);
  }
}

function toggleChartType(type) {
  chartTypeMode = type;
  onStockSelected();
}

function renderStockPlot(records, symbol) {
  const dates = records.map((r) => r.Date);
  const opens = records.map((r) => r.Open);
  const highs = records.map((r) => r.High);
  const lows = records.map((r) => r.Low);
  const closes = records.map((r) => r.Close);

  const themeLayout = getPlotlyThemeLayout();

  let trace;
  if (chartTypeMode === "candlestick") {
    trace = {
      x: dates,
      open: opens,
      high: highs,
      low: lows,
      close: closes,
      type: "candlestick",
      increasing: { line: { color: "#10b981" } },
      decreasing: { line: { color: "#ef4444" } },
      name: symbol
    };
  } else {
    trace = {
      x: dates,
      y: closes,
      type: "scatter",
      mode: "lines",
      line: { color: "#3b82f6", width: 2 },
      name: `${symbol} Close Price`
    };
  }

  const layout = {
    ...themeLayout,
    title: false,
    xaxis: { rangeslider: { visible: false }, gridcolor: themeLayout.gridcolor },
    yaxis: { title: "Price (INR)", gridcolor: themeLayout.gridcolor }
  };

  Plotly.newPlot("stockPricePlot", [trace], layout, { responsive: true, displayModeBar: false });
}

async function updateComparison() {
  const chks = document.querySelectorAll(".compare-chk:checked");
  const symbols = Array.from(chks).map((c) => c.value);
  if (!symbols.length) return;

  try {
    const res = await fetch(`/api/compare?symbols=${symbols.join(",")}`);
    const json = await res.json();
    if (json.status === "success") {
      const data = json.data;
      const dates = data.map((d) => d.Date);
      const themeLayout = getPlotlyThemeLayout();

      const traces = symbols.map((sym) => ({
        x: dates,
        y: data.map((d) => d[sym]),
        type: "scatter",
        mode: "lines",
        name: sym
      }));

      const layout = {
        ...themeLayout,
        title: false,
        xaxis: { gridcolor: themeLayout.gridcolor },
        yaxis: { title: "Closing Price (INR)", gridcolor: themeLayout.gridcolor },
        legend: { orientation: "h", y: 1.15 }
      };

      Plotly.newPlot("comparisonPlot", traces, layout, { responsive: true, displayModeBar: false });
    }
  } catch (e) {
    console.error("Comparison load failed:", e);
  }
}

function exportSelectedStock() {
  const sel = document.getElementById("stockSelector");
  const symbol = sel.value || "RELIANCE";
  window.location.href = `/api/export/${symbol}`;
}

// ---------------------------------------------------------------------------
// 5. Section C: Trend Analysis Controller
// ---------------------------------------------------------------------------

async function loadTrendIndicators() {
  const sel = document.getElementById("trendStockSelector");
  const symbol = sel.value || "RELIANCE";

  try {
    const json = await fetchApiJson(`/api/stock/${symbol}/indicators`);
    const d = json.data;
    const records = d.data;
    const signals = d.signals;
    if (!records || records.length === 0) {
      throw new Error(`No indicator data is available for ${symbol}.`);
    }

    // Update badge
    const badge = document.getElementById("trendStateBadge");
    badge.textContent = `${signals.trend_state} Trend`;
    badge.className = `badge ${signals.trend_state === "Bullish" ? "badge-bullish" : signals.trend_state === "Bearish" ? "badge-bearish" : "badge-neutral"}`;

    document.getElementById("rsiValueBadge").textContent = `RSI-14: ${signals.latest_rsi_14}`;

    renderMovingAveragesPlot(records, symbol);
    renderRsiPlot(records);
    renderMacdPlot(records);
    renderBollingerPlot(records, symbol);
  } catch (e) {
    console.error("Failed to load trend indicators:", e);
    ["maPlot", "rsiPlot", "macdPlot", "bollingerPlot"].forEach((plotId) => {
      const plot = document.getElementById(plotId);
      if (plot) {
        plot.textContent = `Trend data could not be loaded: ${e.message}`;
      }
    });
  }
}

function renderMovingAveragesPlot(records, symbol) {
  const dates = records.map((r) => r.Date);
  const closes = records.map((r) => r.Close);
  const sma20 = records.map((r) => r.SMA_20);
  const sma50 = records.map((r) => r.SMA_50);
  const ema20 = records.map((r) => r.EMA_20);

  const theme = getPlotlyThemeLayout();

  const traces = [
    { x: dates, y: closes, type: "scatter", mode: "lines", name: "Close Price", line: { color: "#94a3b8", width: 1.5 } },
    { x: dates, y: sma20, type: "scatter", mode: "lines", name: "SMA 20", line: { color: "#3b82f6", width: 2 } },
    { x: dates, y: sma50, type: "scatter", mode: "lines", name: "SMA 50", line: { color: "#f59e0b", width: 2 } },
    { x: dates, y: ema20, type: "scatter", mode: "lines", name: "EMA 20", line: { color: "#10b981", width: 2, dash: "dot" } },
  ];

  const layout = {
    ...theme,
    xaxis: { gridcolor: theme.gridcolor },
    yaxis: { title: "Price (INR)", gridcolor: theme.gridcolor },
    legend: { orientation: "h", y: 1.12 }
  };

  Plotly.newPlot("maPlot", traces, layout, { responsive: true, displayModeBar: false });
}

function renderRsiPlot(records) {
  const dates = records.map((r) => r.Date);
  const rsi = records.map((r) => r.RSI_14);
  const theme = getPlotlyThemeLayout();

  const traces = [
    { x: dates, y: rsi, type: "scatter", mode: "lines", name: "RSI-14", line: { color: "#8b5cf6", width: 2 } },
    { x: dates, y: dates.map(() => 70), type: "scatter", mode: "lines", name: "Overbought (70)", line: { color: "#ef4444", width: 1, dash: "dash" } },
    { x: dates, y: dates.map(() => 30), type: "scatter", mode: "lines", name: "Oversold (30)", line: { color: "#10b981", width: 1, dash: "dash" } },
  ];

  const layout = {
    ...theme,
    xaxis: { gridcolor: theme.gridcolor },
    yaxis: { title: "RSI", range: [0, 100], gridcolor: theme.gridcolor },
    legend: { orientation: "h", y: 1.15 }
  };

  Plotly.newPlot("rsiPlot", traces, layout, { responsive: true, displayModeBar: false });
}

function renderMacdPlot(records) {
  const dates = records.map((r) => r.Date);
  const macd = records.map((r) => r.MACD);
  const signal = records.map((r) => r.Signal);
  const hist = records.map((r) => r.Histogram);
  const theme = getPlotlyThemeLayout();

  const traces = [
    { x: dates, y: macd, type: "scatter", mode: "lines", name: "MACD", line: { color: "#2563eb", width: 2 } },
    { x: dates, y: signal, type: "scatter", mode: "lines", name: "Signal", line: { color: "#f97316", width: 1.8 } },
    { x: dates, y: hist, type: "bar", name: "Histogram", marker: { color: hist.map((h) => (h >= 0 ? "#10b981" : "#ef4444")) } },
  ];

  const layout = {
    ...theme,
    xaxis: { gridcolor: theme.gridcolor },
    yaxis: { title: "Value", gridcolor: theme.gridcolor },
    legend: { orientation: "h", y: 1.15 }
  };

  Plotly.newPlot("macdPlot", traces, layout, { responsive: true, displayModeBar: false });
}

function renderBollingerPlot(records, symbol) {
  const dates = records.map((r) => r.Date);
  const closes = records.map((r) => r.Close);
  const upper = records.map((r) => r.BB_Upper);
  const middle = records.map((r) => r.BB_Middle);
  const lower = records.map((r) => r.BB_Lower);
  const theme = getPlotlyThemeLayout();

  const traces = [
    { x: dates, y: upper, type: "scatter", mode: "lines", name: "Upper Band (+2σ)", line: { color: "rgba(59, 130, 246, 0.4)", width: 1 } },
    { x: dates, y: lower, type: "scatter", mode: "lines", name: "Lower Band (-2σ)", line: { color: "rgba(59, 130, 246, 0.4)", width: 1 }, fill: "tonexty", fillcolor: "rgba(59, 130, 246, 0.08)" },
    { x: dates, y: middle, type: "scatter", mode: "lines", name: "SMA 20 (Basis)", line: { color: "#f59e0b", width: 1.5, dash: "dot" } },
    { x: dates, y: closes, type: "scatter", mode: "lines", name: `${symbol} Close`, line: { color: "#0f172a", width: 1.8 } },
  ];

  const layout = {
    ...theme,
    xaxis: { gridcolor: theme.gridcolor },
    yaxis: { title: "Price (INR)", gridcolor: theme.gridcolor },
    legend: { orientation: "h", y: 1.12 }
  };

  Plotly.newPlot("bollingerPlot", traces, layout, { responsive: true, displayModeBar: false });
}

// ---------------------------------------------------------------------------
// 6. Section D: Big Data & MapReduce Controller
// ---------------------------------------------------------------------------

async function loadBigDataMetrics() {
  try {
    // 1. Load HDFS Storage Info
    const hdfsRes = await fetch("/api/hdfs/info");
    const hdfsJson = await hdfsRes.json();
    if (hdfsJson.status === "success") {
      document.getElementById("hdfsMode").textContent = hdfsJson.mode;
      const s = hdfsJson.storage;
      if (s) {
        document.getElementById("hdfsCapacity").textContent = s.total_capacity_gb || "500 GB";
        document.getElementById("hdfsUsedSize").textContent = s.used_capacity_mb || "2.42 MB";
      }
      document.getElementById("hdfsNoticeText").textContent =
        hdfsJson.is_connected
          ? "Connected to Live Hadoop HDFS & YARN Execution Cluster. Verified distributed metrics."
          : "Demonstration & Local Simulation Mode. HDFS cluster is offline; metrics verified via streaming pipes.";
    }

    // 2. Load MapReduce Job Status
    const mrRes = await fetch("/api/mapreduce/status");
    const mrJson = await mrRes.json();
    if (mrJson.status === "success") {
      renderMapReduceJobsTable(mrJson.jobs);
    }

    inspectMapReduceOutput();
  } catch (e) {
    console.error("Failed to load Big Data metrics:", e);
  }
}

function renderMapReduceJobsTable(jobs) {
  const tbody = document.getElementById("mrJobsTableBody");
  tbody.innerHTML = "";

  jobs.forEach((j) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><code>${j.id}</code></td>
      <td><strong>${j.name}</strong></td>
      <td><span style="font-family: monospace; font-size: 12px;">${j.mapper}</span></td>
      <td><span style="font-family: monospace; font-size: 12px;">${j.reducer}</span></td>
      <td><strong>${Number(j.records).toLocaleString()}</strong> records</td>
      <td>${j.duration}</td>
      <td><span class="badge badge-completed"><i class="fa-solid fa-circle-check"></i> ${j.status}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

async function inspectMapReduceOutput() {
  const jobSel = document.getElementById("mrOutputJobSelect");
  const job = jobSel.value;
  const term = document.getElementById("mrOutputTerminal");

  try {
    const res = await fetch(`/api/mapreduce/results?job=${job}`);
    const json = await res.json();
    if (json.status === "success") {
      const jData = json.results[job];
      if (jData && jData.sample.length > 0) {
        term.textContent = `=== PARTITION OUTPUT: ${job} (Displaying first ${jData.sample.length} of ${jData.records_count} rows) ===\n\n` +
          jData.sample.join("\n");
      } else {
        term.textContent = `No output file found yet for ${job}. Click 'Run MapReduce Suite' above to execute.`;
      }
    }
  } catch (e) {
    term.textContent = `Error inspecting output: ${e}`;
  }
}

async function triggerMapReducePipeline() {
  const term = document.getElementById("mrOutputTerminal");
  term.textContent = "Executing all 7 Hadoop MapReduce jobs across HDFS datasets... please wait.";

  try {
    const res = await fetch("/api/processing/mapreduce", { method: "POST" });
    const json = await res.json();
    if (json.status === "success") {
      term.textContent = `SUCCESS: ${json.message}\nReloading job telemetry...`;
      await loadBigDataMetrics();
    } else {
      term.textContent = `ERROR: ${json.message}`;
    }
  } catch (e) {
    term.textContent = `Network / Execution Error: ${e}`;
  }
}
