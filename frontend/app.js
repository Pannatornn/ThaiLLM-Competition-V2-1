const $ = (selector) => document.querySelector(selector);

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2500);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderEvidence(items = []) {
  if (!items.length) return `<div class="empty-panel">ไม่พบ evidence</div>`;
  return `<div class="evidence-grid">${items.map((e, i) => `
    <article class="evidence-card">
      <div class="evidence-top">Evidence ${i + 1} • ${escapeHtml(e.source)} หน้า ${escapeHtml(e.page)}</div>
      <p>${escapeHtml(e.text)}</p>
      <small>${escapeHtml(e.citation || "")}</small>
    </article>
  `).join("")}</div>`;
}

function renderResult(data) {
  return `
  <div class="glass-card answer-card">
    <div class="answer-status">${escapeHtml(data.status)} ${data.verification ? `• Confidence ${(data.verification.confidence * 100).toFixed(0)}%` : ""}</div>
    <h3>คำตอบ</h3>
    <div class="answer-text">${escapeHtml(data.answer)}</div>
    <div class="answer-meta">Latency: ${escapeHtml(data.latency_ms)} ms • Cache: ${escapeHtml(data.cache_hit)}</div>
    <h3>Evidence</h3>
    ${renderEvidence(data.evidence)}
  </div>`;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function refreshHealth() {
  try {
    const data = await fetch("/api/health").then(r => r.json());
    $("#healthText").textContent = data.ok ? "ThaiLLM Ready" : "API Ready / Model Check";
    $("#healthPill .dot").className = "dot good";
    $("#modelLabel").textContent = `Model: ${data.model}`;
    $("#evidenceCountLabel").textContent = `Evidence Units: ${data.evidence_units}`;
    $("#healthDetail").textContent = JSON.stringify(data.detail);
    $("#documentList").innerHTML = (data.programs || []).map(p => `<div>${escapeHtml(p.code)} — ${escapeHtml(p.file)}</div>`).join("");
  } catch (e) {
    $("#healthText").textContent = "Backend Offline";
    $("#healthPill .dot").className = "dot bad";
  }
}

$("#askForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const area = $("#answerArea");
  area.classList.remove("hidden");
  area.innerHTML = `<div class="glass-card">กำลังวิเคราะห์ด้วย ThaiLLM...</div>`;
  try {
    const data = await postJson("/api/ask", {
      question: $("#questionInput").value,
      program: $("#programSelect").value,
    });
    area.innerHTML = renderResult(data);
  } catch (e) {
    area.innerHTML = `<div class="glass-card error">${escapeHtml(e.message)}</div>`;
  }
});

document.querySelectorAll(".quick-chip").forEach(btn => {
  btn.addEventListener("click", () => {
    $("#questionInput").value = btn.dataset.question;
    $("#askButton").click();
  });
});

$("#compareButton").addEventListener("click", async () => {
  const area = $("#compareArea");
  area.classList.remove("hidden");
  area.innerHTML = `<div class="glass-card">กำลังเปรียบเทียบ...</div>`;
  try {
    const data = await postJson("/api/compare", {
      left: $("#compareLeft").value,
      right: $("#compareRight").value,
      focus: $("#compareFocus").value,
    });
    area.innerHTML = renderResult(data);
  } catch (e) {
    area.innerHTML = `<div class="glass-card error">${escapeHtml(e.message)}</div>`;
  }
});

$("#benchmarkButton").addEventListener("click", async () => {
  const area = $("#benchmarkArea");
  area.innerHTML = `<div class="glass-card">Running benchmark...</div>`;
  try {
    const data = await postJson("/api/benchmark", {});
    area.innerHTML = `<div class="glass-card answer-card"><h3>Benchmark Result</h3><h2>${data.passed}/${data.total}</h2><p>${(data.score * 100).toFixed(1)}%</p>${data.rows.map(r => `<div class="bench-row">#${r.id} ${r.passed ? "PASS" : "FAIL"} - ${escapeHtml(r.note)}</div>`).join("")}</div>`;
  } catch (e) {
    area.innerHTML = `<div class="glass-card error">${escapeHtml(e.message)}</div>`;
  }
});

document.querySelectorAll("[data-tab-target]").forEach(btn => {
  btn.addEventListener("click", () => {
    const target = btn.dataset.tabTarget;
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    document.querySelector(`#view-${target}`).classList.add("active");
    document.querySelectorAll(".nav-btn").forEach(v => v.classList.remove("active"));
    if (btn.classList.contains("nav-btn")) btn.classList.add("active");
  });
});

const canvas = $("#matrix");
if (canvas) {
  const ctx = canvas.getContext("2d");
  const chars = "01AI{}[]<>/\\λΣ";
  let width = canvas.width = innerWidth;
  let height = canvas.height = innerHeight;
  let cols = Math.floor(width / 20);
  let drops = Array(cols).fill(1);
  addEventListener("resize", () => {
    width = canvas.width = innerWidth;
    height = canvas.height = innerHeight;
    cols = Math.floor(width / 20);
    drops = Array(cols).fill(1);
  });
  setInterval(() => {
    ctx.fillStyle = "rgba(5,8,20,.18)";
    ctx.fillRect(0,0,width,height);
    ctx.fillStyle = "#38bdf8";
    ctx.font = "14px monospace";
    drops.forEach((y, i) => {
      ctx.fillText(chars[Math.floor(Math.random()*chars.length)], i*20, y*20);
      if (y*20 > height && Math.random() > .97) drops[i]=0;
      drops[i]++;
    });
  }, 45);
}

refreshHealth();
