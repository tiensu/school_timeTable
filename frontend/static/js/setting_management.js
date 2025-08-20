// frontend/static/js/timetable_slots.js
document.addEventListener("DOMContentLoaded", () => {
  const API = "http://localhost:8002/api/timetable-slots";
  const API_CFG = `${API}/config`;
  let deleteObject = null;

  // Element helpers
  const $ = (sel) => document.querySelector(sel);

  // Global DOM elements
  const cfgSummary = $("#cfg-summary");
  const cfgTbody = $("#cfg-tbody");
  const cfgMsg = $("#cfg-msg");

  const selAddDay = $("#cfg-add-day");
  const selDelDay = $("#cfg-del-day");
  const selAddSession = $("#cfg-add-session");
  const selDelSession = $("#cfg-del-session");

  const inpAddSessionPeriods = $("#cfg-add-session-periods"); // currently unused
  const wrapPeriodCtrls = $("#cfg-period-controls"); // currently unused

  const selDayPerDay = $("#day-per-day");
  const selSessionPerDay = $("#session-per-day");
  const inpPeriodsPerDay = $("#periods-per-day");
  const btnDayMinus = $("#btn-day-minus");
  const btnDayPlus = $("#btn-day-plus");
  const btnApplyPerDay = $("#btn-apply-per-day");

  // Constants
  const DAY_ALL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const SES_ALL = ["morning", "afternoon", "evening"];

  // Utility: Fetch Config
  async function fetchConfig() {
    const res = await fetch(API_CFG);
    if (!res.ok) throw new Error("Không tải được cấu hình");
    return res.json();
  }

  function linesToCell(lines) {
    if (!lines || lines.length === 0) return "—";
    return lines.map(l => `<div class="leading-6">${l}</div>`).join("");
  }

  function renderSummary(cfg) {
    const daysHtml = buildSummaryBlock("Ngày", cfg.days.length, cfg.days.join(", "));
    const sessionsHtml = buildSummaryBlock("Buổi", cfg.sessions.length, cfg.sessions.join(", "));
    const periodsList = cfg.sessions.map(s => `${s}: ${cfg.periods_per_session[s] ?? 0}`).join(", ");
    const periodsHtml = `
      <div class="p-3 rounded-lg border">
        <div class="text-xs text-slate-500">Số tiết/buổi (max theo ngày)</div>
        <div class="mt-1 font-medium">${periodsList || "—"}</div>
        <div class="mt-1 text-slate-500">Tổng slot: ${cfg.total_slots}</div>
      </div>`;
    cfgSummary.innerHTML = daysHtml + sessionsHtml + periodsHtml;
  }

  function buildSummaryBlock(title, count, content) {
    return `
      <div class="p-3 rounded-lg border">
        <div class="text-xs text-slate-500">${title}</div>
        <div class="mt-1 font-medium">${count} ${title.toLowerCase()}</div>
        <div class="mt-1 text-slate-600">${content || "—"}</div>
      </div>`;
  }

  function renderConfigTable(cfg) {
    const rows = (cfg.days || []).map((day, idx) => {
      const sessionsInDay = (cfg.sessions || [])
        .map(s => ({ s, cnt: (cfg.per_day_periods[s] && cfg.per_day_periods[s][day]) ? cfg.per_day_periods[s][day] : 0 }))
        .filter(x => x.cnt > 0);

      const sessionLines = sessionsInDay.length ? sessionsInDay.map(x => x.s) : ["—"];
      const periodLines = sessionsInDay.length
        ? sessionsInDay.map(x => (x.cnt ? Array.from({ length: x.cnt }, (_, i) => i + 1).join(", ") : "—"))
        : ["—"];

      return `
        <tr class="border-b">
          <td class="px-3 py-2 align-top">${idx + 1}</td>
          <td class="px-3 py-2 align-top">${day}</td>
          <td class="px-3 py-2 align-top">${linesToCell(sessionLines)}</td>
          <td class="px-3 py-2 align-top font-mono">${linesToCell(periodLines)}</td>
        </tr>`;
    }).join("");

    cfgTbody.innerHTML = rows || `
      <tr><td colspan="4" class="px-3 py-3 text-slate-500">Chưa có cấu hình slot.</td></tr>`;
  }

  function updateDeleteSelectors(cfg) {
    selDelDay.innerHTML = `<option value="">-- chọn --</option>` + (cfg.days || []).map(d => `<option>${d}</option>`).join("");
    selDelSession.innerHTML = `<option value="">-- chọn --</option>` + (cfg.sessions || []).map(s => `<option>${s}</option>`).join("");
  }

  async function reload() {
    const cfg = await fetchConfig();
    renderSummary(cfg);
    renderConfigTable(cfg);
    updateDeleteSelectors(cfg);
  }

  function setupEventListeners() {
    $("#btn-cfg-add-day").addEventListener("click", handleAddDay);
    // $("#btn-cfg-del-day").addEventListener("click", performDeleteDay);
    $("#btn-cfg-add-session").addEventListener("click", handleAddSession);
    $("#btn-cfg-del-session").addEventListener("click", handleDeleteSession);
    setupPerDayControls();
  }

  async function handleAddDay() {
    cfgMsg.textContent = "";
    const day = selAddDay.value;
    if (!day) return showMsg("Chọn ngày cần thêm.", "rose");

    try {
      const res = await fetch(`${API}/config/add-day`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ day })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Thêm ngày thất bại");

      if (data.created === 0 && data.skipped === "day_exists") {
        showMsg("Ngày đã tồn tại.", "orange");
      } else {
        await reload();
        showMsg("Đã thêm ngày.", "emerald");
      }
    } catch (e) {
      showMsg(e.message, "rose");
    }
  }

  async function handleAddSession() {
    cfgMsg.textContent = "";
    const session = selAddSession.value;
    const periods = 5; // default
    if (!session) return showMsg("Chọn buổi cần thêm.", "rose");

    try {
      const res = await fetch(`${API}/config/add-session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session, periods })
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Thêm buổi thất bại");

      await reload();
      showMsg("Đã thêm buổi.", "emerald");
    } catch (e) {
      showMsg(e.message, "rose");
    }
  }

  async function handleDeleteSession() {
    cfgMsg.textContent = "";
    const session = selDelSession.value;
    if (!session) return showMsg("Chọn buổi cần xoá.", "rose");
    if (!confirm(`Xoá toàn bộ slot của buổi ${session}?`)) return;

    try {
      const res = await fetch(`${API}/config/session/${encodeURIComponent(session)}`, { method: "DELETE" });
      if (!res.ok) throw new Error((await res.json()).detail || "Xoá buổi thất bại");

      await reload();
      showMsg("Đã xoá buổi.", "emerald");
    } catch (e) {
      showMsg(e.message, "rose");
    }
  }

  function handleDeleteSession(){
    const selDelSession = $("#cfg-del-session");
    const session = selDelSession.value;
    if (!session) {
      showToast("Chọn buổi cần xoá.", "danger");
      return;
    }
    message = `Bạn có chắc chắn muốn xoá buổi <strong>${session}</strong>?<br>`;
    showDeleteDialog(message);
  }

  async function handleApplyPerDay() {
    cfgMsg.textContent = "";
    const day = selDayPerDay.value;
    const session = selSessionPerDay.value;
    const periods = parseInt(inpPeriodsPerDay.value || "0", 10);

    if (!day || !session || periods < 0 || periods > 12)
      return showMsg("Dữ liệu không hợp lệ (chọn ngày, buổi, số tiết 0..12)", "rose");

    try {
      const res = await fetch(`${API}/config/periods/day`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ day, session, periods })
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Cập nhật số tiết thất bại");

      await reload();
      showMsg(`Đã áp dụng: ${day} - ${session} → ${periods} tiết`, "emerald");
    } catch (err) {
      showMsg(err.message, "rose");
    }
  }

  function setupPerDayControls() {
    if (btnDayMinus && btnDayPlus) {
      btnDayMinus.addEventListener("click", () => {
        const v = Math.max(0, parseInt(inpPeriodsPerDay.value || "0", 10) - 1);
        inpPeriodsPerDay.value = v;
      });
      btnDayPlus.addEventListener("click", () => {
        const v = Math.min(12, parseInt(inpPeriodsPerDay.value || "0", 10) + 1);
        inpPeriodsPerDay.value = v;
      });
    }

    if (btnApplyPerDay) {
      btnApplyPerDay.addEventListener("click", handleApplyPerDay);
    }
  }

  // Init
  setupEventListeners();
  reload();
});

function handleDeleteDay() {
  const selDelDay = $("#cfg-del-day").val();
  if (!selDelDay) {
    showToast("Chọn ngày cần xoá.", "danger");
    return;
  }
  message = `Bạn có chắc chắn muốn xoá ngày <strong>${selDelDay}</strong>?<br>`;
  $("#btn-cfg-del-day").off("click", performDeleteDay);
  $("#btn-cfg-del-day").on("click", performDeleteDay);
  showDeleteDialog(message);
}

async function performDeleteDay() {
  $("#confirmDeleteModal").modal("hide");
    const BASE_API = "http://localhost:8002/api/timetable-slots";
    const selDelDay = $("#cfg-del-day").val();
    const delAPI = `${BASE_API}/config/day/${encodeURIComponent(selDelDay)}`;
    console.log('API: ', delAPI);
    const res = await fetch(delAPI, { method: "DELETE" });

    if (res.status === 404) return showToast("Ngày không tồn tại trong cấu hình hiện tại.", "warning");
    if (res.status === 400) {
      showToast("Các tiết học của ngày này đã được sắp xếp trong thời khóa biểu. Hãy xóa thời khóa biểu trước rồi cấu hình lại.", "warning");
      return;
    }

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Xoá ngày thất bại");
    }

    await reload();
    showToast("Đã xoá ngày.", "success");
}

function showDeleteDialog(message) {
  document.getElementById("deleteMessage").innerHTML = message;
  $("#confirmDeleteModal").modal("show");
}

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast-message bg-${type}`;

  // Màu nền theo loại thông báo
  let bgColor = "#28a745"; // success
  let fontColor = "#000";
  if (type === "danger"){
    bgColor = "#dc3545";
    fontColor = "#fff";
  } else if (type === "warning") {
    bgColor = "#ffc107";
  }

  toast.innerHTML = `
    <div style="
      min-width: 200px;
      margin-top: 10px;
      padding: 12px 20px;
      color: ${fontColor};
      border-radius: 10px;
      font-size: 16px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.2);
      background-color: ${bgColor};
      animation: slideIn 0.3s ease;
    ">
      ${message}
    </div>
  `;
  const container = document.getElementById("toastContainer");
  container.appendChild(toast);

  // Tự xoá sau 3 giây
  setTimeout(() => {
    toast.remove();
  }, 3000);
}

$(document).ready(function () {
    // Home functionality
    const homeBtn = document.getElementById("btnHome");
    if (homeBtn) {
        homeBtn.addEventListener("click", () => {
            window.location.href = "/home.html"; // Redirect to home page
        });
    }

    // Logout functionality
    const logoutBtn = document.getElementById("btnLogout");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", () => {
            localStorage.removeItem("access_token");
            localStorage.removeItem("username");
            localStorage.removeItem("role");
            localStorage.removeItem("menu");
            window.location.href = "/login.html"; // Redirect to login page
        });
    }
});