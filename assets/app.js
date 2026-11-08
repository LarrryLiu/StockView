"use strict";

(async function () {
  const byId = (id) => document.getElementById(id);
  const state = { lists: {}, symbol: "", frame: "day", request: 0 };
  let chart;
  const status = byId("status");
  async function getJson(url) {
    const response = await fetch(url, { cache: "no-store" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    return payload;
  }
  function showError(error) {
    status.className = "error";
    status.textContent = error.message;
  }
  async function renderChart() {
    const sequence = ++state.request;
    const month = byId("month").value;
    const row = state.lists[month].find((item) => item.symbol === state.symbol);
    if (!row) return;
    byId("name").textContent = row.name || row.symbol;
    byId("symbol").textContent = row.symbol;
    byId("cutoff").textContent = `Cutoff / 历史截止日: ${row.cutoff}`;
    status.className = "";
    status.textContent = "Loading local candles… / 正在读取本地 K 线…";
    try {
      const query = new URLSearchParams({ month, symbol: state.symbol, timeframe: state.frame });
      const payload = await getJson(`/api/candles?${query}`);
      if (sequence !== state.request) return;
      if (chart) chart.remove();
      chart = window.LightweightCharts.createChart(byId("chart"), {
        width: byId("chart").clientWidth, height: byId("chart").clientHeight,
        layout: { backgroundColor: "#ffffff", textColor: "#64766f", fontSize: 10 },
        grid: { vertLines: { color: "#f2f4ef" }, horzLines: { color: "#f2f4ef" } },
        rightPriceScale: { borderColor: "#e5eae3", scaleMargins: { top: 0.08, bottom: 0.25 } },
        timeScale: { borderColor: "#e5eae3" },
      });
      const candles = chart.addCandlestickSeries({
        upColor: "#307c5b", downColor: "#bb6860", borderVisible: false,
        wickUpColor: "#307c5b", wickDownColor: "#bb6860",
      });
      candles.setData(payload.bars);
      const volumes = chart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "volume" });
      chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
      volumes.setData(payload.bars.map((bar) => ({
        time: bar.time, value: bar.volume, color: bar.close >= bar.open ? "#307c5b44" : "#bb686044",
      })));
      chart.timeScale().fitContent();
      status.textContent = `${payload.bars.length} candles · ${state.frame} · Local data / 本地数据`;
    } catch (error) { if (sequence === state.request) showError(error); }
  }
  function renderSymbols() {
    const rows = state.lists[byId("month").value] || [];
    if (!rows.some((row) => row.symbol === state.symbol)) state.symbol = rows[0]?.symbol || "";
    byId("symbols").replaceChildren();
    for (const row of rows) {
      const button = document.createElement("button");
      button.className = `symbol-button${row.symbol === state.symbol ? " active" : ""}`;
      button.setAttribute("aria-pressed", String(row.symbol === state.symbol));
      const symbol = document.createElement("strong");
      symbol.textContent = row.symbol;
      const name = document.createElement("span");
      name.textContent = row.name || row.symbol;
      button.append(symbol, name);
      button.addEventListener("click", () => { state.symbol = row.symbol; renderSymbols(); renderChart(); });
      byId("symbols").append(button);
    }
  }
  byId("month").addEventListener("change", () => { renderSymbols(); renderChart(); });
  document.querySelectorAll("[data-frame]").forEach((button) => button.addEventListener("click", () => {
    state.frame = button.dataset.frame;
    document.querySelectorAll("[data-frame]").forEach((item) => item.classList.toggle("active", item === button));
    renderChart();
  }));
  new ResizeObserver(() => { if (chart) chart.resize(byId("chart").clientWidth, byId("chart").clientHeight); }).observe(byId("chart"));
  try {
    const mode = await getJson("/api/mode");
    if (mode.private_strategy) {
      byId("data-kind").replaceChildren();
      byId("data-kind").append("Private strategy output");
      const note = document.createElement("small");
      note.lang = "zh"; note.textContent = "私有策略本机结果";
      byId("data-kind").append(note);
    }
    state.lists = await getJson("/api/watchlists");
    const months = Object.keys(state.lists).filter((month) => state.lists[month].length).sort().reverse();
    if (!months.length) throw new Error("No watchlists. / 暂无观察名单。");
    for (const month of months) {
      const option = document.createElement("option"); option.value = month; option.textContent = month; byId("month").append(option);
    }
    renderSymbols();
    await renderChart();
  } catch (error) { showError(error); }
})();
