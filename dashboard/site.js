"use strict";

let data;
const content = document.getElementById("content");
const error = document.getElementById("error");
const config = {responsive: true, displaylogo: false, topojsonURL: "static/"};
const eraLabels = {both: "Both periods", old: "2023-2024", new: "Jan 2025-Mar 10, 2026"};
const specs = ["M0 + lagged outcome", "M2 + controls"];
const sensitivitySpec = "M0 excluding highest-rate state (TX)";
const csvSources = {
  monthly_arrests: "monthly_arrests",
  arrest_rate_panel: "arrest_rate_panel",
  locations: "arrests_state_locations",
  detention: "by_region",
  models: "arrest_regressions"
};

function node(tag, text, parent = content) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  parent.append(element);
  return element;
}

function select(label, options, value, changed) {
  const wrapper = node("label", label + " ");
  const element = node("select", undefined, wrapper);
  element.setAttribute("aria-label", label);
  options.forEach(([key, text]) => {
    const option = node("option", text, element);
    option.value = key;
  });
  element.value = value;
  element.addEventListener("change", () => changed(element.value));
  return element;
}

function chart(traces, layout = {}) {
  const element = node("div");
  element.className = "chart";
  Plotly.newPlot(element, traces, {margin: {t: 50}, ...layout}, config).catch(showError);
  return element;
}

function csv(rows) {
  if (!rows.length) return "";
  const keys = Object.keys(rows[0]);
  const escape = value => '"' + String(value ?? "").replaceAll('"', '""') + '"';
  return [keys, ...rows.map(row => keys.map(key => row[key]))]
    .map(row => row.map(escape).join(",")).join("\n");
}

function source(rows, sourceName) {
  const details = node("details");
  node("summary", "Data behind this chart", details);
  const link = node("a", "Download displayed data (CSV)", details);
  const url = URL.createObjectURL(new Blob([csv(rows)], {type: "text/csv;charset=utf-8"}));
  link.href = url;
  link.download = sourceName + ".csv";
  link.dataset.blobUrl = url;
  const original = node("a", " · Full source table", details);
  original.href = "results/" + sourceName + ".csv";
  node("p", `${rows.length.toLocaleString()} rows; preview shows up to 100.`, details);
  if (!rows.length) return;
  const table = node("table", undefined, details);
  const head = node("tr", undefined, node("thead", undefined, table));
  const keys = Object.keys(rows[0]);
  keys.forEach(key => node("th", key, head));
  const body = node("tbody", undefined, table);
  rows.slice(0, 100).forEach(row => {
    const tr = node("tr", undefined, body);
    keys.forEach(key => node("td", String(row[key] ?? ""), tr));
  });
}

function reset(title) {
  content.querySelectorAll("[data-blob-url]").forEach(link => URL.revokeObjectURL(link.dataset.blobUrl));
  content.querySelectorAll(".chart").forEach(element => Plotly.purge(element));
  content.replaceChildren();
  node("h2", title);
}

function trend(era = "both") {
  reset("Enforcement over time");
  select("Period", Object.entries(eraLabels), era, trend);
  node("p", "Comparison KPIs always show both windows. Arrest cutoff: March 10; detention cutoff: March 11, 2026.");
  const k = data.kpis;
  const tiles = node("div");
  tiles.className = "kpis";
  const metrics = [
    ["Arrests/day, old", k.old_per_day.toFixed(0)],
    ["Arrests/day, new", `${k.new_per_day.toFixed(0)} (+${k.pct_change.toFixed(0)}%)`],
    ["Convicted-criminal share", `${k.convicted_old.toFixed(1)}% → ${k.convicted_new.toFixed(1)}%`],
    ["Detention ADP", `${(k.adp_old / 1000).toFixed(1)}k → ${(k.adp_new / 1000).toFixed(1)}k`]
  ];
  metrics.forEach(([label, value]) => node("strong", value, node("div", label, tiles)));
  const rows = data.monthly_arrests.filter(row => era === "both" ||
    (era === "new" ? row.month >= "2025-01" : row.month < "2025-01"));
  chart([{type: "bar", x: rows.map(r => r.month), y: rows.map(r => r.arrests),
    marker: {color: rows.map(r => r.partial_month ? "#b0bac4" : "#1f77b4")}}],
  {title: "Monthly arrest records (grey = partial March)", yaxis: {title: "Arrest records"}});
  source(rows, csvSources.monthly_arrests);
}

function geography(year = "2025", region = "All", selectedState = null) {
  reset("Where apprehensions occurred");
  select("Year", ["2023", "2024", "2025"].map(y => [y, y]), year,
    value => geography(value, region, selectedState));
  const regions = ["All", ...new Set(data.arrest_rate_panel.map(r => r.region))].sort();
  select("Region", regions.map(r => [r, r]), region,
    value => geography(year, value));
  const rows = data.arrest_rate_panel.filter(r => r.year === Number(year) && (region === "All" || r.region === region));
  const options = rows.map(r => r.state).sort();
  const state = options.includes(selectedState) ? selectedState : options[0];
  select("State (or select on map)", options.map(s => [s, s]), state,
    value => geography(year, region, value));
  node("p", "50-state annual rates, not full-era totals. Color scale is fixed across years.");
  const map = chart([{type: "choropleth", locations: rows.map(r => r.state),
    z: rows.map(r => r.arr_rate), locationmode: "USA-states", colorscale: "Reds",
    zmin: 0, zmax: Math.max(...data.arrest_rate_panel.map(r => r.arr_rate)),
    colorbar: {title: "Arrests per 100k"}}],
  {geo: {scope: "usa"}, title: `Annual arrest records per 100k, ${year}`});
  map.on("plotly_click", event => geography(year, region, event.points[0].location));
  source(rows, csvSources.arrest_rate_panel);
  ["aor", "landmark"].forEach(dimension => {
    const joint = data.arrests_state_locations.filter(r =>
      r.year === Number(year) && r.state === data.states[state] && r.dimension === dimension)
      .sort((a, b) => b.arrests - a.arrests || a.location.localeCompare(b.location));
    node("h3", `${state}: ${dimension === "aor" ? "Areas of Responsibility" : "Landmarks"}`);
    node("p", "Joint source-record counts for this state/year. Top 15 shown; download includes all.");
    const top = joint.slice(0, 15).reverse();
    chart([{type: "bar", x: top.map(r => r.arrests), y: top.map(r => r.location), orientation: "h"}],
      {margin: {l: 270}, xaxis: {title: "Arrest records"}});
    source(joint, csvSources.locations);
  });
}

function detention(dimension = "Region", metric = "adp_per_100k", era = "both") {
  reset("Detention geography");
  const dims = {"Region": ["by_region", "region"], "CBSA class": ["by_cbsa_class", "cbsa_class"],
    "Operator": ["by_operator", "operator"]};
  select("Break down by", Object.keys(dims).map(d => [d, d]), dimension,
    value => detention(value, metric, era));
  select("Measure", [["adp_per_100k", "ADP per 100k residents"], ["adp", "Raw ADP"]], metric,
    value => detention(dimension, value, era));
  select("Period", Object.entries(eraLabels), era, value => detention(dimension, metric, value));
  node("p", "Facility location, not resident detention risk. Operator categories are inferred; their per-capita denominators are national, not local catchment populations.");
  const [table, key] = dims[dimension];
  const rows = data[table].filter(r => era === "both" || r.period.startsWith(era === "old" ? "Old" : "New"));
  const traces = [...new Set(rows.map(r => r.period))].map(period => {
    const subset = rows.filter(r => r.period === period);
    return {type: "bar", name: period, x: subset.map(r => r[key]), y: subset.map(r => r[metric])};
  });
  chart(traces, {barmode: "group", yaxis: {title: metric === "adp" ? "Average daily population" : "ADP per 100k"}});
  source(rows, table);
}

function models(outcome = "Real GDP growth (%)", specification = "Both", sensitivity = false) {
  reset("Model uncertainty");
  node("p", "0 of 64 arrest-related coefficients survive Benjamini-Hochberg q<.10. This is not proof of no relationship.");
  const outcomes = [...new Set(data.arrest_regressions.filter(r => r.era === "New").map(r => r.outcome))].sort();
  select("Outcome", outcomes.map(o => [o, o]), outcome, value => models(value, specification, sensitivity));
  select("Specification", ["Both", ...specs].map(s => [s, s]), specification,
    value => models(outcome, value, sensitivity));
  const label = node("label", " Include M0 excluding Texas ");
  const checkbox = node("input", undefined, label);
  checkbox.type = "checkbox"; checkbox.checked = sensitivity;
  checkbox.addEventListener("change", () => models(outcome, specification, checkbox.checked));
  const rows = data.arrest_regressions.filter(r => r.era === "New" && r.term === "arr_rate10" &&
    r.outcome === outcome && ((specs.includes(r.spec) && (specification === "Both" || r.spec === specification)) ||
      (sensitivity && r.spec === sensitivitySpec)));
  chart([{type: "scatter", mode: "markers", x: rows.map(r => r.coef), y: rows.map(r => r.spec),
    error_x: {type: "data", symmetric: false, array: rows.map(r => r.ci_high - r.coef),
      arrayminus: rows.map(r => r.coef - r.ci_low)}}],
  {margin: {l: 280}, title: outcome, xaxis: {zeroline: true, title:
    (outcome === "Real GDP growth (%)" || outcome === "Unemployment change (pp)" ?
      "Percentage points" : "Percent change") + " per +10 arrests per 100k"}});
  node("p", "HC3 robust, t-based pointwise 95% intervals; not multiplicity-adjusted. Texas exclusion applies to M0 only.");
  source(rows, csvSources.models);
}

function sql() {
  reset("Declarative SQL");
  node("p", "SQL describes the result; DuckDB plans execution. Pandas groupby/joins are also vectorized, set-oriented operations, not inherently row-by-row loops.");
  node("pre", data.sql);
  node("p", "Precomputed synthetic demonstration, executed with DuckDB during the site build. This static page does not run a SQL engine in your browser.");
  source(data.sql_result, "arrests_by_state");
}

function showError(exc) {
  error.textContent = `Unable to render this view: ${exc.message}. Source CSVs and full-size figures remain available.`;
}

fetch("data.json").then(response => {
  if (!response.ok) throw new Error(`Data request returned HTTP ${response.status}`);
  return response.json();
}).then(payload => {
  data = payload;
  const views = {trend, geography, detention, models, sql};
  document.querySelectorAll("nav button").forEach(button => button.addEventListener("click", () => {
    error.textContent = "";
    document.querySelectorAll("nav button").forEach(b => b.setAttribute("aria-pressed", String(b === button)));
    try { views[button.dataset.page](); } catch (exc) { showError(exc); }
  }));
  trend();
}).catch(showError);
