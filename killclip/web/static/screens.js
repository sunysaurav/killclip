// Trim, Short and Montage. Separate from app.js so each screen reads on its own.
import { $, api, fmt, state, go, waitForJob } from "./app.js";

const view = () => $("#view");

// ---- Trim: one moment, a filmstrip, two handles ---------------------------------------------
export async function screenTrim(pid, mid) {
  const s = await api.get(`/api/projects/${pid}/moments/${mid}/strip`);
  const m = s.moment;
  const span = s.t1 - s.t0;
  let tIn = m.clip_start, tOut = m.clip_end;

  view().innerHTML = `
    <div class="toolbar"><strong>Moment #${m.id}</strong>
      <span style="color:var(--dim)">${m.labels?.join(", ") || `${m.kills} kill${m.kills === 1 ? "" : "s"}`}</span>
      <span style="flex:1"></span>
      <button class="link" data-go="#/p/${pid}">back to moments</button></div>
    <div class="trim">
      <div>
        <div class="peek" id="peek"></div>
        <div class="readout"><span>in <b id="r-in"></b></span><span>out <b id="r-out"></b></span>
          <span>length <b id="r-len"></b></span><span>at <b id="r-at">–</b></span></div>
        <label>Colour <select id="grade">${state.server.grades.map((g) =>
          `<option${g === "natural" ? " selected" : ""}>${g}</option>`).join("")}</select></label>
        <p class="hint">"natural" tone-maps the HDR recording to SDR, which is what Shorts, Reels and TikTok expect
          and what a browser can show. "none" keeps the HDR look for YouTube.</p>
        <div class="row"><button class="primary" id="cut">Cut this clip</button>
          <button id="save">Save in/out</button><span class="hint" id="msg"></span></div>
      </div>
      <div><p class="hint">Drag the blue handles. Yellow marks are the kills the detector found.
        Hover anywhere to see that frame.</p>
        <div id="result"></div></div>
    </div>
    <div class="stripwrap"><div class="strip" id="strip">
      <img src="${s.url}" id="stripimg">
      <div class="shade" id="shade-l"></div><div class="shade" id="shade-r"></div>
      ${(m.kill_times || []).map((t) => `<div class="tick" style="left:${((t - s.t0) / span) * 100}%"></div>`).join("")}
      <div class="handle" id="h-in"></div><div class="handle" id="h-out"></div>
      <div class="cursor" id="cur"></div>
    </div></div>`;

  const strip = $("#strip"), img = $("#stripimg"), peek = $("#peek");
  img.onload = () => {
    strip.style.width = img.naturalWidth + "px";
    peek.style.backgroundImage = `url(${s.url})`;
    peek.style.backgroundSize = `${s.frames * 480}px 270px`;
    showAt(m.kill_times?.[0] ?? m.start);
    layout();
    $("#h-in").scrollIntoView({ inline: "center", block: "nearest" });
  };

  const tAt = (x) => s.t0 + Math.max(0, Math.min(1, x / strip.clientWidth)) * span;
  const xAt = (t) => ((t - s.t0) / span) * 100;
  function showAt(t) {
    const i = Math.max(0, Math.min(s.frames - 1, Math.floor(((t - s.t0) / span) * s.frames)));
    peek.style.backgroundPosition = `-${i * 480}px 0`;
    $("#r-at").textContent = t.toFixed(1) + "s";
    $("#cur").style.left = xAt(t) + "%";
  }
  function layout() {
    $("#h-in").style.left = xAt(tIn) + "%";
    $("#h-out").style.left = xAt(tOut) + "%";
    $("#shade-l").style.cssText = `left:0;width:${xAt(tIn)}%`;
    $("#shade-r").style.cssText = `left:${xAt(tOut)}%;right:0`;
    $("#r-in").textContent = fmt.time(tIn) + "." + Math.floor((tIn % 1) * 10);
    $("#r-out").textContent = fmt.time(tOut) + "." + Math.floor((tOut % 1) * 10);
    $("#r-len").textContent = (tOut - tIn).toFixed(1) + "s";
  }

  let drag = null;
  strip.addEventListener("pointerdown", (e) => {
    if (e.target.id === "h-in") drag = "in";
    else if (e.target.id === "h-out") drag = "out";
    else return;
    strip.setPointerCapture(e.pointerId);
  });
  strip.addEventListener("pointermove", (e) => {
    const x = e.clientX - strip.getBoundingClientRect().left;
    const t = Math.round(tAt(x) * 10) / 10;
    showAt(t);
    if (drag === "in") tIn = Math.min(t, tOut - 0.5);
    if (drag === "out") tOut = Math.max(t, tIn + 0.5);
    if (drag) layout();
  });
  strip.addEventListener("pointerup", () => { drag = null; });

  const save = () => api.put(`/api/projects/${pid}/moments/${mid}`, { clip_start: tIn, clip_end: tOut });
  $("#save").onclick = async () => { await save(); $("#msg").textContent = "saved"; };
  $("#cut").onclick = async () => {
    await save();
    $("#cut").disabled = true;
    $("#msg").textContent = "cutting…";
    const job = await api.post("/api/jobs", { kind: "cut", project: pid,
      args: { moments: [{ ...m, clip_start: tIn, clip_end: tOut }], grade: $("#grade").value } });
    const done = await waitForJob(job.id);
    $("#cut").disabled = false;
    if (done.state !== "done") { $("#msg").textContent = done.error || done.state; return; }
    const path = done.result.clips[0];
    $("#msg").textContent = "done";
    $("#result").innerHTML = `<video class="result" controls src="/media/file?path=${encodeURIComponent(path)}"></video>
      <p class="hint">${path}</p>
      <button data-go="#/short?clip=${encodeURIComponent(path)}">Make a short from this</button>`;
  };
}

// ---- Short: title, captions, a phone-shaped preview ------------------------------------------
export async function screenShort(clipFromUrl) {
  const clips = await api.get("/api/clips");
  if (!clips.length) {
    view().innerHTML = `<p class="empty">Cut a clip first: open a project, pick a moment, and cut it.</p>`;
    return;
  }
  const S = state.server.short;
  let cues = [];
  view().innerHTML = `
    <div class="composer">
      <div class="pane">
        <h2>Short</h2>
        <label>Clip <select id="clip">${clips.map((c) =>
          `<option value="${c.path}">${c.project} · ${c.name}</option>`).join("")}</select></label>
        <label>Title <input id="title" placeholder="He said he could drive"></label>
        <label>Platform <select id="platform">${Object.keys(S.safe).map((p) =>
          `<option${p === "reels" ? " selected" : ""}>${p}</option>`).join("")}</select></label>
        <label>Gameplay crop: <b id="aspect-v"></b>
          <input type="range" id="aspect" min="1.0" max="1.78" step="0.01" value="1.33"></label>
        <label>Background dim: <b id="dim-v"></b>
          <input type="range" id="dim" min="0" max="0.6" step="0.05" value="0.2"></label>
        <div class="row"><button id="read">Read the game's captions</button><span class="hint" id="cmsg"></span></div>
        <table class="cues" id="cues"></table>
        <div class="row"><button class="link" id="addcue">+ caption line</button></div>
        <div class="row"><button class="primary" id="render">Render short</button><span class="hint" id="msg"></span></div>
      </div>
      <div><canvas class="phone" id="phone" width="270" height="480"></canvas>
        <p class="hint">Shaded bands are where the platform draws its own buttons and text.</p></div>
      <div id="result"></div>
    </div>`;
  if (clipFromUrl) $("#clip").value = clipFromUrl;

  const still = new Image();
  const loadStill = () => { still.src = `/api/still?path=${encodeURIComponent($("#clip").value)}&t=3`; };
  still.onload = draw;
  loadStill();

  function draw() {
    const c = $("#phone"), g = c.getContext("2d");
    const k = c.width / S.w;                         // the preview is the real 1080x1920 layout, scaled
    const aspect = parseFloat($("#aspect").value);
    const dim = parseFloat($("#dim").value);
    $("#aspect-v").textContent = aspect >= 1.77 ? "full 16:9" : aspect.toFixed(2);
    $("#dim-v").textContent = dim.toFixed(2);
    const [top, bottom] = S.safe[$("#platform").value];
    const panelH = Math.round(S.w / aspect / 2) * 2, panelY = (S.h - panelH) / 2;
    g.fillStyle = "#000"; g.fillRect(0, 0, c.width, c.height);
    if (still.naturalWidth) {
      g.save(); g.filter = `blur(6px) brightness(${1 - dim})`;
      const sc = Math.max(c.width / still.naturalWidth, c.height / still.naturalHeight);
      g.drawImage(still, (c.width - still.naturalWidth * sc) / 2, (c.height - still.naturalHeight * sc) / 2,
        still.naturalWidth * sc, still.naturalHeight * sc);
      g.restore();
      const srcAspect = still.naturalWidth / still.naturalHeight;
      const sw = aspect < srcAspect ? still.naturalHeight * aspect : still.naturalWidth;
      g.drawImage(still, (still.naturalWidth - sw) / 2, 0, sw, still.naturalHeight,
        0, panelY * k, c.width, panelH * k);
    }
    const title = $("#title").value.toUpperCase();
    if (title) text(g, title, (top + (panelY - top) / 2) * k, 96 * k, "Anton, Impact, sans-serif", c.width * 0.86);
    const cap = cues[0]?.[2] || "Captions appear here";
    const capY = (panelY + panelH + (S.h - bottom - (panelY + panelH)) / 2) * k;
    text(g, cap, capY, 64 * k, "bold 1em Arial, sans-serif", c.width * 0.84);
    g.fillStyle = "rgba(240,180,60,.22)";
    g.fillRect(0, 0, c.width, top * k);
    g.fillRect(0, c.height - bottom * k, c.width, bottom * k);
  }
  function text(g, str, cy, size, family, maxW) {
    g.font = `${family.startsWith("bold") ? "bold " : ""}${size}px ${family.replace(/^bold 1em /, "")}`;
    const words = str.split(" "), lines = []; let cur = "";
    for (const w of words) {
      const t = (cur + " " + w).trim();
      if (g.measureText(t).width <= maxW || !cur) cur = t; else { lines.push(cur); cur = w; }
    }
    if (cur) lines.push(cur);
    const lh = size * 1.18; let y = cy - (lh * lines.length) / 2 + size * 0.85;
    g.textAlign = "center"; g.lineJoin = "round";
    for (const l of lines) {
      g.lineWidth = Math.max(2, size / 6); g.strokeStyle = "#000"; g.strokeText(l, 270 / 2, y);
      g.fillStyle = "#fff"; g.fillText(l, 270 / 2, y); y += lh;
    }
  }
  function renderCues() {
    $("#cues").innerHTML = cues.map((c, i) => `<tr>
      <td><input class="num" data-i="${i}" data-k="0" value="${c[0].toFixed(1)}"></td>
      <td><input class="num" data-i="${i}" data-k="1" value="${c[1].toFixed(1)}"></td>
      <td><input data-i="${i}" data-k="2" value="${c[2].replace(/"/g, "&quot;")}"></td>
      <td><button class="link" data-del="${i}">×</button></td></tr>`).join("");
  }

  for (const id of ["title", "platform", "aspect", "dim"]) $("#" + id).addEventListener("input", draw);
  $("#clip").addEventListener("change", () => { cues = []; renderCues(); loadStill(); });
  $("#cues").addEventListener("input", (e) => {
    const { i, k } = e.target.dataset;
    cues[i][k] = k === "2" ? e.target.value : parseFloat(e.target.value) || 0;
    if (i === "0") draw();
  });
  $("#cues").addEventListener("click", (e) => {
    if (e.target.dataset.del !== undefined) { cues.splice(+e.target.dataset.del, 1); renderCues(); draw(); }
  });
  $("#addcue").onclick = () => {
    const last = cues.at(-1)?.[1] ?? 0;
    cues.push([last, last + 2, ""]); renderCues();
  };
  $("#read").onclick = async () => {
    const clip = clips.find((c) => c.path === $("#clip").value);
    $("#cmsg").textContent = "reading…";
    const job = await api.post("/api/jobs", { kind: "captions", project: clip.project, args: { clip: clip.path } });
    const done = await waitForJob(job.id);
    if (done.state !== "done") { $("#cmsg").textContent = done.error || done.state; return; }
    cues = done.result.cues;
    $("#cmsg").textContent = `${cues.length} lines`;
    renderCues(); draw();
  };
  $("#render").onclick = async () => {
    const clip = clips.find((c) => c.path === $("#clip").value);
    const aspect = parseFloat($("#aspect").value);
    $("#render").disabled = true; $("#msg").textContent = "rendering…";
    const out = clip.path.replace(/\/clips\/([^/]+)\.mp4$/, `/shorts/$1-${Date.now() % 100000}.mp4`);
    const job = await api.post("/api/jobs", { kind: "short", project: clip.project, args: {
      clip: clip.path, title: $("#title").value, cues, platform: $("#platform").value,
      dim: parseFloat($("#dim").value), panel_aspect: aspect >= 1.77 ? null : aspect, out } });
    const done = await waitForJob(job.id);
    $("#render").disabled = false;
    if (done.state !== "done") { $("#msg").textContent = done.error || done.state; return; }
    $("#msg").textContent = "done";
    $("#result").innerHTML = `<video class="result" style="max-width:360px" controls
      src="/media/file?path=${encodeURIComponent(done.result.short)}"></video><p class="hint">${done.result.short}</p>`;
  };
  draw();
}

// ---- Montage: kept kills from several projects, on the beat ---------------------------------
export async function screenMontage() {
  const projects = state.server.projects.filter((p) => p.has_events);
  if (!projects.length) {
    view().innerHTML = `<p class="empty">Detect at least one project first.</p>`;
    return;
  }
  view().innerHTML = `
    <div class="mgrid">
      <div class="pane">
        <h2>Montage</h2>
        <div class="checks">${projects.map((p) =>
          `<label><input type="checkbox" value="${p.id}" checked> ${p.name} <span class="hint">${p.moments}</span></label>`).join("")}</div>
        <label>Music file <input id="music" placeholder="/path/to/track.mp3"></label>
        <div id="music-pick" class="hint"></div>
        <label>Style <select id="style">${state.server.styles.map((s) => `<option>${s}</option>`).join("")}</select></label>
        <label>Beats per kill <input id="bpk" type="number" min="1" max="8" value="4"></label>
        <label>Start this far into the track (seconds) <input id="mstart" type="number" min="0" step="1" placeholder="0"></label>
        <label>Streak gap (seconds) <input id="gap" type="number" min="0" step="1" value="6"></label>
        <label>Colour <select id="grade">${state.server.grades.map((g) => `<option>${g}</option>`).join("")}</select></label>
        <div class="row"><button id="plan">Plan</button>
          <button class="primary" id="render" disabled>Render</button><span class="hint" id="msg"></span></div>
      </div>
      <div id="out"><p class="hint">Plan first: it reads the track and shows which kill lands on which beat
        in a few seconds, before anything is encoded.</p></div>
    </div>`;

  const audio = await api.get("/api/browse");
  const findAudio = async (dir, depth = 0) => {
    const b = dir === audio.dir ? audio : await api.get(`/api/browse?path=${encodeURIComponent(dir)}`);
    const hits = b.entries.filter((e) => e.kind === "audio");
    if (depth < 2) for (const d of b.entries.filter((e) => e.kind === "dir").slice(0, 8)) hits.push(...await findAudio(d.path, depth + 1));
    return hits;
  };
  findAudio(audio.dir).then((hits) => {
    if (!hits.length) return;
    $("#music-pick").innerHTML = "Found: " + hits.slice(0, 6).map((h) =>
      `<button class="chip" data-music="${h.path}">${h.name}</button>`).join(" ");
    $("#music").value ||= hits[0].path;
  });
  $("#music-pick").addEventListener("click", (e) => { if (e.target.dataset.music) $("#music").value = e.target.dataset.music; });

  const body = () => ({
    projects: [...document.querySelectorAll(".checks input:checked")].map((i) => i.value),
    music: $("#music").value.trim(), style: $("#style").value,
    beats_per_kill: parseInt($("#bpk").value, 10) || 4,
    music_start: $("#mstart").value === "" ? null : parseFloat($("#mstart").value),
    streak_gap: parseFloat($("#gap").value) || 0,
  });
  $("#plan").onclick = async () => {
    $("#msg").textContent = "reading the track…";
    try {
      const p = await api.post("/api/plan", body());
      $("#msg").textContent = "";
      $("#render").disabled = false;
      $("#out").innerHTML = `
        <div class="stat"><div><b>${p.tempo}</b><span>BPM</span></div>
          <div><b>${p.used}/${p.kills}</b><span>kills fit</span></div>
          <div><b>${p.slots.length}</b><span>slots</span></div>
          <div><b>${p.length}s</b><span>long</span></div></div>
        ${p.unused ? `<p class="hint">${p.unused} kills did not fit the track. Fewer beats per kill, or a later start, fits more.</p>` : ""}
        <table class="slots"><tr><th>#</th><th>on the track</th><th>kills at</th><th>recording</th></tr>
        ${p.slots.map((s, i) => `<tr><td>${i + 1}</td><td>${fmt.time(s.start)}–${fmt.time(s.end)}</td>
          <td>${s.kills.map((k) => k.toFixed(1) + "s").join(", ")}</td><td>${s.video}</td></tr>`).join("")}</table>`;
    } catch (e) { $("#msg").textContent = e.message; }
  };
  $("#render").onclick = async () => {
    const b = body();
    $("#render").disabled = true; $("#msg").textContent = "rendering…";
    const job = await api.post("/api/jobs", { kind: "beatsync", project: null, args: {
      projects: b.projects, music: b.music, style: b.style, beats_per_kill: b.beats_per_kill,
      music_start: b.music_start, streak_gap: b.streak_gap, grade: $("#grade").value } });
    const done = await waitForJob(job.id);
    $("#render").disabled = false;
    if (done.state !== "done") { $("#msg").textContent = done.error || done.state; return; }
    $("#msg").textContent = `${done.result.kills} kills, ${done.result.slots} slots`;
    $("#out").insertAdjacentHTML("afterbegin", `<video class="result" controls
      src="/media/file?path=${encodeURIComponent(done.result.montage)}"></video><p class="hint">${done.result.montage}</p>`);
  };
}
