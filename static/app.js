/* ==========================================================================
   PolSci & IR MA AI Agent — Frontend Logic (Vanilla JS)
   ========================================================================== */

let allPrograms = [];
let activeTab = "matrix";

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderSimpleMarkdown(md) {
  if (!md) return "";
  const lines = md.split("\n");
  let html = "";
  let inList = false;

  for (let rawLine of lines) {
    let line = escapeHtml(rawLine.trim());
    // Bold & italic formatting
    line = line.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    line = line.replace(/\*(.+?)\*/g, "<em>$1</em>");

    if (line.startsWith("### ")) {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      html += `<h3>${line.slice(4)}</h3>`;
    } else if (line.startsWith("#### ")) {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      html += `<h4>${line.slice(5)}</h4>`;
    } else if (line.startsWith("- ")) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${line.slice(2)}</li>`;
    } else if (line === "---") {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      html += "<hr style='border:none;border-top:1px solid var(--border-hairline);margin:1rem 0;' />";
    } else if (line.length > 0) {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      html += `<p style="margin:0.45rem 0;">${line}</p>`;
    }
  }
  if (inList) html += "</ul>";
  return html;
}

function getDifficultyColor(score) {
  const s = Number(score) || 7.0;
  if (s >= 8.7) return "var(--diff-elite)";
  if (s >= 7.8) return "var(--diff-high)";
  if (s >= 7.0) return "var(--diff-strong)";
  return "var(--diff-moderate)";
}

function showBanner(msg, detail = "") {
  const banner = document.getElementById("agent-live-banner");
  const msgEl = document.getElementById("agent-live-message");
  const detEl = document.getElementById("agent-live-detail");
  if (!banner) return;
  banner.classList.add("visible");
  msgEl.textContent = msg;
  detEl.textContent = detail;
}

async function fetchStatus() {
  try {
    const resp = await fetch("/api/status");
    const data = await resp.json();
    const ollama = data.ollama || {};
    const dot = document.getElementById("ollama-status-dot");
    const txt = document.getElementById("ollama-status-text");
    const sel = document.getElementById("ollama-model-select");

    if (ollama.online) {
      dot.classList.add("online");
      txt.textContent = `Ollama Aktív (${ollama.active_model})`;
    } else {
      dot.classList.remove("online");
      txt.textContent = "Hibrid Mód (Ollama offline – Kész a helyi indításra)";
    }

    if (ollama.configured_model && sel) {
      const exists = Array.from(sel.options).some((o) => o.value === ollama.configured_model);
      if (exists) sel.value = ollama.configured_model;
    }

    const counter = document.getElementById("stats-counter-badge");
    if (counter) {
      counter.textContent = `Elemzett szakok: ${data.programs_count} (${data.hungarian_count} Magyar / ${data.european_count} Európai)`;
    }
  } catch (err) {
    console.error("Status error:", err);
  }
}

async function loadPrograms() {
  try {
    const resp = await fetch("/api/programs");
    allPrograms = await resp.json();
    applyFiltersAndRender();
    await fetchStatus();
  } catch (err) {
    console.error("Failed to load programs:", err);
  }
}

function getFilteredPrograms() {
  const searchVal = (document.getElementById("filter-search-input")?.value || "").toLowerCase().trim();
  const regionVal = document.getElementById("filter-region-select")?.value || "all";
  const catVal = document.getElementById("filter-category-select")?.value || "all";
  const sortVal = document.getElementById("filter-sort-select")?.value || "diff-desc";

  let list = allPrograms.filter((p) => {
    if (regionVal !== "all" && p.region_group !== regionVal) return false;
    if (catVal !== "all" && !(p.category || "").toLowerCase().includes(catVal.toLowerCase())) return false;
    if (searchVal) {
      const hay = [
        p.program_name,
        p.university,
        p.city,
        p.country,
        p.focus,
        p.admission_requirements,
        ...(p.courses || []),
      ]
        .join(" ")
        .toLowerCase();
      if (!hay.includes(searchVal)) return false;
    }
    return true;
  });

  list.sort((a, b) => {
    if (sortVal === "diff-desc") return (b.difficulty_score || 0) - (a.difficulty_score || 0);
    if (sortVal === "diff-asc") return (a.difficulty_score || 0) - (b.difficulty_score || 0);
    if (sortVal === "ects-asc") return (a.ects || 120) - (b.ects || 120);
    if (sortVal === "uni-asc") return (a.university || "").localeCompare(b.university || "", "hu");
    return 0;
  });

  return list;
}

function applyFiltersAndRender() {
  const filtered = getFilteredPrograms();
  renderMatrix(filtered);
  renderCards(filtered);
}

function renderMatrix(programs) {
  const tbody = document.getElementById("matrix-tbody");
  if (!tbody) return;

  if (!programs.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align:center; padding: 2.5rem; color: var(--text-muted);">
          Nincs a szűrőnek megfelelő mesterszak. Indíts egy élő webes keresést a fenti sávban!
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = programs
    .map((p) => {
      const isHu = p.region_group === "Magyarország";
      const regionBadge = isHu
        ? `<span class="badge badge-hu">Magyarország</span>`
        : `<span class="badge badge-eu">${escapeHtml(p.country)}</span>`;

      const coursesHtml = (p.courses || [])
        .slice(0, 7)
        .map((c) => `<li class="course-tag">${escapeHtml(c)}</li>`)
        .join("");

      const specsHtml =
        p.specializations && p.specializations.length
          ? `<div style="margin-top:0.4rem; font-size:0.78rem; color:var(--text-secondary);">
               <strong>Specializációk:</strong> ${escapeHtml(p.specializations.join(" • "))}
             </div>`
          : "";

      const bd = p.difficulty_breakdown || {};
      const diffColor = getDifficultyColor(p.difficulty_score);
      const pct = Math.min(100, Math.round((Number(p.difficulty_score) || 7) * 10));

      return `
        <tr>
          <td>
            <div class="uni-name">${escapeHtml(p.university)}</div>
            <div class="prog-title">${escapeHtml(p.program_name)} (${escapeHtml(p.degree_type)})</div>
            <div>
              ${regionBadge}
              <span class="badge badge-cat">${escapeHtml(p.category)}</span>
            </div>
            <div style="margin-top:0.45rem; display:flex; gap:0.5rem; align-items:center;">
              <a href="${escapeHtml(p.source_url)}" target="_blank" rel="noopener" class="source-link" style="font-size:0.76rem;">
                Forrás URL ↗
              </a>
              <button type="button" class="btn btn-sm btn-secondary btn-rescrape" data-url="${escapeHtml(p.source_url)}" style="padding:0.15rem 0.45rem; font-size:0.72rem;">
                Élő Frissítés
              </button>
              <button type="button" class="btn btn-sm btn-secondary btn-delete-prog" data-id="${escapeHtml(p.id)}" style="padding:0.15rem 0.45rem; font-size:0.72rem;" title="Eltávolítás">
                ✕
              </button>
            </div>
          </td>

          <td>
            <div class="mono-pill">${escapeHtml(p.duration)}</div>
            <div style="font-size:0.78rem; color:var(--text-muted); margin-top:0.2rem;">
              ${escapeHtml(p.ects)} ECTS kredit
            </div>
          </td>

          <td>
            <div style="font-weight:600;">${escapeHtml(p.city)}</div>
            <div style="font-size:0.8rem; color:var(--text-secondary);">${escapeHtml(p.country)}</div>
            <div style="font-size:0.76rem; color:var(--text-muted); margin-top:0.35rem;">
              <strong>Nyelv:</strong> ${escapeHtml(p.language)}
            </div>
            <div style="font-size:0.74rem; color:var(--text-muted); margin-top:0.2rem;">
              ${escapeHtml(p.tuition || "")}
            </div>
          </td>

          <td>
            <div style="font-size:0.84rem;">${escapeHtml(p.focus)}</div>
            ${specsHtml}
          </td>

          <td>
            <ul class="course-tags">${coursesHtml}</ul>
          </td>

          <td>
            <div style="font-size:0.82rem;">${escapeHtml(p.admission_requirements)}</div>
          </td>

          <td>
            <div class="diff-box">
              <div class="diff-score-header">
                <span class="diff-number" style="color:${diffColor};">${escapeHtml(p.difficulty_score)} / 10</span>
              </div>
              <div class="diff-bar-track">
                <div class="diff-bar-fill" style="width:${pct}%; background-color:${diffColor};"></div>
              </div>
              <div style="font-size:0.75rem; font-weight:600; color:var(--text-secondary);">
                ${escapeHtml(p.difficulty_label)}
              </div>
              <div class="diff-subgrid">
                <span>Felvételi: ${escapeHtml(bd.selectivity ?? "-")}</span>
                <span>Módszertan: ${escapeHtml(bd.methodology ?? "-")}</span>
                <span>Terhelés: ${escapeHtml(bd.workload ?? "-")}</span>
                <span>Nyelv/Akad.: ${escapeHtml(bd.language_academic ?? "-")}</span>
              </div>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");

  bindRowActionButtons();
}

function renderCards(programs) {
  const container = document.getElementById("cards-container");
  if (!container) return;

  if (!programs.length) {
    container.innerHTML = `<p style="color:var(--text-muted);">Nincs megjeleníthető képzés.</p>`;
    return;
  }

  container.innerHTML = programs
    .map((p) => {
      const diffColor = getDifficultyColor(p.difficulty_score);
      const bd = p.difficulty_breakdown || {};
      const coursesHtml = (p.courses || [])
        .map((c) => `<li class="course-tag">${escapeHtml(c)}</li>`)
        .join("");

      return `
        <article class="program-card">
          <div>
            <div class="card-top">
              <div>
                <div class="uni-name">${escapeHtml(p.university)}</div>
                <div class="prog-title">${escapeHtml(p.program_name)} (${escapeHtml(p.degree_type)})</div>
                <span class="badge ${p.region_group === "Magyarország" ? "badge-hu" : "badge-eu"}">
                  ${escapeHtml(p.city)}, ${escapeHtml(p.country)}
                </span>
                <span class="badge badge-cat">${escapeHtml(p.category)}</span>
              </div>
              <div style="text-align:right;">
                <div class="diff-number" style="color:${diffColor};">${escapeHtml(p.difficulty_score)}/10</div>
                <div style="font-size:0.72rem; color:var(--text-muted);">Nehézségi index</div>
              </div>
            </div>

            <div class="card-meta-grid" style="margin: 0.85rem 0;">
              <div class="meta-item">
                <span>Képzés hossza</span>
                <strong>${escapeHtml(p.duration)}</strong>
              </div>
              <div class="meta-item">
                <span>Oktatás nyelve</span>
                <strong>${escapeHtml(p.language)}</strong>
              </div>
              <div class="meta-item">
                <span>Kredit &amp; Tandíj</span>
                <strong>${escapeHtml(p.ects)} ECTS</strong>
              </div>
            </div>

            <div style="margin-bottom: 0.75rem;">
              <h3 class="card-section-title">Szakmai Fókusz</h3>
              <p style="margin:0; font-size:0.86rem;">${escapeHtml(p.focus)}</p>
            </div>

            <div style="margin-bottom: 0.75rem;">
              <h3 class="card-section-title">Kulcstárgyak a Tantervben</h3>
              <ul class="course-tags">${coursesHtml}</ul>
            </div>

            <div style="margin-bottom: 0.75rem;">
              <h3 class="card-section-title">Felvételi Követelmények</h3>
              <p style="margin:0; font-size:0.84rem; color:var(--text-secondary);">
                ${escapeHtml(p.admission_requirements)}
              </p>
            </div>

            <div>
              <h3 class="card-section-title">Képzés Nehézségének Indoklása (${escapeHtml(p.difficulty_label)})</h3>
              <p style="margin:0 0 0.4rem 0; font-size:0.82rem; color:var(--text-secondary);">
                ${escapeHtml(p.difficulty_rationale)}
              </p>
              <div class="diff-subgrid" style="background:var(--bg-canvas); padding:0.45rem 0.65rem; border-radius:4px;">
                <span>Szelektivitás: <strong>${escapeHtml(bd.selectivity ?? "-")}/10</strong></span>
                <span>Módszertani szigor: <strong>${escapeHtml(bd.methodology ?? "-")}/10</strong></span>
                <span>Féléves terhelés: <strong>${escapeHtml(bd.workload ?? "-")}/10</strong></span>
                <span>Nyelvi/Akadémiai: <strong>${escapeHtml(bd.language_academic ?? "-")}/10</strong></span>
              </div>
            </div>
          </div>

          <div class="card-footer">
            <span style="color:var(--text-muted); font-family:var(--font-mono); font-size:0.72rem;">
              ${escapeHtml(p.extraction_engine)}
            </span>
            <a href="${escapeHtml(p.source_url)}" target="_blank" rel="noopener" class="source-link">
              Hivatalos egyetemi oldal ↗
            </a>
          </div>
        </article>
      `;
    })
    .join("");
}

function bindRowActionButtons() {
  document.querySelectorAll(".btn-rescrape").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const url = btn.getAttribute("data-url");
      if (url) await runDirectUrlAnalysis(url);
    });
  });

  document.querySelectorAll(".btn-delete-prog").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-id");
      if (!id) return;
      await fetch(`/api/programs/${encodeURIComponent(id)}`, { method: "DELETE" });
      await loadPrograms();
    });
  });
}

async function runDirectUrlAnalysis(url) {
  const btn = document.getElementById("btn-run-live-search");
  if (btn) btn.disabled = true;
  showBanner(`Élő egyetemi oldal letöltése és 7-szempontos elemzése: ${url} ...`, "Tanterv és felvételi aloldalak vizsgálata");

  try {
    const resp = await fetch("/api/agent/analyze-url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, use_ollama: true }),
    });
    const data = await resp.json();
    if (data.ok && data.program) {
      showBanner(
        `Sikeres élő webelemzés: ${data.program.university} — ${data.program.program_name}`,
        `Nehézség: ${data.program.difficulty_score}/10 | Bejárt URL-ek: ${(data.program.crawled_urls || []).length} db`
      );
      await loadPrograms();
      await loadComparisonSynthesis();
    }
  } catch (err) {
    showBanner("Hiba történt az URL elemzése közben.", String(err));
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function runLiveSearchOrUrl(query) {
  const q = query.trim();
  if (!q) return;

  if (q.startsWith("http://") || q.startsWith("https://")) {
    await runDirectUrlAnalysis(q);
    return;
  }

  const btn = document.getElementById("btn-run-live-search");
  if (btn) btn.disabled = true;
  showBanner(`Élő webes keresés és egyetemi szakoldalak elemzése: "${q}" ...`, "DuckDuckGo + Egyetemi URL feloldó futtatása");

  try {
    const resp = await fetch("/api/agent/live-search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q, max_targets: 4, use_ollama: true }),
    });
    const data = await resp.json();
    if (data.ok) {
      const count = (data.analyzed_programs || []).length;
      showBanner(
        `Élő keresés kész: ${count} egyetemi mesterszak kinyerve és összehasonlítva.`,
        (data.targets_found || []).map((t) => t.title).slice(0, 3).join(" • ")
      );
      await loadPrograms();
      await loadComparisonSynthesis();
    }
  } catch (err) {
    showBanner("Hiba az élő keresés során.", String(err));
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function loadComparisonSynthesis() {
  const contentEl = document.getElementById("synthesis-content");
  const badgeEl = document.getElementById("synthesis-engine-badge");
  if (!contentEl) return;

  const filtered = getFilteredPrograms();
  const ids = filtered.map((p) => p.id);

  try {
    const resp = await fetch("/api/agent/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ program_ids: ids }),
    });
    const data = await resp.json();
    contentEl.innerHTML = renderSimpleMarkdown(data.synthesis_markdown);
    if (badgeEl && data.engine) {
      badgeEl.textContent = data.engine;
    }
  } catch (err) {
    contentEl.textContent = "Nem sikerült betölteni az összehasonlító szintézist.";
  }
}

async function sendChatQuestion(question) {
  const q = question.trim();
  if (!q) return;

  const box = document.getElementById("chat-messages-box");
  const input = document.getElementById("advisor-chat-input");
  const btn = document.getElementById("btn-send-chat");

  const userDiv = document.createElement("div");
  userDiv.className = "chat-bubble user";
  userDiv.textContent = q;
  box.appendChild(userDiv);

  const loadingDiv = document.createElement("div");
  loadingDiv.className = "chat-bubble agent";
  loadingDiv.textContent = "Ügynök elemzi a betöltött egyetemeket...";
  box.appendChild(loadingDiv);
  box.scrollTop = box.scrollHeight;

  if (input) input.value = "";
  if (btn) btn.disabled = true;

  try {
    const filtered = getFilteredPrograms();
    const resp = await fetch("/api/agent/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: q,
        program_ids: filtered.map((p) => p.id),
      }),
    });
    const data = await resp.json();
    loadingDiv.innerHTML = `
      <div class="markdown-body">${renderSimpleMarkdown(data.answer)}</div>
      <div style="margin-top:0.4rem; font-size:0.72rem; color:var(--text-muted); font-family:var(--font-mono);">
        Forrásmotor: ${escapeHtml(data.engine || "")}
      </div>
    `;
    box.scrollTop = box.scrollHeight;
  } catch (err) {
    loadingDiv.textContent = "Hiba történt a válasz generálásakor.";
  } finally {
    if (btn) btn.disabled = false;
  }
}

function setupEventListeners() {
  // View Tabs
  document.querySelectorAll(".view-tab").forEach((tabBtn) => {
    tabBtn.addEventListener("click", () => {
      document.querySelectorAll(".view-tab").forEach((b) => {
        b.classList.remove("active");
        b.setAttribute("aria-selected", "false");
      });
      tabBtn.classList.add("active");
      tabBtn.setAttribute("aria-selected", "true");

      activeTab = tabBtn.getAttribute("data-tab");
      document.getElementById("view-panel-matrix").style.display = activeTab === "matrix" ? "block" : "none";
      document.getElementById("view-panel-cards").style.display = activeTab === "cards" ? "block" : "none";
      document.getElementById("view-panel-advisor").style.display = activeTab === "advisor" ? "block" : "none";

      if (activeTab === "advisor") {
        loadComparisonSynthesis();
      }
    });
  });

  // Live search form
  const form = document.getElementById("live-agent-form");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const input = document.getElementById("agent-query-input");
      if (input && input.value) {
        await runLiveSearchOrUrl(input.value);
      }
    });
  }

  // Refresh comparison button
  const refreshBtn = document.getElementById("btn-refresh-comparison");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", async () => {
      document.getElementById("tab-btn-advisor")?.click();
      await loadComparisonSynthesis();
    });
  }

  // University preset chips
  document.querySelectorAll(".preset-chip[data-url]").forEach((chip) => {
    chip.addEventListener("click", async () => {
      const url = chip.getAttribute("data-url");
      const input = document.getElementById("agent-query-input");
      if (input) input.value = url;
      await runDirectUrlAnalysis(url);
    });
  });

  // Filters
  ["filter-search-input", "filter-region-select", "filter-category-select", "filter-sort-select"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", () => applyFiltersAndRender());
      el.addEventListener("change", () => applyFiltersAndRender());
    }
  });

  // Ollama Model Selection & Pull
  const modelSelect = document.getElementById("ollama-model-select");
  if (modelSelect) {
    modelSelect.addEventListener("change", async () => {
      await fetch("/api/ollama/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: modelSelect.value }),
      });
      await fetchStatus();
    });
  }

  const pullBtn = document.getElementById("btn-ollama-pull");
  if (pullBtn && modelSelect) {
    pullBtn.addEventListener("click", async () => {
      const chosen = modelSelect.value;
      pullBtn.disabled = true;
      showBanner(
        `Ollama modell konfigurálása / letöltése: ${chosen} ...`,
        "Ha az Ollama fut a Mac-en (ollama serve), a modell automatikusan aktiválódik."
      );
      try {
        await fetch("/api/ollama/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model: chosen }),
        });
        const resp = await fetch("/api/ollama/pull", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model: chosen }),
        });
        const res = await resp.json();
        if (res.ok) {
          showBanner(`Modell sikeresen aktiválva: ${chosen}`, "Helyi Ollama LLM készen áll!");
        } else {
          showBanner(
            `Modell beállítva (${chosen}). A helyi LLM futtatásához a Mac-eden indítsd el az Ollama alkalmazást!`,
            "Parancs Mac-en: ./run_mac.sh"
          );
        }
        await fetchStatus();
      } finally {
        pullBtn.disabled = false;
      }
    });
  }

  // Advisor Chat
  const chatForm = document.getElementById("advisor-chat-form");
  if (chatForm) {
    chatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const input = document.getElementById("advisor-chat-input");
      if (input && input.value) {
        await sendChatQuestion(input.value);
      }
    });
  }

  document.querySelectorAll(".chat-prompt-chip").forEach((chip) => {
    chip.addEventListener("click", async () => {
      const q = chip.getAttribute("data-q");
      if (q) await sendChatQuestion(q);
    });
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  setupEventListeners();
  await loadPrograms();
  await loadComparisonSynthesis();
});
