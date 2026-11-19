// The whole UI. No build step: the server is the state, and the event stream says when to re-read it.
const $ = (sel, root = document) => root.querySelector(sel);
const view = $("#view");

const api = {
  async get(path) { return this.go("GET", path); },
  async post(path, body) { return this.go("POST", path, body); },
  async put(path, body) { return this.go("PUT", path, body); },
  async del(path) { return this.go("DELETE", path); },
  async go(method, path, body) {
    const r = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : null,
    });
    const out = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(out.error || `${r.status} ${path}`);
    return out;
  },
};

const state = { server: null, jobs: new Map(), openJob: null };

const fmt = {
  time(s) {
    if (s == null) return "";
    const m = Math.floor(s / 60), r = Math.floor(s % 60);
    return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
  },
  size(b) {
    if (!b) return "";
    const u = ["B", "KB", "MB", "GB"]; let i = 0;
    while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
    return `${b.toFixed(i ? 1 : 0)} ${u[i]}`;
  },
};

// ---- chrome -------------------------------------------------------------------------------
function renderCaps() {
  const c = state.server.caps;
  const bits = [
    `ffmpeg <b>${c.ffmpeg || "?"}</b>`,
    `encoder <b>${c.encoder || "none"}</b>`,
    c.ocr ? "ocr <b>ok</b>" : `<span class="bad">ocr missing</span>`,
    c.sound ? "sound <b>ok</b>" : `sound <b>off</b>`,
  ];
  $("#caps").innerHTML = bits.join("");
  if (c.trouble?.length) $("#caps").title = c.trouble.join("\n");
}

function crumbs(parts) {
  $("#crumbs").innerHTML = parts
    .map((p, i) => (i === parts.length - 1 ? `<span>${p.label}</span>` : `<a data-go="${p.href}">${p.label}</a>`))
    .join(" › ");
}

// ---- jobs panel ---------------------------------------------------------------------------
function renderJobs() {
  const live = [...state.jobs.values()].filter((j) => j.state === "queued" || j.state === "running");
  const recent = [...state.jobs.values()].slice(0, 6);
  const panel = $("#jobs");
  panel.hidden = recent.length === 0;
  $("#jobs-list").innerHTML = recent.map((j) => {
    const p = j.progress || {};
    const pct = p.total ? Math.min(100, (p.done / p.total) * 100) : (j.state === "running" ? 100 : 0);
    const detail = p.total ? `${p.stage} ${Math.round(p.done)}/${Math.round(p.total)}` : (p.stage || "");
    return `<div class="job" data-job="${j.id}">
      <div class="top"><span>${j.kind}${j.project ? " · " + j.project : ""}</span>
        <span class="state ${j.state}">${j.state}</span></div>
      <div class="l" style="color:var(--dim);font-size:12px">${detail}${j.error ? " — " + j.error : ""}</div>
      <div class="bar"><i style="width:${pct}%${p.total ? "" : ";opacity:.35"}"></i></div>
      ${j.state === "running" ? `<button class="link" data-cancel="${j.id}">cancel</button>` : ""}
    </div>`;
  }).join("");
  if (!live.length && state.openJob && !state.jobs.get(state.openJob)?.state?.match(/running|queued/)) {
    // leave the log visible after it finishes
  }
}

async function showJobLog(jid) {
  state.openJob = jid;
  const { log } = await api.get(`/api/jobs/${jid}`);
  $("#joblog").textContent = log.join("\n");
  $("#joblog").scrollTop = 1e9;
}

// ---- screens ------------------------------------------------------------------------------
async function screenLibrary() {
  crumbs([{ label: "Library" }]);
  view.innerHTML = "";
  view.append($("#tpl-library").content.cloneNode(true));
  renderProjects();
  await renderBrowse();
}

function renderProjects() {
  const list = state.server.projects;
  const el = $("#projects");
  if (!list.length) { el.innerHTML = `<p class="empty">No projects yet. Pick a recording on the left.</p>`; return; }
  el.innerHTML = list.map((p) => `
    <div class="card" data-project="${p.id}">
      ${p.poster ? `<img loading="lazy" src="/media/file?path=${encodeURIComponent(p.poster)}">` : `<img>`}
      <div class="meta"><b>${p.name}</b>
        <span>${p.game} · ${p.moments ? p.moments + " moments" : "not detected"}</span></div>
    </div>`).join("");
}

async function renderBrowse(path) {
  const b = await api.get("/api/browse" + (path ? `?path=${encodeURIComponent(path)}` : ""));
  $("#roots").innerHTML = b.roots.map((r) => `<button class="chip" data-dir="${r.path}">${r.name}</button>`).join("");
  $("#browse-path").textContent = b.dir;
  const up = b.parent ? `<li data-dir="${b.parent}"><span>..</span><span class="kind">up</span></li>` : "";
  $("#files").innerHTML = up + b.entries.map((e) => `
    <li data-${e.kind === "dir" ? "dir" : "video"}="${e.path}">
      <span>${e.name}</span><span class="kind">${e.kind === "dir" ? "" : fmt.size(e.size)}</span>
    </li>`).join("");
}

async function newProject(video) {
  const info = await api.get(`/api/probe?path=${encodeURIComponent(video)}`);
  view.innerHTML = "";
  view.append($("#tpl-newproject").content.cloneNode(true));
  $("#np-name").textContent = info.name;
  $("#np-facts").innerHTML = [
    `<span><b>${info.width}×${info.height}</b></span>`,
    `<span><b>${info.fps.toFixed(0)}</b> fps</span>`,
    `<span><b>${fmt.time(info.duration)}</b></span>`,
    `<span><b>${fmt.size(info.size)}</b></span>`,
    info.hdr ? `<span><b>HDR</b></span>` : "",
    `<span>${info.codec}</span>`,
  ].join("");
  $("#np-game").innerHTML = state.server.games
    .map((g) => `<option value="${g.game}"${g.needs_sound && !state.server.caps.sound ? " disabled" : ""}>
       ${g.game}${g.needs_sound && !state.server.caps.sound ? " (needs the sound extra)" : ""}</option>`).join("");
  const guess = state.server.games.find((g) => video.toLowerCase().includes(g.game.split("-")[0]));
  if (guess) $("#np-game").value = guess.game;
  $("#np-cancel").onclick = () => go("#/");
  $("#np-go").onclick = async () => {
    $("#np-go").disabled = true;
    $("#np-hint").textContent = "creating…";
    try {
      const p = await api.post("/api/projects", {
        video, game: $("#np-game").value, player: $("#np-player").value.trim(),
      });
      await api.post("/api/jobs", { kind: "detect", project: p.id, args: {} });
      await refresh();
      go(`#/p/${p.id}`);
    } catch (e) {
      $("#np-hint").textContent = e.message;
      $("#np-go").disabled = false;
    }
  };
}

async function screenProject(pid) {
  const { project, moments } = await api.get(`/api/projects/${pid}`);
  crumbs([{ label: "Library", href: "#/" }, { label: project.name }]);
  const kept = moments.filter((m) => m.keep).length;
  view.innerHTML = `
    <div class="toolbar">
      <strong>${project.name}</strong>
      <span style="color:var(--dim)">${project.game} · ${moments.length} moments · ${kept} kept</span>
      <span style="flex:1"></span>
      <button class="chip" data-redetect="${pid}">re-detect</button>
      <button class="primary" data-cut="${pid}">Cut kept clips</button>
    </div>
    ${moments.length ? `<div class="grid">${moments.map((m) => momentCard(pid, m)).join("")}</div>`
      : `<p class="empty">Nothing detected yet. If a job is running, its progress is bottom right.</p>`}`;
}

function momentCard(pid, m) {
  const label = m.labels?.length ? m.labels.join(", ")
    : `${m.kills} kill${m.kills === 1 ? "" : "s"}${m.victims?.length ? " · " + m.victims.join(", ") : ""}`;
  return `<div class="moment ${m.keep ? "" : "dropped"}" data-moment="${m.id}">
    <img loading="lazy" src="/media/thumb/${pid}/m${String(m.id).padStart(2, "0")}.jpg"
         onerror="this.style.visibility='hidden'">
    <div class="meta">
      <span class="t">#${m.id} · ${fmt.time(m.start)}${m.end > m.start ? "–" + fmt.time(m.end) : ""}</span>
      <span class="l">${label}</span>
      <span class="l">clip ${fmt.time(m.clip_start)}–${fmt.time(m.clip_end)}${m.score != null ? " · score " + m.score : ""}</span>
      <div class="row" style="margin-top:4px">
        <button class="chip" data-keep="${m.id}" data-pid="${pid}">${m.keep ? "drop" : "keep"}</button>
      </div>
    </div></div>`;
}

// ---- routing ------------------------------------------------------------------------------
function go(hash) { location.hash = hash; }

async function route() {
  const h = location.hash || "#/";
  try {
    const p = h.match(/^#\/p\/([^/]+)$/);
    if (p) return await screenProject(p[1]);
    return await screenLibrary();
  } catch (e) {
    view.innerHTML = `<p class="empty">${e.message}</p>`;
  }
}

async function refresh() {
  state.server = await api.get("/api/state");
  state.jobs = new Map(state.server.jobs.map((j) => [j.id, j]));
  renderCaps();
  renderJobs();
}

// ---- events -------------------------------------------------------------------------------
function listen() {
  const es = new EventSource("/api/events");
  es.addEventListener("job", (e) => {
    const j = JSON.parse(e.data);
    state.jobs.set(j.id, { ...state.jobs.get(j.id), ...j });
    renderJobs();
    if (j.state === "running" && !state.openJob) showJobLog(j.id);
  });
  es.addEventListener("progress", (e) => {
    const p = JSON.parse(e.data);
    const j = state.jobs.get(p.id);
    if (j) { j.progress = p; renderJobs(); }
  });
  es.addEventListener("log", (e) => {
    const { id, line } = JSON.parse(e.data);
    if (id !== state.openJob) return;
    const pre = $("#joblog");
    pre.textContent += (pre.textContent ? "\n" : "") + line;
    pre.scrollTop = 1e9;
  });
  es.addEventListener("project", async () => { await refresh(); route(); });
  es.onerror = () => {};   // EventSource reconnects on its own
}

document.addEventListener("click", async (e) => {
  const t = e.target.closest("[data-dir],[data-video],[data-project],[data-go],[data-cancel],[data-job],[data-keep],[data-cut],[data-redetect]");
  if (!t) return;
  if (t.dataset.dir) return renderBrowse(t.dataset.dir);
  if (t.dataset.video) return newProject(t.dataset.video);
  if (t.dataset.project) return go(`#/p/${t.dataset.project}`);
  if (t.dataset.go) return go(t.dataset.go);
  if (t.dataset.cancel) { await api.del(`/api/jobs/${t.dataset.cancel}`); return; }
  if (t.dataset.keep) {
    const card = t.closest(".moment");
    const keep = card.classList.contains("dropped");
    await api.put(`/api/projects/${t.dataset.pid}/moments/${t.dataset.keep}`, { keep });
    card.classList.toggle("dropped", !keep);
    t.textContent = keep ? "drop" : "keep";
    return;
  }
  if (t.dataset.redetect) {
    await api.post("/api/jobs", { kind: "detect", project: t.dataset.redetect, args: {} });
    return;
  }
  if (t.dataset.cut) {
    const pid = t.dataset.cut;
    const { moments } = await api.get(`/api/projects/${pid}`);
    const keep = moments.filter((m) => m.keep);
    if (!keep.length) return;
    await api.post("/api/jobs", { kind: "cut", project: pid, args: { moments: keep, edl: true } });
    return;
  }
  if (t.dataset.job) return showJobLog(t.dataset.job);
});

$("#jobs-close").onclick = () => { $("#jobs").hidden = true; };
window.addEventListener("hashchange", route);

await refresh();
listen();
await route();
