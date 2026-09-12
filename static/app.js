const SIMULATION_DELAY = 145;
const state = { indicators: [], index: 0, results: {}, profile: null, running: false, animation: null };
const $ = (id) => document.getElementById(id);

async function getJSON(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

function currentIndicator() { return state.indicators[state.index]; }

function renderProfile(profile) {
  state.profile = profile;
  $("fly-name").textContent = profile.name;
  $("fly-country").textContent = profile.country;
  $("fly-birthplace").textContent = profile.birthplace;
  $("fly-code").textContent = profile.code;
}

function renderIndicator() {
  const item = currentIndicator();
  if (!item) return;
  $("dimension").textContent = item.dimension.toUpperCase();
  $("indicator-id").textContent = `#${String(state.index + 1).padStart(2, "0")}`;
  $("indicator-title").textContent = item.title;
  $("question").textContent = item.question;
  $("description").textContent = item.description;
  $("stimulus-title").textContent = item.stimulus.title;
  $("stimulus-description").textContent = item.stimulus.description;
  $("stimulus-rule").textContent = item.stimulus.responseRule;
  $("progress-label").textContent = `Indicador ${state.index + 1} de ${state.indicators.length}`;
  $("progress-percent").textContent = `${Math.round(((state.index + 1) / state.indicators.length) * 100)}%`;
  $("progress-bar").style.width = `${((state.index + 1) / state.indicators.length) * 100}%`;
  $("next-button").disabled = !state.results[item.id] || state.index >= state.indicators.length - 1;
  resetResult();
  drawScene(item, 0.5, "idle");
}

function resetResult() {
  $("result-box").className = "result-box pending";
  $("result-label").textContent = "La mosca aún no ha respondido";
  $("result-detail").textContent = "Ejecuta la observación para iniciar la simulación.";
  $("step-label").textContent = "En espera";
  renderBars({ approach: 0.2, avoidance: 0.2, exploration: 0.2, dwell: 0.2 });
}

function renderBars(metrics) {
  const labels = [["approach", "acercamiento"], ["avoidance", "evitación"], ["exploration", "exploración"], ["dwell", "permanencia"]];
  $("bars").innerHTML = labels.map(([key, label]) => `<div class="bar-col"><div class="bar"><i style="height:${Math.max(4, (metrics[key] || 0) * 100)}%"></i></div><label>${label}</label></div>`).join("");
}

function drawScene(item, flyPosition, mode, step = 0) {
  const canvas = $("scene");
  const context = canvas.getContext("2d");
  const width = canvas.width; const height = canvas.height;
  context.clearRect(0, 0, width, height);
  const time = performance.now();
  const sky = context.createLinearGradient(0, 0, 0, height);
  sky.addColorStop(0, "#071b22"); sky.addColorStop(.55, "#123b3b"); sky.addColorStop(1, "#071c20"); context.fillStyle = sky; context.fillRect(0, 0, width, height);
  const horizon = 130;
  const floor = context.createLinearGradient(0, horizon, 0, height); floor.addColorStop(0, "#173f3c"); floor.addColorStop(1, "#06161c"); context.fillStyle = floor; context.fillRect(0, horizon, width, height - horizon);
  context.fillStyle = "rgba(121,220,191,.08)"; context.beginPath(); context.arc(width * .78, 105, 115 + Math.sin(time / 650) * 7, 0, Math.PI * 2); context.fill();
  context.strokeStyle = "rgba(111,220,190,.13)"; context.lineWidth = 1;
  for (let x = -width; x <= width * 2; x += 44) { context.beginPath(); context.moveTo(width / 2, horizon); context.lineTo(x, height); context.stroke(); }
  for (let y = horizon + 12; y < height; y += 22) { context.beginPath(); context.moveTo(0, y); context.lineTo(width, y); context.stroke(); }
  for (let i = 0; i < 20; i += 1) { const px = (i * 97 + Math.sin(time / 1200 + i) * 22) % width; const py = 30 + (i * 29) % 105; const alpha = .16 + (i % 3) * .08; context.fillStyle = `rgba(148,237,207,${alpha})`; context.beginPath(); context.arc(px, py, 1.3 + (i % 2), 0, Math.PI * 2); context.fill(); }
  const targetPosition = item.stimulus?.targetPosition || 0.80; const targetX = targetPosition * width; const targetY = 188; const pulse = 1 + Math.sin(time / 420) * .06;
  const glow = context.createRadialGradient(targetX, targetY, 5, targetX, targetY, 78); glow.addColorStop(0, "rgba(92,231,174,.34)"); glow.addColorStop(1, "rgba(92,231,174,0)"); context.fillStyle = glow; context.beginPath(); context.arc(targetX, targetY, 82, 0, Math.PI * 2); context.fill();
  context.fillStyle = "rgba(0,0,0,.35)"; context.beginPath(); context.ellipse(targetX, targetY + 42, 67, 13, 0, 0, Math.PI * 2); context.fill();
  context.fillStyle = "#1d5e55"; context.beginPath(); context.moveTo(targetX - 48, targetY + 28); context.lineTo(targetX - 37, targetY + 8); context.lineTo(targetX + 37, targetY + 8); context.lineTo(targetX + 48, targetY + 28); context.closePath(); context.fill(); context.strokeStyle = "rgba(148,237,207,.45)"; context.stroke();
  context.fillStyle = "rgba(92,231,174,.18)"; context.beginPath(); context.arc(targetX, targetY, 44 * pulse, 0, Math.PI * 2); context.fill(); context.strokeStyle = "rgba(115,239,195,.8)"; context.lineWidth = 1.5; context.setLineDash([5, 5]); context.beginPath(); context.arc(targetX, targetY, 35 * pulse, 0, Math.PI * 2); context.stroke(); context.setLineDash([]);
  drawStimulus(context, item.stimulus?.icon || "spark", targetX, targetY);
  context.fillStyle = "#a1e6d0"; context.font = "700 11px system-ui"; context.textAlign = "center"; context.fillText(item.stimulus?.title || "estímulo", targetX, targetY + 65);
  const x = 40 + flyPosition * (width - 80); const airborne = mode === "fly" || mode === "avoid"; const y = airborne ? 205 + Math.sin(time / 135) * 9 : 250 + Math.sin(time / 310) * 2; const scale = airborne ? .80 : .88;
  drawFly(context, x, y, scale, mode, time, step);
  context.fillStyle = "#98b9b1"; context.font = "600 11px system-ui"; context.textAlign = "left"; context.fillText(`estímulo: ${item.stimulus?.title || item.id}`, 18, 24);
  context.fillStyle = "#5f8d84"; context.font = "500 10px system-ui"; context.fillText(mode === "idle" ? "sensores calibrándose" : mode === "fly" ? "vuelo de reconocimiento" : mode === "land" ? "aterrizaje en curso" : mode === "walk" ? "camina y explora" : "respuesta de evitación", 18, 41);
}

function drawFly(context, x, y, scale, mode, time, step = 0) {
  context.save(); context.translate(x, y); context.scale(scale, scale); context.rotate(mode === "avoid" ? -.22 : mode === "approach" ? .14 : 0);
  const grounded = mode === "walk" || mode === "land" || mode === "idle"; const wingBeat = grounded ? .03 : Math.sin(time / 42) * .18; context.fillStyle = "rgba(2,10,13,.55)"; context.beginPath(); context.ellipse(0, 14, 24, 6, 0, 0, Math.PI * 2); context.fill();
  context.save(); context.rotate(-.28 + wingBeat); context.fillStyle = grounded ? "rgba(177,243,225,.18)" : "rgba(177,243,225,.32)"; context.strokeStyle = "rgba(194,255,234,.75)"; context.lineWidth = 1.5; context.beginPath(); context.ellipse(-5, -11, 18, 7, 0, 0, Math.PI * 2); context.fill(); context.stroke(); context.restore();
  context.save(); context.rotate(.28 - wingBeat); context.fillStyle = grounded ? "rgba(177,243,225,.14)" : "rgba(177,243,225,.22)"; context.strokeStyle = "rgba(194,255,234,.65)"; context.beginPath(); context.ellipse(5, 11, 18, 7, 0, 0, Math.PI * 2); context.fill(); context.stroke(); context.restore();
  context.strokeStyle = "#081214"; context.lineWidth = 2.3; context.lineCap = "round";
  const walkingPhase = step * 1.7; const legs = [[-8, -2, -19, 8, -24, 15], [-4, 3, -12, 14, -10, 22], [6, -2, 18, 8, 23, 15], [9, 3, 16, 14, 13, 22]];
  legs.forEach(([x1, y1, x2, y2, x3, y3], legIndex) => { const lift = grounded ? Math.max(0, Math.sin(walkingPhase + legIndex * Math.PI) * 3.5) : 0; context.beginPath(); context.moveTo(x1, y1); context.lineTo(x2, y2 - lift); context.lineTo(x3, y3 - lift); context.stroke(); });
  context.strokeStyle = "rgba(194,255,234,.45)"; context.lineWidth = 1.2; context.beginPath(); context.moveTo(-8, -4); context.lineTo(-16, -13); context.moveTo(-3, -5); context.lineTo(-7, -15); context.moveTo(8, -4); context.lineTo(16, -13); context.stroke();
  const body = context.createLinearGradient(-14, 0, 13, 0); body.addColorStop(0, "#09181b"); body.addColorStop(.55, "#55726c"); body.addColorStop(1, "#081214"); context.fillStyle = body; context.beginPath(); context.ellipse(0, 0, 14, 7, 0, 0, Math.PI * 2); context.fill();
  context.fillStyle = "#111d1f"; context.beginPath(); context.arc(13, -1, 6, 0, Math.PI * 2); context.fill(); context.fillStyle = "#b5ffe2"; context.beginPath(); context.arc(15, -3, 1.5, 0, Math.PI * 2); context.fill();
  context.restore();
}

function drawStimulus(context, icon, x, y) {
  context.save(); context.translate(x, y); context.strokeStyle = "#24564d"; context.fillStyle = "#d5eee4"; context.lineWidth = 2;
  if (icon === "banana") { context.strokeStyle = "#e5a51c"; context.lineWidth = 7; context.beginPath(); context.arc(-3, 0, 20, -.95, .75); context.stroke(); context.strokeStyle = "#f7d669"; context.lineWidth = 3; context.beginPath(); context.arc(-3, 0, 20, -.95, .75); context.stroke(); }
  else if (icon === "sugar") { context.fillStyle = "#fff3c3"; context.beginPath(); context.moveTo(-17,-10); context.lineTo(9,-16); context.lineTo(18,-5); context.lineTo(-8,2); context.closePath(); context.fill(); context.stroke(); context.fillStyle = "#fff9e8"; context.beginPath(); context.moveTo(-17,-10); context.lineTo(-8,2); context.lineTo(-8,19); context.lineTo(-17,7); context.closePath(); context.fill(); context.stroke(); context.beginPath(); context.moveTo(-8,2); context.lineTo(18,-5); context.lineTo(18,12); context.lineTo(-8,19); context.closePath(); context.fill(); context.stroke(); }
  else if (icon === "orange") { context.fillStyle = "#f5a53a"; context.beginPath(); context.arc(0,0,18,0,Math.PI*2); context.fill(); context.stroke(); context.strokeStyle = "rgba(255,239,185,.8)"; context.lineWidth = 1.5; for (let angle = 0; angle < Math.PI; angle += Math.PI / 4) { context.beginPath(); context.moveTo(0,0); context.lineTo(Math.cos(angle)*16,Math.sin(angle)*16); context.stroke(); } context.fillStyle="#70a55d"; context.beginPath(); context.ellipse(9,-17,7,3, -.35,0,Math.PI*2); context.fill(); context.stroke(); }
  else if (icon === "grape") { [[-9,-8], [5,-10], [-16,3], [0,2], [15,3], [-7,14], [8,14]].forEach(([gx,gy]) => { context.fillStyle = "#8f6bc5"; context.beginPath(); context.arc(gx,gy,7,0,Math.PI*2); context.fill(); context.stroke(); }); context.strokeStyle="#70a55d"; context.beginPath(); context.moveTo(0,-16); context.quadraticCurveTo(12,-25,19,-17); context.stroke(); }
  else if (icon === "yeast") { context.fillStyle = "#f2d7a1"; context.beginPath(); context.roundRect(-17,-15,34,31,7); context.fill(); context.stroke(); context.fillStyle="#8b6045"; context.fillRect(-13,-20,26,6); context.strokeRect(-13,-20,26,6); context.fillStyle="#fff3cf"; context.beginPath(); context.arc(-6,-2,3,0,Math.PI*2); context.arc(3,5,3,0,Math.PI*2); context.fill(); }
  else if (icon === "spoiled") { context.fillStyle = "#7f704a"; context.beginPath(); context.arc(0,1,20,0,Math.PI*2); context.fill(); context.stroke(); context.fillStyle="#443d2c"; [[-8,-6,4],[8,-9,3],[4,9,4],[-11,8,2]].forEach(([sx,sy,sr]) => { context.beginPath(); context.arc(sx,sy,sr,0,Math.PI*2); context.fill(); }); context.strokeStyle="#6e9b5b"; context.beginPath(); context.moveTo(0,-18); context.lineTo(5,-27); context.stroke(); }
  else if (icon === "meat") { context.fillStyle = "#e88370"; context.beginPath(); context.ellipse(0, 0, 22, 13, -.2, 0, Math.PI * 2); context.fill(); context.stroke(); context.fillStyle = "#fff0e8"; context.beginPath(); context.arc(10, -1, 5, 0, Math.PI * 2); context.fill(); context.stroke(); }
  else if (icon === "water") { context.fillStyle = "#72bdd0"; context.beginPath(); context.moveTo(0,-21); context.bezierCurveTo(18,-1,15,15,0,16); context.bezierCurveTo(-15,15,-18,-1,0,-21); context.fill(); context.stroke(); }
  else if (icon === "shelter") { context.beginPath(); context.moveTo(-24,14); context.lineTo(-24,-2); context.lineTo(0,-22); context.lineTo(24,-2); context.lineTo(24,14); context.closePath(); context.fill(); context.stroke(); context.fillStyle="#24564d"; context.fillRect(-6,2,12,12); }
  else if (icon === "group") { [-16,0,16].forEach((offset, index) => { context.fillStyle = index === 1 ? "#24564d" : "#71a69a"; context.beginPath(); context.arc(offset, 2, 8, 0, Math.PI * 2); context.fill(); context.stroke(); }); }
  else if (icon === "reward") { context.fillStyle = "#e5a51c"; context.beginPath(); context.arc(0,0,17,0,Math.PI*2); context.fill(); context.stroke(); context.fillStyle="#fff8dd"; context.font="700 20px system-ui"; context.textAlign="center"; context.textBaseline="middle"; context.fillText("+",0,1); }
  else { context.strokeStyle="#e5a51c"; context.lineWidth=3; context.beginPath(); context.moveTo(0,-22); context.lineTo(5,-5); context.lineTo(22,0); context.lineTo(5,5); context.lineTo(0,22); context.lineTo(-5,5); context.lineTo(-22,0); context.lineTo(-5,-5); context.closePath(); context.stroke(); }
  context.restore();
}

async function simulateCurrent() {
  if (state.running) return;
  const item = currentIndicator(); if (!item) return;
  state.running = true; $("run-button").disabled = true; $("run-button").textContent = "Observando…";
  try {
    const result = await getJSON("/api/simulate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ indicatorId: item.id, seed: Date.now() % 100000, steps: 36 }) });
    await animateResult(item, result);
    state.results[item.id] = result;
    updateCounts();
    $("next-button").disabled = state.index >= state.indicators.length - 1;
  } catch (error) { $("result-label").textContent = "No se pudo ejecutar la simulación"; $("result-detail").textContent = error.message; }
  state.running = false; $("run-button").disabled = false; $("run-button").innerHTML = 'Observar respuesta de la mosca <span>→</span>';
}

function animateResult(item, result) {
  return new Promise((resolve) => {
    const trace = result.trace; let index = 0;
    if (state.animation) clearTimeout(state.animation);
    const tick = () => {
      const sample = trace[index]; const progress = Math.min(1, (index + 1) / trace.length * 1.35); const targetPosition = item.stimulus?.targetPosition || .80; const desiredPosition = Math.max(.10, Math.min(targetPosition - .05, .16 + sample.approach * .84 - sample.avoidance * .12)); const position = Math.max(.06, Math.min(.94, .16 + (desiredPosition - .16) * progress));
      const mode = sample.avoidance > sample.approach + .12 ? "avoid" : index < 6 ? "fly" : index < 10 ? "land" : "walk";
      drawScene(item, position, mode, index); renderBars(sample); $("step-label").textContent = `paso ${sample.step} / ${trace.length}`;
      index += 1;
      if (index < trace.length) state.animation = setTimeout(tick, SIMULATION_DELAY); else { state.animation = null; showResult(result); resolve(); }
    }; tick();
  });
}

function showResult(result) {
  const names = { red: "Rojo", yellow: "Amarillo", green: "Verde" }; const box = $("result-box");
  box.className = `result-box ${result.answer}`; $("result-label").textContent = `${names[result.answer]} · ${result.meaning}`; $("result-detail").textContent = `${result.behavior?.interpretation || "conducta observada"} · confianza ${Math.round(result.confidence * 100)}% · backend ${result.backend}`; $("result-box").querySelector(".result-icon").textContent = result.answer === "green" ? "✓" : result.answer === "yellow" ? "!" : "×";
}

function updateCounts() {
  const counts = { green: 0, yellow: 0, red: 0 }; Object.values(state.results).forEach((result) => { counts[result.answer] += 1; });
  $("count-green").textContent = counts.green; $("count-yellow").textContent = counts.yellow; $("count-red").textContent = counts.red;
}

async function runAll() {
  if (state.running) return; state.running = true; $("run-all-button").disabled = true; $("run-all-button").textContent = "Ejecutando…";
  try { const response = await getJSON("/api/survey", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ seed: Date.now() % 100000 }) }); response.results.forEach((result) => { state.results[result.indicatorId] = result; }); updateCounts(); const current = response.results[state.index]; if (current) { renderBars(current.metrics); $("step-label").textContent = "Lectura completa"; showResult(current); } } catch (error) { $("result-detail").textContent = error.message; }
  state.running = false; $("run-all-button").disabled = false; $("run-all-button").textContent = "Correr todos los estímulos";
}

async function downloadReport() {
  if (state.running) return;
  const button = $("download-button");
  button.disabled = true;
  button.innerHTML = "Generando PDF…";
  try {
    const response = await fetch("/api/report", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile: state.profile, results: state.results }) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `flymap-${(state.profile?.name || "mosca").toLowerCase().replace(/[^a-z0-9]+/g, "-")}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    button.innerHTML = '<span>✓</span> PDF descargado';
    setTimeout(() => { button.innerHTML = '<span>↓</span> Descargar FlyMap PDF'; }, 2200);
  } catch (error) {
    button.textContent = "No se pudo generar el PDF";
    setTimeout(() => { button.innerHTML = '<span>↓</span> Descargar FlyMap PDF'; }, 2500);
  } finally {
    button.disabled = false;
  }
}

async function init() {
  try { const [indicatorResponse, profileResponse] = await Promise.all([getJSON("/api/indicators"), getJSON("/api/profile")]); state.indicators = indicatorResponse.indicators; renderProfile(profileResponse.profile); renderIndicator(); } catch (error) { document.body.dataset.connection = "offline"; }
  $("run-button").addEventListener("click", simulateCurrent);
  $("next-button").addEventListener("click", () => { if (state.index < state.indicators.length - 1) { state.index += 1; renderIndicator(); } });
  $("run-all-button").addEventListener("click", runAll);
  $("download-button").addEventListener("click", downloadReport);
}
init();
