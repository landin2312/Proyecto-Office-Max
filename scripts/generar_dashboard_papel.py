from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


HTML_TEMPLATE = r"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dashboard Elasticidad - Papel</title>
  <style>
    :root {
      --bg: #f7f8fa;
      --panel: #ffffff;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #d8dde6;
      --accent: #2563eb;
      --green: #059669;
      --red: #dc2626;
      --amber: #d97706;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      letter-spacing: 0;
    }
    header {
      background: #ffffff;
      border-bottom: 1px solid var(--line);
      padding: 18px 24px 14px;
      position: sticky;
      top: 0;
      z-index: 5;
    }
    h1 {
      font-size: 22px;
      line-height: 1.2;
      margin: 0 0 12px;
      font-weight: 700;
    }
    .filters {
      display: grid;
      grid-template-columns: minmax(340px, 1.6fr) 190px 150px 150px;
      gap: 12px;
      align-items: end;
    }
    label {
      display: grid;
      gap: 5px;
      font-size: 12px;
      font-weight: 700;
      color: #374151;
    }
    .filter-title {
      font-size: 12px;
      font-weight: 700;
      color: #374151;
      margin-bottom: 5px;
    }
    .sku-search {
      height: 34px;
      border: 1px solid #bfc7d4;
      background: #ffffff;
      color: var(--ink);
      border-radius: 6px;
      padding: 0 10px;
      font-size: 14px;
      width: 100%;
    }
    .sku-list {
      margin-top: 6px;
      height: 118px;
      overflow-y: auto;
      background: #ffffff;
      border: 1px solid #bfc7d4;
      border-radius: 6px;
      padding: 4px;
    }
    .sku-actions {
      display: grid;
      grid-template-columns: 120px 1fr;
      gap: 8px;
      align-items: center;
      margin-top: 6px;
    }
    .sku-apply {
      height: 32px;
      border: 1px solid #1d4ed8;
      background: #2563eb;
      color: #ffffff;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
    }
    .sku-count {
      color: var(--muted);
      font-size: 11px;
      font-weight: 600;
    }
    .sku-option {
      width: 100%;
      border: 0;
      border-radius: 4px;
      background: #ffffff;
      color: var(--ink);
      display: block;
      padding: 8px 9px;
      text-align: left;
      font-size: 13px;
      line-height: 1.25;
      cursor: pointer;
    }
    .sku-option:hover,
    .sku-option.active {
      background: #eaf2ff;
    }
    .status {
      min-height: 14px;
      color: var(--red);
      font-size: 11px;
      font-weight: 600;
    }
    select, input {
      height: 38px;
      border: 1px solid #bfc7d4;
      background: white;
      color: var(--ink);
      border-radius: 6px;
      padding: 0 10px;
      font-size: 14px;
      width: 100%;
    }
    main {
      max-width: 1480px;
      margin: 0 auto;
      padding: 18px 20px 32px;
    }
    .kpis {
      display: grid;
      grid-template-columns: repeat(6, minmax(120px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }
    .kpi, .chart, .table-panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .kpi {
      padding: 12px;
      min-height: 74px;
    }
    .kpi .label {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 8px;
    }
    .kpi .value {
      font-size: 20px;
      font-weight: 700;
      overflow-wrap: anywhere;
    }
    .grid-main {
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 14px;
      align-items: start;
    }
    .grid-heatmaps {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 14px;
    }
    .chart, .table-panel {
      padding: 12px;
      min-width: 0;
    }
    .chart h2, .table-panel h2 {
      margin: 0 0 8px;
      font-size: 14px;
      line-height: 1.25;
    }
    .chart p {
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 12px;
    }
    svg {
      width: 100%;
      display: block;
      overflow: visible;
    }
    .axis text, .legend text {
      fill: var(--muted);
      font-size: 11px;
    }
    .axis line, .axis path, .grid-line {
      stroke: #d7dce5;
      stroke-width: 1;
    }
    .tooltip {
      position: fixed;
      pointer-events: none;
      background: #111827;
      color: white;
      padding: 8px 9px;
      border-radius: 6px;
      font-size: 12px;
      line-height: 1.35;
      opacity: 0;
      transform: translate(-50%, -110%);
      max-width: 260px;
      z-index: 20;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    th, td {
      padding: 7px 8px;
      border-bottom: 1px solid #edf0f5;
      text-align: right;
      white-space: nowrap;
    }
    th:first-child, td:first-child { text-align: left; }
    th { color: #374151; background: #f9fafb; }
    .footer-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-top: 14px;
    }
    @media (max-width: 1100px) {
      .filters { grid-template-columns: 1fr 1fr; }
      .kpis { grid-template-columns: repeat(3, 1fr); }
      .grid-main, .footer-grid { grid-template-columns: 1fr; }
      .grid-heatmaps { grid-template-columns: 1fr; }
    }
    @media (max-width: 640px) {
      header { position: static; padding: 14px; }
      main { padding: 14px; }
      .filters, .kpis { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Elasticidad Dinámica - Departamento Papel</h1>
    <div class="filters">
      <div class="sku-field">
        <div class="filter-title">SKU</div>
        <input id="skuSearch" class="sku-search" placeholder="Filtrar SKU o nombre" />
        <div class="sku-actions">
          <button id="skuApply" class="sku-apply" type="button">Aplicar SKU</button>
          <span id="skuCount" class="sku-count"></span>
        </div>
        <div id="skuListPanel" class="sku-list"></div>
      </div>
      <label>Ventana
        <select id="windowSelect">
          <option value="mensual">Mensual</option>
          <option value="trimestral">Trimestral</option>
          <option value="semestral">Semestral</option>
        </select>
      </label>
      <label>R² mínimo
        <input id="r2Min" type="number" min="0" max="1" step="0.05" value="0" />
      </label>
      <label>N mínimo
        <input id="nMin" type="number" min="1" step="1" value="3" />
      </label>
    </div>
  </header>

  <main>
    <section class="kpis" id="kpis"></section>

    <section class="grid-main">
      <div class="chart">
        <h2>Beta vs tiempo</h2>
        <p>Serie temporal de elasticidad para la ventana seleccionada.</p>
        <svg id="lineBeta" viewBox="0 0 760 340"></svg>
      </div>
      <div class="chart">
        <h2>Precio y cantidad mensual</h2>
        <p>Precio promedio y unidades vendidas por mes.</p>
        <svg id="priceQty" viewBox="0 0 520 340"></svg>
      </div>
    </section>

    <section class="grid-heatmaps">
      <div class="chart">
        <h2>Heatmap beta</h2>
        <p>Intensidad por año y mes de inicio de ventana.</p>
        <svg id="heatBeta" viewBox="0 0 520 270"></svg>
      </div>
      <div class="chart">
        <h2>Heatmap R²</h2>
        <p>Calidad del ajuste por periodo.</p>
        <svg id="heatR2" viewBox="0 0 520 270"></svg>
      </div>
      <div class="chart">
        <h2>Heatmap observaciones</h2>
        <p>Número de puntos usados en cada regresión.</p>
        <svg id="heatN" viewBox="0 0 520 270"></svg>
      </div>
      <div class="chart">
        <h2>Heatmap promoción</h2>
        <p>Meses con venta de SKU marcada con promoción.</p>
        <svg id="heatPromo" viewBox="0 0 520 270"></svg>
      </div>
    </section>

    <section class="footer-grid">
      <div class="chart">
        <h2>Relación precio-cantidad</h2>
        <p>Puntos mensuales en escala logarítmica.</p>
        <svg id="scatterLog" viewBox="0 0 520 330"></svg>
      </div>
      <div class="table-panel">
        <h2>Cambios importantes</h2>
        <table>
          <thead>
            <tr>
              <th>Periodo</th><th>Beta anterior</th><th>Beta actual</th><th>Delta</th><th>Razón</th>
            </tr>
          </thead>
          <tbody id="changesTable"></tbody>
        </table>
      </div>
    </section>
  </main>

  <div class="tooltip" id="tooltip"></div>
  <script id="dashboard-data" type="application/json">__DATA__</script>
  <script>
    const DATA = JSON.parse(document.getElementById("dashboard-data").textContent);
    const skuSearch = document.getElementById("skuSearch");
    const skuListPanel = document.getElementById("skuListPanel");
    const skuApply = document.getElementById("skuApply");
    const skuCount = document.getElementById("skuCount");
    let selectedSku = null;
    let visibleSkuItems = [];
    const windowSelect = document.getElementById("windowSelect");
    const r2Min = document.getElementById("r2Min");
    const nMin = document.getElementById("nMin");
    const tooltip = document.getElementById("tooltip");
    const months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

    function fmt(value, digits = 2) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "NA";
      return Number(value).toLocaleString("es-MX", { maximumFractionDigits: digits, minimumFractionDigits: digits });
    }
    function showTip(event, html) {
      tooltip.innerHTML = html;
      tooltip.style.left = event.clientX + "px";
      tooltip.style.top = event.clientY + "px";
      tooltip.style.opacity = "1";
    }
    function hideTip() { tooltip.style.opacity = "0"; }
    function clear(svg) { while (svg.firstChild) svg.removeChild(svg.firstChild); }
    function el(name, attrs = {}) {
      const node = document.createElementNS("http://www.w3.org/2000/svg", name);
      Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
      return node;
    }
    function extent(values) {
      const nums = values.filter(v => v !== null && v !== undefined && Number.isFinite(Number(v))).map(Number);
      if (!nums.length) return [0, 1];
      let min = Math.min(...nums), max = Math.max(...nums);
      if (min === max) { min -= 1; max += 1; }
      return [min, max];
    }
    function colorScale(value, min, max, mode) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "#eef1f5";
      const v = Math.max(0, Math.min(1, (Number(value) - min) / (max - min || 1)));
      if (mode === "diverging") {
        if (Number(value) < 0) {
          const a = Math.min(1, Math.abs(Number(value)) / Math.max(Math.abs(min), 1));
          return `rgb(${Math.round(235 - 30*a)}, ${Math.round(245 - 110*a)}, ${Math.round(255 - 40*a)})`;
        }
        const a = Math.min(1, Number(value) / Math.max(Math.abs(max), 1));
        return `rgb(${Math.round(255 - 25*a)}, ${Math.round(241 - 120*a)}, ${Math.round(230 - 110*a)})`;
      }
      return `rgb(${Math.round(239 - 190*v)}, ${Math.round(246 - 80*v)}, ${Math.round(255 - 50*v)})`;
    }
    function validBetas(sku, windowType) {
      const minR = Number(r2Min.value || 0);
      const minN = Number(nMin.value || 1);
      return (DATA.betas[sku] || [])
        .filter(d => d.tipo_ventana === windowType)
        .filter(d => d.beta !== null && d.r2 !== null && d.n_observaciones >= minN && d.r2 >= minR)
        .sort((a, b) => a.periodo_inicio.localeCompare(b.periodo_inicio));
    }
    function drawAxes(svg, box, xTicks, yTicks) {
      svg.appendChild(el("line", { x1: box.x, y1: box.y + box.h, x2: box.x + box.w, y2: box.y + box.h, class: "axis" }));
      svg.appendChild(el("line", { x1: box.x, y1: box.y, x2: box.x, y2: box.y + box.h, class: "axis" }));
      yTicks.forEach(t => {
        svg.appendChild(el("line", { x1: box.x, y1: t.y, x2: box.x + box.w, y2: t.y, class: "grid-line" }));
        const text = el("text", { x: box.x - 8, y: t.y + 4, "text-anchor": "end", class: "axis" });
        text.textContent = t.label;
        svg.appendChild(text);
      });
      xTicks.forEach(t => {
        const text = el("text", { x: t.x, y: box.y + box.h + 18, "text-anchor": "middle", class: "axis" });
        text.textContent = t.label;
        svg.appendChild(text);
      });
    }
    function drawLineChart(svgId, data, yKey, color, label) {
      const svg = document.getElementById(svgId);
      clear(svg);
      const box = { x: 58, y: 20, w: 680, h: 270 };
      if (!data.length) {
        const text = el("text", { x: 380, y: 160, "text-anchor": "middle", fill: "#6b7280" });
        text.textContent = "Sin datos suficientes con los filtros actuales";
        svg.appendChild(text);
        return;
      }
      const ys = data.map(d => d[yKey]);
      const [minY, maxY] = extent(ys);
      const x = i => box.x + (data.length === 1 ? box.w / 2 : i * box.w / (data.length - 1));
      const y = v => box.y + box.h - (Number(v) - minY) * box.h / (maxY - minY || 1);
      const yTicks = [0, 0.25, 0.5, 0.75, 1].map(p => ({ y: box.y + box.h - p * box.h, label: fmt(minY + p * (maxY - minY), 1) }));
      const xTicks = data.filter((_, i) => i % Math.max(1, Math.ceil(data.length / 7)) === 0).map((d, i, arr) => ({ x: x(data.indexOf(d)), label: d.periodo_inicio.slice(0, 7) }));
      drawAxes(svg, box, xTicks, yTicks);
      const path = data.map((d, i) => `${i ? "L" : "M"} ${x(i)} ${y(d[yKey])}`).join(" ");
      svg.appendChild(el("path", { d: path, fill: "none", stroke: color, "stroke-width": 2.2 }));
      data.forEach((d, i) => {
        const c = el("circle", { cx: x(i), cy: y(d[yKey]), r: 4, fill: color });
        c.addEventListener("mousemove", ev => showTip(ev, `<b>${label}</b><br>${d.periodo_inicio} a ${d.periodo_fin}<br>Beta: ${fmt(d.beta, 3)}<br>R²: ${fmt(d.r2, 3)}<br>N: ${d.n_observaciones}`));
        c.addEventListener("mouseleave", hideTip);
        svg.appendChild(c);
      });
    }
    function drawPriceQty(sku) {
      const svg = document.getElementById("priceQty");
      clear(svg);
      const data = (DATA.monthly[sku] || []).sort((a, b) => a.mes.localeCompare(b.mes));
      const box = { x: 54, y: 20, w: 450, h: 270 };
      if (!data.length) return;
      const [minP, maxP] = extent(data.map(d => d.precio));
      const [minQ, maxQ] = extent(data.map(d => d.qty));
      const x = i => box.x + (data.length === 1 ? box.w / 2 : i * box.w / (data.length - 1));
      const yP = v => box.y + box.h - (Number(v) - minP) * box.h / (maxP - minP || 1);
      const yQ = v => box.y + box.h - (Number(v) - minQ) * box.h / (maxQ - minQ || 1);
      const yTicks = [0, .5, 1].map(p => ({ y: box.y + box.h - p * box.h, label: fmt(minP + p * (maxP - minP), 0) }));
      const xTicks = data.filter((_, i) => i % Math.max(1, Math.ceil(data.length / 6)) === 0).map(d => ({ x: x(data.indexOf(d)), label: d.mes }));
      drawAxes(svg, box, xTicks, yTicks);
      [["precio", yP, "#2563eb"], ["qty", yQ, "#d97706"]].forEach(([key, fn, color]) => {
        const path = data.map((d, i) => `${i ? "L" : "M"} ${x(i)} ${fn(d[key])}`).join(" ");
        svg.appendChild(el("path", { d: path, fill: "none", stroke: color, "stroke-width": 2 }));
      });
      const legend = el("text", { x: box.x + box.w - 5, y: box.y + 14, "text-anchor": "end", class: "legend" });
      legend.textContent = "Azul: precio | Naranja: qty";
      svg.appendChild(legend);
    }
    function drawHeatmap(svgId, rows, valueKey, mode, label) {
      const svg = document.getElementById(svgId);
      clear(svg);
      const box = { x: 58, y: 28, w: 448, h: 190 };
      const years = [...new Set(rows.map(d => d.periodo_inicio ? d.periodo_inicio.slice(0, 4) : d.mes.slice(0, 4)))].sort();
      const values = rows.map(d => d[valueKey]);
      const [minV, maxV] = extent(values);
      const cellW = box.w / 12;
      const cellH = box.h / Math.max(1, years.length);
      months.forEach((m, i) => {
        const t = el("text", { x: box.x + i * cellW + cellW / 2, y: 18, "text-anchor": "middle", class: "axis" });
        t.textContent = m;
        svg.appendChild(t);
      });
      years.forEach((year, yi) => {
        const yt = el("text", { x: box.x - 10, y: box.y + yi * cellH + cellH / 2 + 4, "text-anchor": "end", class: "axis" });
        yt.textContent = year;
        svg.appendChild(yt);
      });
      rows.forEach(d => {
        const date = d.periodo_inicio || `${d.mes}-01`;
        const year = date.slice(0, 4);
        const month = Number(date.slice(5, 7)) - 1;
        const yi = years.indexOf(year);
        if (yi < 0 || month < 0) return;
        const rect = el("rect", {
          x: box.x + month * cellW + 1,
          y: box.y + yi * cellH + 1,
          width: Math.max(1, cellW - 2),
          height: Math.max(1, cellH - 2),
          fill: colorScale(d[valueKey], minV, maxV, mode),
          stroke: "#ffffff",
          "stroke-width": 1
        });
        rect.addEventListener("mousemove", ev => showTip(ev, `<b>${label}</b><br>${date.slice(0, 7)}<br>${fmt(d[valueKey], 3)}`));
        rect.addEventListener("mouseleave", hideTip);
        svg.appendChild(rect);
      });
      const minText = el("text", { x: box.x, y: box.y + box.h + 24, class: "axis" });
      minText.textContent = `min ${fmt(minV, 2)}`;
      svg.appendChild(minText);
      const maxText = el("text", { x: box.x + box.w, y: box.y + box.h + 24, "text-anchor": "end", class: "axis" });
      maxText.textContent = `max ${fmt(maxV, 2)}`;
      svg.appendChild(maxText);
    }
    function drawScatter(sku) {
      const svg = document.getElementById("scatterLog");
      clear(svg);
      const data = (DATA.monthly[sku] || []).filter(d => d.precio > 0 && d.qty > 0);
      const box = { x: 58, y: 20, w: 450, h: 260 };
      if (!data.length) return;
      const xs = data.map(d => Math.log(d.precio));
      const ys = data.map(d => Math.log(d.qty));
      const [minX, maxX] = extent(xs), [minY, maxY] = extent(ys);
      const x = v => box.x + (v - minX) * box.w / (maxX - minX || 1);
      const y = v => box.y + box.h - (v - minY) * box.h / (maxY - minY || 1);
      drawAxes(svg, box, [], [0, .5, 1].map(p => ({ y: box.y + box.h - p * box.h, label: fmt(minY + p * (maxY - minY), 1) })));
      data.forEach(d => {
        const c = el("circle", { cx: x(Math.log(d.precio)), cy: y(Math.log(d.qty)), r: 5, fill: d.promocion > 0 ? "#dc2626" : "#2563eb", opacity: 0.8 });
        c.addEventListener("mousemove", ev => showTip(ev, `<b>${d.mes}</b><br>Precio: ${fmt(d.precio, 2)}<br>Qty: ${fmt(d.qty, 0)}<br>Promo: ${d.promocion > 0 ? "sí" : "no"}`));
        c.addEventListener("mouseleave", hideTip);
        svg.appendChild(c);
      });
    }
    function updateKpis(sku, windowType, betaRows) {
      const monthly = DATA.monthly[sku] || [];
      const product = DATA.products[sku] || {};
      const valid = betaRows.length;
      const avgBeta = valid ? betaRows.reduce((a, d) => a + d.beta, 0) / valid : null;
      const promoMonths = monthly.filter(d => d.promocion > 0).length;
      const totalQty = monthly.reduce((a, d) => a + Number(d.qty || 0), 0);
      const kpis = [
        ["Producto", product.prod_nm || sku],
        ["Ventana", windowType],
        ["Betas válidas", valid],
        ["Beta promedio", avgBeta === null ? "NA" : fmt(avgBeta, 3)],
        ["Meses con promo", promoMonths],
        ["Qty total", fmt(totalQty, 0)]
      ];
      const box = document.getElementById("kpis");
      box.innerHTML = "";
      kpis.forEach(([label, value]) => {
        const div = document.createElement("div");
        div.className = "kpi";
        div.innerHTML = `<div class="label">${label}</div><div class="value">${value}</div>`;
        box.appendChild(div);
      });
    }
    function updateTable(sku, windowType) {
      const rows = (DATA.changes[sku] || []).filter(d => d.tipo_ventana === windowType).slice(0, 12);
      const tbody = document.getElementById("changesTable");
      tbody.innerHTML = "";
      if (!rows.length) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td colspan="5">Sin cambios importantes para esta selección</td>`;
        tbody.appendChild(tr);
        return;
      }
      rows.forEach(d => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${d.periodo_actual}</td><td>${fmt(d.beta_anterior, 2)}</td><td>${fmt(d.beta_actual, 2)}</td><td>${fmt(d.delta_beta, 2)}</td><td>${d.razon_cambio}</td>`;
        tbody.appendChild(tr);
      });
    }
    function update() {
      const sku = selectedSku || (DATA.skus[0] && DATA.skus[0].sku);
      const windowType = windowSelect.value;
      const betaRows = validBetas(sku, windowType);
      const monthly = DATA.monthly[sku] || [];
      updateKpis(sku, windowType, betaRows);
      drawLineChart("lineBeta", betaRows, "beta", WINDOW_COLORS[windowType] || "#2563eb", "Beta");
      drawPriceQty(sku);
      drawHeatmap("heatBeta", betaRows, "beta", "diverging", "Beta");
      drawHeatmap("heatR2", betaRows, "r2", "sequential", "R²");
      drawHeatmap("heatN", betaRows, "n_observaciones", "sequential", "N observaciones");
      drawHeatmap("heatPromo", monthly, "promocion", "sequential", "Promoción");
      drawScatter(sku);
      updateTable(sku, windowType);
    }
    function init() {
      selectedSku = DATA.skus.length ? DATA.skus[0].sku : null;
      renderSkuList("");
      skuSearch.addEventListener("input", () => renderSkuList(skuSearch.value));
      skuSearch.addEventListener("keydown", event => {
        if (event.key === "Enter") {
          event.preventDefault();
          applySkuSearch();
        }
      });
      skuApply.addEventListener("click", applySkuSearch);
      skuListPanel.addEventListener("click", event => {
        const button = event.target.closest(".sku-option");
        if (!button || !button.dataset.sku) return;
        const item = DATA.skus.find(row => row.sku === button.dataset.sku);
        if (item) selectSku(item, false);
      });
      [windowSelect, r2Min, nMin].forEach(node => node.addEventListener("change", update));
      updateActiveSku();
      update();
    }
    function renderSkuList(filterText) {
      const filter = String(filterText || "").trim().toLowerCase();
      skuListPanel.innerHTML = "";
      const filtered = DATA.skus.filter(item => (`${item.sku} ${item.name || ""}`).toLowerCase().includes(filter));
      const source = filter ? filtered : DATA.skus;
      visibleSkuItems = source;
      skuCount.textContent = filter
        ? `${source.length} coincidencia${source.length === 1 ? "" : "s"}`
        : `${DATA.skus.length} SKUs de Papel`;
      if (!source.length) {
        const empty = document.createElement("div");
        empty.className = "sku-option";
        empty.textContent = "Sin coincidencias";
        skuListPanel.appendChild(empty);
        return;
      }
      source.forEach(item => {
        const opt = document.createElement("button");
        opt.type = "button";
        opt.className = "sku-option";
        opt.dataset.sku = item.sku;
        opt.textContent = `${item.sku} - ${item.name || ""}`.slice(0, 140);
        skuListPanel.appendChild(opt);
      });
      updateActiveSku();
    }
    function applySkuSearch() {
      const text = String(skuSearch.value || "").trim().toLowerCase();
      if (!text && visibleSkuItems.length) {
        selectSku(visibleSkuItems[0]);
        return;
      }
      const exact = DATA.skus.find(item => item.sku.toLowerCase() === text);
      const prefix = DATA.skus.find(item => item.sku.toLowerCase().startsWith(text));
      const firstVisible = visibleSkuItems[0];
      const target = exact || prefix || firstVisible;
      if (target) {
        selectSku(target, true);
      } else {
        skuCount.textContent = "No hay SKU de Papel con ese texto";
      }
    }
    function selectSku(item, updateSearchText) {
      selectedSku = item.sku;
      if (updateSearchText) {
        skuSearch.value = item.sku;
        renderSkuList(skuSearch.value);
      }
      updateActiveSku();
      update();
    }
    function updateActiveSku() {
      skuListPanel.querySelectorAll(".sku-option").forEach(node => {
        node.classList.toggle("active", node.dataset.sku === selectedSku);
      });
    }
    init();
  </script>
</body>
</html>
"""


def to_number(value: object) -> float | None:
    if pd.isna(value):
        return None
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return None
    return float(number)


def records_by_key(df: pd.DataFrame, key: str, columns: list[str]) -> dict[str, list[dict[str, object]]]:
    output: dict[str, list[dict[str, object]]] = {}
    for sku, group in df.groupby(key, sort=False):
        output[str(sku)] = group[columns].to_dict(orient="records")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera dashboard HTML de elasticidad para departamento Papel.")
    parser.add_argument("--master", default=Path("output/MASTER_FINAL_SKU_FECHA_PAPEL.csv"), type=Path)
    parser.add_argument("--betas", default=Path("output/elasticidad_dinamica_betas_papel.csv"), type=Path)
    parser.add_argument("--diagnostico", default=Path("output/diagnostico_betas_papel.csv"), type=Path)
    parser.add_argument("--cambios", default=Path("output/cambios_importantes_betas_papel.csv"), type=Path)
    parser.add_argument("--output", default=Path("output/dashboard_elasticidad_papel.html"), type=Path)
    args = parser.parse_args()

    master = pd.read_csv(args.master, dtype={"prod_nbr": str}, encoding="utf-8-sig")
    betas = pd.read_csv(args.betas, dtype={"SKU": str}, encoding="utf-8-sig")
    changes = pd.read_csv(args.cambios, dtype={"SKU": str}, encoding="utf-8-sig") if args.cambios.exists() else pd.DataFrame()
    diagnostic = pd.read_csv(args.diagnostico, dtype={"metric": str}, encoding="utf-8-sig")

    for col in ["precio", "qty", "promocion", "descuento", "venta_neta"]:
        master[col] = pd.to_numeric(master[col], errors="coerce")
    master["fecha"] = pd.to_datetime(master["fecha"], errors="coerce")
    monthly = (
        master.groupby(["prod_nbr", "mes"], as_index=False)
        .agg(
            precio=("precio", "mean"),
            qty=("qty", "sum"),
            promocion=("promocion", "max"),
            descuento=("descuento", "mean"),
            venta_neta=("venta_neta", "sum"),
        )
        .sort_values(["prod_nbr", "mes"])
    )
    for col in ["precio", "qty", "promocion", "descuento", "venta_neta"]:
        monthly[col] = monthly[col].map(to_number)

    for col in ["beta", "r2", "n_observaciones"]:
        betas[col] = pd.to_numeric(betas[col], errors="coerce")
        betas[col] = betas[col].map(to_number)
    betas = betas.sort_values(["SKU", "tipo_ventana", "periodo_inicio"])

    product_dim = (
        master[["prod_nbr", "prod_nm", "subdept_nm", "class_nm"]]
        .drop_duplicates("prod_nbr")
        .set_index("prod_nbr")
        .fillna("")
        .to_dict(orient="index")
    )
    top = diagnostic[diagnostic["seccion"] == "top_20_mas_betas_validas"].copy()
    top["valor"] = pd.to_numeric(top["valor"], errors="coerce")
    top_skus = top.sort_values("valor", ascending=False)["metric"].astype(str).tolist()
    all_skus = sorted(master["prod_nbr"].dropna().astype(str).unique())
    ordered_skus = top_skus + [sku for sku in all_skus if sku not in set(top_skus)]
    sku_items = [{"sku": sku, "name": product_dim.get(sku, {}).get("prod_nm", "")} for sku in ordered_skus]

    if not changes.empty:
        for col in ["beta_anterior", "beta_actual", "delta_beta", "r2_actual", "n_observaciones_actual"]:
            if col in changes.columns:
                changes[col] = pd.to_numeric(changes[col], errors="coerce").map(to_number)
        changes["abs_delta"] = changes["delta_beta"].abs()
        changes = changes.sort_values(["SKU", "abs_delta"], ascending=[True, False])
        change_cols = [
            "SKU",
            "tipo_ventana",
            "periodo_anterior",
            "periodo_actual",
            "beta_anterior",
            "beta_actual",
            "delta_beta",
            "razon_cambio",
        ]
        changes_by_sku = records_by_key(changes, "SKU", change_cols[1:])
    else:
        changes_by_sku = {}

    data = {
        "skus": sku_items,
        "products": product_dim,
        "monthly": records_by_key(monthly, "prod_nbr", ["mes", "precio", "qty", "promocion", "descuento", "venta_neta"]),
        "betas": records_by_key(
            betas,
            "SKU",
            ["periodo_inicio", "periodo_fin", "tipo_ventana", "beta", "r2", "n_observaciones"],
        ),
        "changes": changes_by_sku,
    }

    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    args.output.write_text(html, encoding="utf-8")
    print("Dashboard Papel generado")
    print(f"SKUs: {len(sku_items)}")
    print(f"salida: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
