"use strict";

const MAX_MAP_MARKERS = 1800;
const elements = {
  courierCount: document.querySelector("#courier-count"),
  generateButton: document.querySelector("#generate-button"),
  restaurantQuery: document.querySelector("#restaurant-query"),
  restaurantOptions: document.querySelector("#restaurant-options"),
  radius: document.querySelector("#radius"),
  searchButton: document.querySelector("#search-button"),
  status: document.querySelector("#status"),
  resultCount: document.querySelector("#result-count"),
  resultsBody: document.querySelector("#results-body"),
  canvas: document.querySelector("#map-canvas"),
  mapLoading: document.querySelector("#map-loading"),
  zoomIn: document.querySelector("#zoom-in"),
  zoomOut: document.querySelector("#zoom-out"),
  resetMap: document.querySelector("#reset-map"),
};

const state = {
  map: null,
  couriers: [],
  matches: [],
  restaurant: null,
  radiusKm: 2,
  selectedEstablishmentId: null,
  zoom: 1,
  panX: 0,
  panY: 0,
  dragging: null,
  resizeObserver: null,
};

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Requisição falhou (${response.status}).`);
  }
  return payload;
}

function setStatus(message, isError = false) {
  elements.status.textContent = message;
  elements.status.classList.toggle("error", isError);
}

function canvasContext() {
  const rect = elements.canvas.getBoundingClientRect();
  const width = Math.max(1, Math.round(rect.width));
  const height = Math.max(1, Math.round(rect.height));
  const pixelRatio = window.devicePixelRatio || 1;
  if (
    elements.canvas.width !== Math.round(width * pixelRatio) ||
    elements.canvas.height !== Math.round(height * pixelRatio)
  ) {
    elements.canvas.width = Math.round(width * pixelRatio);
    elements.canvas.height = Math.round(height * pixelRatio);
  }
  const context = elements.canvas.getContext("2d");
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  return { context, width, height, pixelRatio };
}

function projectedBounds() {
  const [minLon, minLat, maxLon, maxLat] = state.map.bounds;
  const midLat = (minLat + maxLat) / 2;
  const lonFactor = 111.32 * Math.max(Math.abs(Math.cos((midLat * Math.PI) / 180)), 0.01);
  return {
    minX: minLon * lonFactor,
    minY: minLat * 110.574,
    maxX: maxLon * lonFactor,
    maxY: maxLat * 110.574,
    lonFactor,
  };
}

function mapProjection(width, height) {
  const bounds = projectedBounds();
  const margin = 24;
  const spanX = Math.max(bounds.maxX - bounds.minX, 0.1);
  const spanY = Math.max(bounds.maxY - bounds.minY, 0.1);
  const scale = Math.min((width - 2 * margin) / spanX, (height - 2 * margin) / spanY);
  return {
    ...bounds,
    scale,
    offsetX: (width - spanX * scale) / 2,
    offsetY: (height - spanY * scale) / 2,
  };
}

function toBasePoint(longitude, latitude, projection, height) {
  const x = longitude * projection.lonFactor;
  const y = latitude * 110.574;
  return [
    projection.offsetX + (x - projection.minX) * projection.scale,
    height - projection.offsetY - (y - projection.minY) * projection.scale,
  ];
}

function drawRoadLayer() {
  if (!state.map || !state.map.bounds) {
    return;
  }
  const { width, height, pixelRatio } = canvasContext();
  const buffer = document.createElement("canvas");
  buffer.width = Math.round(width * pixelRatio);
  buffer.height = Math.round(height * pixelRatio);
  const context = buffer.getContext("2d");
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  context.strokeStyle = "#c7d3df";
  context.lineWidth = 1;
  context.lineCap = "round";
  const projection = mapProjection(width, height);

  context.beginPath();
  for (const road of state.map.roads) {
    if (road.length < 2) {
      continue;
    }
    const [firstX, firstY] = toBasePoint(road[0][0], road[0][1], projection, height);
    context.moveTo(firstX, firstY);
    for (let i = 1; i < road.length; i += 1) {
      const [x, y] = toBasePoint(road[i][0], road[i][1], projection, height);
      context.lineTo(x, y);
    }
  }
  context.stroke();
  state.map.buffer = buffer;
  state.map.projection = projection;
  state.map.width = width;
  state.map.height = height;
  drawMap();
}

function transformedPoint(longitude, latitude) {
  const [baseX, baseY] = toBasePoint(
    longitude,
    latitude,
    state.map.projection,
    state.map.height,
  );
  const centerX = state.map.width / 2;
  const centerY = state.map.height / 2;
  return [
    centerX + (baseX - centerX) * state.zoom + state.panX,
    centerY + (baseY - centerY) * state.zoom + state.panY,
  ];
}

function markerSample(couriers, maximum) {
  if (couriers.length <= maximum) {
    return couriers;
  }
  const sampled = [];
  const step = couriers.length / maximum;
  for (let i = 0; i < maximum; i += 1) {
    sampled.push(couriers[Math.floor(i * step)]);
  }
  return sampled;
}

function drawMap() {
  if (!state.map || !state.map.buffer) {
    return;
  }
  const { context, width, height, pixelRatio } = canvasContext();
  context.clearRect(0, 0, width, height);
  const centerX = width / 2;
  const centerY = height / 2;
  const drawX = centerX * (1 - state.zoom) + state.panX;
  const drawY = centerY * (1 - state.zoom) + state.panY;
  context.drawImage(
    state.map.buffer,
    0,
    0,
    state.map.buffer.width,
    state.map.buffer.height,
    drawX,
    drawY,
    width * state.zoom,
    height * state.zoom,
  );

  const matchesById = new Map(state.matches.map((item) => [item.id, item]));
  const sampledCouriers = markerSample(state.couriers, MAX_MAP_MARKERS);
  const courierIds = new Set(sampledCouriers.map((item) => item.id));
  for (const match of state.matches) {
    if (!courierIds.has(match.id)) {
      sampledCouriers.push(match);
    }
  }
  for (const courier of sampledCouriers) {
    const [x, y] = transformedPoint(courier.longitude, courier.latitude);
    const isMatch = matchesById.has(courier.id);
    const radius = (isMatch ? 4 : 2.5) * Math.min(state.zoom, 2);
    context.beginPath();
    context.arc(x, y, radius, 0, Math.PI * 2);
    context.fillStyle = isMatch ? "#e04545" : "#738397";
    context.fill();
  }

  if (state.restaurant) {
    const [x, y] = transformedPoint(state.restaurant.longitude, state.restaurant.latitude);
    const radius = state.radiusKm * state.map.projection.scale * state.zoom;
    context.beginPath();
    context.arc(x, y, radius, 0, Math.PI * 2);
    context.fillStyle = "rgba(246, 180, 95, 0.12)";
    context.strokeStyle = "#e89642";
    context.lineWidth = 2;
    context.fill();
    context.stroke();
    context.beginPath();
    context.arc(x, y, 7, 0, Math.PI * 2);
    context.fillStyle = "#27a6c7";
    context.strokeStyle = "#145a78";
    context.lineWidth = 2;
    context.fill();
    context.stroke();
    context.font = "bold 12px Segoe UI, Arial, sans-serif";
    context.fillStyle = "#172b4d";
    context.fillText(state.restaurant.name.slice(0, 34), x + 11, y - 10);
  }
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
}

function setZoom(nextZoom, pointerX, pointerY) {
  if (!state.map) {
    return;
  }
  const { width, height } = elements.canvas.getBoundingClientRect();
  const targetZoom = Math.max(1, Math.min(16, nextZoom));
  const factor = targetZoom / state.zoom;
  const x = pointerX ?? width / 2;
  const y = pointerY ?? height / 2;
  state.panX = x - width / 2 - (x - width / 2 - state.panX) * factor;
  state.panY = y - height / 2 - (y - height / 2 - state.panY) * factor;
  state.zoom = targetZoom;
  drawMap();
}

async function loadMap() {
  try {
    const response = await fetch("/api/map");
    if (!response.ok) {
      throw new Error(`Não foi possível carregar o mapa (${response.status}).`);
    }
    state.map = await response.json();
    if (!state.map.bounds || state.map.roads.length === 0) {
      elements.mapLoading.textContent = "Grafo viário local indisponível.";
      return;
    }
    elements.mapLoading.hidden = true;
    drawRoadLayer();
  } catch (error) {
    elements.mapLoading.textContent = error.message;
    setStatus(error.message, true);
  }
}

async function loadHealth() {
  try {
    const health = await requestJson("/api/health");
    if (health.graph_error) {
      setStatus(health.graph_error, true);
      elements.generateButton.disabled = true;
      elements.mapLoading.textContent = "Grafo viário local indisponível.";
      return;
    }
    setStatus(
      `${health.restaurants.toLocaleString("pt-BR")} estabelecimentos locais carregados. Gere uma frota para iniciar.`,
    );
  } catch (error) {
    setStatus(error.message, true);
  }
}

let suggestionTimer = null;
async function updateSuggestions() {
  const query = elements.restaurantQuery.value.trim();
  elements.restaurantOptions.replaceChildren();
  state.selectedEstablishmentId = null;
  if (query.length < 2) {
    return;
  }
  try {
    const result = await requestJson(`/api/restaurants?q=${encodeURIComponent(query)}`);
    const fragment = document.createDocumentFragment();
    for (const restaurant of result.restaurants) {
      const option = document.createElement("option");
      option.value = restaurant.id;
      option.textContent = restaurant.label;
      fragment.append(option);
    }
    elements.restaurantOptions.append(fragment);
    if (result.restaurants.length === 0) {
      setStatus("Nenhum estabelecimento encontrado para essa busca.");
    }
  } catch (error) {
    setStatus(error.message, true);
  }
}

function renderResults(matches) {
  const fragment = document.createDocumentFragment();
  for (const item of matches) {
    const row = document.createElement("tr");
    for (const value of [
      item.id,
      item.distance_km.toFixed(3),
      item.eta_minutes.toFixed(1),
    ]) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    fragment.append(row);
  }
  elements.resultsBody.replaceChildren(fragment);
  elements.resultCount.textContent = matches.length
    ? `(${matches.length.toLocaleString("pt-BR")})`
    : "";
}

async function generateFleet() {
  const quantity = Number(elements.courierCount.value);
  if (!Number.isInteger(quantity) || quantity < 1 || quantity > 5000) {
    setStatus("Informe uma quantidade inteira entre 1 e 5.000.", true);
    return;
  }
  elements.generateButton.disabled = true;
  elements.searchButton.disabled = true;
  state.couriers = [];
  state.matches = [];
  state.restaurant = null;
  renderResults([]);
  drawMap();
  setStatus("Gerando frota e projetando posições nas vias locais...");
  try {
    const result = await requestJson("/api/fleet", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantity }),
    });
    state.couriers = result.couriers;
    setStatus(`Frota criada: ${result.count.toLocaleString("pt-BR")} entregadores. A busca está pronta.`);
    elements.searchButton.disabled = false;
    drawMap();
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    elements.generateButton.disabled = false;
  }
}

async function searchNearby() {
  if (!state.selectedEstablishmentId) {
    setStatus("Digite a busca e selecione um estabelecimento na lista.", true);
    return;
  }
  if (state.couriers.length === 0) {
    setStatus("Gere uma frota antes de realizar a busca.", true);
    return;
  }
  const radiusKm = Number(elements.radius.value);
  if (!Number.isFinite(radiusKm) || radiusKm < 0.2 || radiusKm > 10) {
    setStatus("O raio deve estar entre 0,2 e 10 km.", true);
    return;
  }
  elements.searchButton.disabled = true;
  setStatus("Buscando entregadores próximos...");
  try {
    const result = await requestJson("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        establishment_id: state.selectedEstablishmentId,
        radius_km: radiusKm,
      }),
    });
    state.restaurant = result.restaurant;
    state.radiusKm = result.radius_km;
    state.matches = result.matches;
    renderResults(result.matches);
    setStatus(
      `${result.matches.length.toLocaleString("pt-BR")} entregador(es) em ${radiusKm.toFixed(1)} km · ${result.candidate_count.toLocaleString("pt-BR")} candidatos · ${result.elapsed_ms.toFixed(2)} ms`,
    );
    drawMap();
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    elements.searchButton.disabled = false;
  }
}

elements.restaurantOptions.addEventListener("change", () => {
  state.selectedEstablishmentId = elements.restaurantOptions.value || null;
});
elements.restaurantOptions.addEventListener("dblclick", searchNearby);
elements.restaurantQuery.addEventListener("input", () => {
  window.clearTimeout(suggestionTimer);
  suggestionTimer = window.setTimeout(updateSuggestions, 180);
});
elements.generateButton.addEventListener("click", generateFleet);
elements.searchButton.addEventListener("click", searchNearby);
elements.zoomIn.addEventListener("click", () => setZoom(state.zoom * 1.25));
elements.zoomOut.addEventListener("click", () => setZoom(state.zoom / 1.25));
elements.resetMap.addEventListener("click", () => {
  state.zoom = 1;
  state.panX = 0;
  state.panY = 0;
  drawMap();
});
elements.canvas.addEventListener(
  "wheel",
  (event) => {
    event.preventDefault();
    const bounds = elements.canvas.getBoundingClientRect();
    setZoom(
      state.zoom * (event.deltaY < 0 ? 1.2 : 1 / 1.2),
      event.clientX - bounds.left,
      event.clientY - bounds.top,
    );
  },
  { passive: false },
);
elements.canvas.addEventListener("pointerdown", (event) => {
  state.dragging = { x: event.clientX, y: event.clientY };
  elements.canvas.setPointerCapture(event.pointerId);
  elements.canvas.classList.add("dragging");
});
elements.canvas.addEventListener("pointermove", (event) => {
  if (!state.dragging) {
    return;
  }
  state.panX += event.clientX - state.dragging.x;
  state.panY += event.clientY - state.dragging.y;
  state.dragging = { x: event.clientX, y: event.clientY };
  drawMap();
});
elements.canvas.addEventListener("pointerup", () => {
  state.dragging = null;
  elements.canvas.classList.remove("dragging");
});
elements.canvas.addEventListener("pointercancel", () => {
  state.dragging = null;
  elements.canvas.classList.remove("dragging");
});
state.resizeObserver = new ResizeObserver(() => {
  if (state.map) {
    drawRoadLayer();
  }
});
state.resizeObserver.observe(elements.canvas);

loadHealth();
loadMap();
