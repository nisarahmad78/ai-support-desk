/* AI Support Desk dashboard - vanilla JS, talks to the /api endpoints. */
const $ = (sel) => document.querySelector(sel);

let currentTicket = null;

function badge(kind, value) {
  if (!value) return '<span class="badge badge-general">pending</span>';
  const label = value.replace("_", " ");
  return `<span class="badge badge-${value}">${label}</span>`;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function formatDate(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" }) +
    ", " + d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

/* ---------------- Stats ---------------- */
async function loadStats() {
  const res = await fetch("/api/stats");
  const s = await res.json();
  $("#stat-total").textContent = s.total_tickets;
  $("#stat-open").textContent = (s.by_status.open || 0) + (s.by_status.in_progress || 0);
  $("#stat-urgent").textContent = (s.by_priority.urgent || 0) + (s.by_priority.high || 0);
  const resolved = (s.by_status.resolved || 0) + (s.by_status.closed || 0);
  $("#stat-resolved").textContent = resolved;
  $("#stat-rate").textContent = s.total_tickets
    ? `${Math.round(s.resolution_rate * 100)}% resolution rate` : "";
  $("#stat-sentiment").textContent =
    s.average_sentiment_score === null ? "-" : s.average_sentiment_score.toFixed(2);

  const parts = [];
  for (const [k, v] of Object.entries(s.by_category)) parts.push(`<span class="chip">${k}: <strong>${v}</strong></span>`);
  for (const [k, v] of Object.entries(s.by_sentiment)) parts.push(`<span class="chip">sentiment ${k}: <strong>${v}</strong></span>`);
  $("#breakdown").innerHTML = parts.join("");
}

/* ---------------- Ticket list ---------------- */
async function loadTickets() {
  const params = new URLSearchParams();
  const status = $("#filter-status").value;
  const priority = $("#filter-priority").value;
  const category = $("#filter-category").value;
  const search = $("#filter-search").value.trim();
  if (status) params.set("status", status);
  if (priority) params.set("priority", priority);
  if (category) params.set("category", category);
  if (search) params.set("search", search);

  const res = await fetch("/api/tickets?" + params.toString());
  const tickets = await res.json();
  const tbody = $("#ticket-rows");
  if (!tickets.length) {
    tbody.innerHTML = '<tr><td colspan="9" class="empty">No tickets match these filters.</td></tr>';
    return;
  }
  tbody.innerHTML = tickets.map((t) => `
    <tr data-id="${t.id}">
      <td>#${t.id}</td>
      <td>
        <div class="ticket-title">${escapeHtml(t.title)}</div>
        <div class="ticket-preview">${escapeHtml(t.body.slice(0, 80))}...</div>
      </td>
      <td>
        <div class="customer-name">${escapeHtml(t.customer_name || "-")}</div>
        <div class="customer-email">${escapeHtml(t.customer_email)}</div>
      </td>
      <td>${badge("category", t.category)}</td>
      <td>${badge("priority", t.priority)}</td>
      <td>${badge("sentiment", t.sentiment)}</td>
      <td>${badge("status", t.status)}</td>
      <td>${escapeHtml(t.assignee || "-")}</td>
      <td>${formatDate(t.created_at)}</td>
    </tr>`).join("");

  tbody.querySelectorAll("tr[data-id]").forEach((row) => {
    row.addEventListener("click", () => openDrawer(Number(row.dataset.id)));
  });
}

async function refresh() {
  await Promise.all([loadStats(), loadTickets()]);
}

/* ---------------- Drawer ---------------- */
async function openDrawer(id) {
  const res = await fetch(`/api/tickets/${id}`);
  if (!res.ok) return;
  const t = await res.json();
  currentTicket = t;

  $("#drawer-id").textContent = `Ticket #${t.id} - ${formatDate(t.created_at)}`;
  $("#drawer-title").textContent = t.title;
  $("#drawer-meta").innerHTML =
    `<span><strong>${escapeHtml(t.customer_name || "")}</strong></span>` +
    `<span>${escapeHtml(t.customer_email)}</span>` +
    `<span>Status: ${escapeHtml(t.status.replace("_", " "))}</span>`;
  $("#drawer-body").textContent = t.body;
  $("#drawer-source").textContent = t.triage_source ? `engine: ${t.triage_source}` : "triage pending";
  $("#drawer-triage").innerHTML = `
    <div class="triage-cell"><div class="t-label">Category</div>${badge("category", t.category)}</div>
    <div class="triage-cell"><div class="t-label">Priority</div>${badge("priority", t.priority)}</div>
    <div class="triage-cell"><div class="t-label">Sentiment</div>${badge("sentiment", t.sentiment)}
      <div class="stat-note">score: ${t.sentiment_score ?? "-"}</div></div>`;
  $("#drawer-reply").value = t.final_reply || t.suggested_reply || "";
  $("#drawer-status").value = t.status;
  $("#drawer-assignee").value = t.assignee || "";
  $("#drawer-sent").textContent = t.final_reply ? "Reply sent - ticket resolved." : "";

  $("#drawer").classList.add("open");
  $("#drawer-overlay").classList.add("open");
}

function closeDrawer() {
  $("#drawer").classList.remove("open");
  $("#drawer-overlay").classList.remove("open");
  currentTicket = null;
}

async function saveDrawer(send) {
  if (!currentTicket) return;
  const id = currentTicket.id;
  if (send) {
    const reply = $("#drawer-reply").value.trim();
    if (!reply) { $("#drawer-sent").textContent = "Write a reply first."; return; }
    // Persist assignee edits first, then send the reply.
    await fetch(`/api/tickets/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ assignee: $("#drawer-assignee").value || null }),
    });
    const res = await fetch(`/api/tickets/${id}/reply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reply }),
    });
    if (res.ok) $("#drawer-sent").textContent = "Reply sent - ticket resolved.";
  } else {
    const res = await fetch(`/api/tickets/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: $("#drawer-status").value,
        assignee: $("#drawer-assignee").value || null,
        suggested_reply: $("#drawer-reply").value,
      }),
    });
    if (res.ok) $("#drawer-sent").textContent = "Changes saved.";
  }
  await refresh();
  await openDrawer(id);
}

/* ---------------- Submit form ---------------- */
async function submitTicket(event) {
  event.preventDefault();
  const result = $("#submit-result");
  result.classList.remove("error");
  result.textContent = "Submitting...";
  const res = await fetch("/api/tickets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      customer_name: $("#sub-name").value || null,
      customer_email: $("#sub-email").value,
      title: $("#sub-title").value,
      body: $("#sub-body").value,
    }),
  });
  if (!res.ok) {
    result.classList.add("error");
    result.textContent = "Submission failed - please check the fields and try again.";
    return;
  }
  const ticket = await res.json();
  result.textContent = `Thank you! Ticket #${ticket.id} created. Our team (and the AI triage) is on it.`;
  event.target.reset();
  // Give the background triage a moment, then refresh the dashboard data.
  setTimeout(refresh, 1200);
}

/* ---------------- Wiring ---------------- */
document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
    item.classList.add("active");
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    $("#view-" + item.dataset.view).classList.add("active");
    if (item.dataset.view === "dashboard") refresh();
  });
});

["filter-status", "filter-priority", "filter-category"].forEach((id) =>
  $("#" + id).addEventListener("change", loadTickets)
);
$("#filter-search").addEventListener("input", loadTickets);
$("#refresh-btn").addEventListener("click", refresh);
$("#drawer-close").addEventListener("click", closeDrawer);
$("#drawer-overlay").addEventListener("click", closeDrawer);
$("#save-btn").addEventListener("click", () => saveDrawer(false));
$("#send-btn").addEventListener("click", () => saveDrawer(true));
$("#retriage-btn").addEventListener("click", async () => {
  if (!currentTicket) return;
  await fetch(`/api/tickets/${currentTicket.id}/retriage`, { method: "POST" });
  await openDrawer(currentTicket.id);
  await refresh();
});
$("#submit-form").addEventListener("submit", submitTicket);

refresh();
