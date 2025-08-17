// frontend/static/js/timetable_slots.js
document.addEventListener("DOMContentLoaded", () => {
  const API = "http://localhost:8000/api/timetable-slots";
  const API_CFG = `${API}/config`;

  const $ = (sel) => document.querySelector(sel);

  const cfgSummary = $("#cfg-summary");
  const cfgTbody = $("#cfg-tbody");
  const cfgMsg = $("#cfg-msg");

  const selAddDay = $("#cfg-add-day");
  const selDelDay = $("#cfg-del-day");
  const selAddSession = $("#cfg-add-session");
  const selDelSession = $("#cfg-del-session");
  const inpAddSessionPeriods = $("#cfg-add-session-periods");
  const wrapPeriodCtrls = $("#cfg-period-controls");

  const DAY_ALL = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
  const SES_ALL = ["morning","afternoon","evening"];

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
    const daysHtml = `<div class="p-3 rounded-lg border">
      <div class="text-xs text-slate-500">Ngày</div>
      <div class="mt-1 font-medium">${cfg.days.length} ngày</div>
      <div class="mt-1 text-slate-600">${cfg.days.join(", ") || "—"}</div>
    </div>`;

    const sessionsHtml = `<div class="p-3 rounded-lg border">
      <div class="text-xs text-slate-500">Buổi</div>
      <div class="mt-1 font-medium">${cfg.sessions.length} buổi</div>
      <div class="mt-1 text-slate-600">${cfg.sessions.join(", ") || "—"}</div>
    </div>`;

    const periodsList = cfg.sessions.map(s => `${s}: ${cfg.periods_per_session[s] ?? 0}`).join(", ");
    const periodsHtml = `<div class="p-3 rounded-lg border">
      <div class="text-xs text-slate-500">Số tiết/buổi (max theo ngày)</div>
      <div class="mt-1 font-medium">${periodsList || "—"}</div>
      <div class="mt-1 text-slate-500">Tổng slot: ${cfg.total_slots}</div>
    </div>`;

    cfgSummary.innerHTML = daysHtml + sessionsHtml + periodsHtml;
  }

  function renderConfigTable(cfg) {
    // Mỗi ngày một dòng
    const rows = (cfg.days || []).map((day, idx) => {
      // Những buổi có slot ở ngày này
      const sessionsInDay = (cfg.sessions || [])
        .map(s => ({ s, cnt: (cfg.per_day_periods[s] && cfg.per_day_periods[s][day]) ? cfg.per_day_periods[s][day] : 0 }))
        .filter(x => x.cnt > 0);

      const sessionLines = sessionsInDay.length ? sessionsInDay.map(x => x.s) : ["—"];
      const periodLines = sessionsInDay.length
        ? sessionsInDay.map(x => (x.cnt ? Array.from({length:x.cnt}, (_,i)=>i+1).join(", ") : "—"))
        : ["—"];

      return `
        <tr class="border-b">
          <td class="px-3 py-2 align-top">${idx + 1}</td>
          <td class="px-3 py-2 align-top">${day}</td>
          <td class="px-3 py-2 align-top">${linesToCell(sessionLines)}</td>
          <td class="px-3 py-2 align-top font-mono">${linesToCell(periodLines)}</td>
        </tr>
      `;
    }).join("");

    cfgTbody.innerHTML = rows || `
      <tr><td colspan="4" class="px-3 py-3 text-slate-500">Chưa có cấu hình slot.</td></tr>
    `;
  }

  // function renderPeriodControls(cfg) {
  //   wrapPeriodCtrls.innerHTML = (cfg.sessions || []).map(s => {
  //     const v = cfg.periods_per_session[s] ?? 0;
  //     return `<div class="flex items-center gap-2 border rounded-lg p-2" data-session="${s}">
  //       <span class="w-24 text-slate-700">${s}</span>
  //       <button class="btn-per-minus px-2 py-1 border rounded">−</button>
  //       <input type="number" min="0" max="12" value="${v}" class="inp-per border rounded p-1 w-20 text-center"/>
  //       <button class="btn-per-plus px-2 py-1 border rounded">+</button>
  //       <button class="btn-per-apply px-3 py-1 rounded bg-slate-800 text-white">Áp dụng</button>
  //     </div>`;
  //   }).join("");
  // }

  function updateDeleteSelectors(cfg) {
    selDelDay.innerHTML = `<option value="">-- chọn --</option>` + (cfg.days || []).map(d => `<option>${d}</option>`).join("");
    selDelSession.innerHTML = `<option value="">-- chọn --</option>` + (cfg.sessions || []).map(s => `<option>${s}</option>`).join("");
  }

  async function reload() {
    const cfg = await fetchConfig();
    renderSummary(cfg);
    renderConfigTable(cfg);
    // renderPeriodControls(cfg);
    updateDeleteSelectors(cfg);
  }

  // --- Sự kiện: thêm/xoá ngày ---
  $("#btn-cfg-add-day").addEventListener("click", async () => {
    cfgMsg.textContent = "";
    const day = selAddDay.value;
    if (!day) {
      cfgMsg.textContent = "Chọn ngày cần thêm.";
      cfgMsg.className = "text-rose-600";
      return;
    }

    try {
      const res = await fetch(`${API}/config/add-day`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ day })
      });

      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || "Thêm ngày thất bại");

      if (data.created === 0 && data.skipped === "day_exists") {
        cfgMsg.textContent = "Ngày đã tồn tại.";
        cfgMsg.className = "text-orange-600";
      } else {
        await reload();
        cfgMsg.textContent = "Đã thêm ngày.";
        cfgMsg.className = "text-emerald-600";
      }

    } catch (e) {
      cfgMsg.textContent = e.message;
      cfgMsg.className = "text-rose-600";
    }
  });


  $("#btn-cfg-del-day").addEventListener("click", async () => {
    cfgMsg.textContent = "";
    const day = selDelDay.value;
    if (!day) {
      cfgMsg.textContent = "Chọn ngày cần xoá.";
      cfgMsg.className = "text-rose-600";
      return;
    }
    // if (!confirm(`Xoá toàn bộ slot của ${day}?`)) return;

    try {
      const res = await fetch(`${API}/config/day/${encodeURIComponent(day)}`, {
        method: "DELETE"
      });

      if (res.status === 404) {
        cfgMsg.textContent = "Ngày không tồn tại trong cấu hình hiện tại.";
        cfgMsg.className = "text-rose-600";
        $("#deleteSingleModal").modal("hide");
        return;
      }
      if (res.status === 400) {
        $("#deleteSingleModal").modal("hide");
        cfgMsg.textContent = "Các tiết học của ngày này đã được sắp xếp trong thời khóa biểu. Hãy xóa thời khóa biểu trước rồi cấu hình lại.";
        cfgMsg.className = "text-rose-600";
        
        return;
      }

      if (!res.ok) {
        const err = await res.json();
        $("#deleteSingleModal").modal("hide");
        throw new Error(err.detail || "Xoá ngày thất bại");
      }

      await reload();
      cfgMsg.textContent = "Đã xoá ngày.";
      cfgMsg.className = "text-emerald-600";
      $("#deleteSingleModal").modal("hide");
    } catch (e) {
      cfgMsg.textContent = e.message;
      cfgMsg.className = "text-rose-600";
    }
  });


  // --- Sự kiện: thêm/xoá buổi ---
  $("#btn-cfg-add-session").addEventListener("click", async () => {
    cfgMsg.textContent = "";
    const session = selAddSession.value;
    // const periods = parseInt(inpAddSessionPeriods.value || "0", 10);
    const periods = 5; // mặc định là 5
    if (!session) { cfgMsg.textContent = "Chọn buổi cần thêm."; cfgMsg.className="text-rose-600"; return; }
    // if (periods < 1) { cfgMsg.textContent = "Số tiết phải ≥ 1."; cfgMsg.className="text-rose-600"; return; }
    try {
      const res = await fetch(`${API}/config/add-session`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ session, periods })
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Thêm buổi thất bại");
      await reload();
      cfgMsg.textContent = "Đã thêm buổi.";
      cfgMsg.className = "text-emerald-600";
    } catch (e) { cfgMsg.textContent = e.message; cfgMsg.className = "text-rose-600"; }
  });

  $("#btn-cfg-del-session").addEventListener("click", async () => {
    cfgMsg.textContent = "";
    const session = selDelSession.value;
    if (!session) { cfgMsg.textContent = "Chọn buổi cần xoá."; cfgMsg.className="text-rose-600"; return; }
    if (!confirm(`Xoá toàn bộ slot của buổi ${session}?`)) return;
    try {
      const res = await fetch(`${API}/config/session/${encodeURIComponent(session)}`, { method: "DELETE" });
      if (!res.ok) throw new Error((await res.json()).detail || "Xoá buổi thất bại");
      await reload();
      cfgMsg.textContent = "Đã xoá buổi.";
      cfgMsg.className = "text-emerald-600";
    } catch (e) { cfgMsg.textContent = e.message; cfgMsg.className = "text-rose-600"; }
  });

  // --- Biến điều khiển per-day ---
const selDayPerDay = document.querySelector("#day-per-day");
const selSessionPerDay = document.querySelector("#session-per-day");
const inpPeriodsPerDay = document.querySelector("#periods-per-day");
const btnDayMinus = document.querySelector("#btn-day-minus");
const btnDayPlus = document.querySelector("#btn-day-plus");
const btnApplyPerDay = document.querySelector("#btn-apply-per-day");

// Nút +/- cho input per-day
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

// Áp dụng per-day
if (btnApplyPerDay) {
  btnApplyPerDay.addEventListener("click", async () => {
    cfgMsg.textContent = "";
    const day = selDayPerDay.value;
    const session = selSessionPerDay.value;
    const periods = parseInt(inpPeriodsPerDay.value || "0", 10);

    if (!day) { cfgMsg.textContent = "Chọn ngày."; cfgMsg.className="text-rose-600"; return; }
    if (!session) { cfgMsg.textContent = "Chọn buổi."; cfgMsg.className="text-rose-600"; return; }
    if (periods < 0 || periods > 12) { cfgMsg.textContent = "Số tiết 0..12."; cfgMsg.className="text-rose-600"; return; }

    try {
      const res = await fetch(`${API}/config/periods/day`, {
        method: "PUT",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ day, session, periods })
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Cập nhật số tiết (theo ngày) thất bại");
      await reload();
      cfgMsg.textContent = `Đã áp dụng: ${day} - ${session} → ${periods} tiết`;
      cfgMsg.className = "text-emerald-600";
    } catch (err) {
      cfgMsg.textContent = err.message;
      cfgMsg.className = "text-rose-600";
    }
  });
}
  // Khởi tạo
  reload();
});

function showDeleteModal(selectedDay) {
    // document.getElementById("deleteSubjectId").value = subjectId;
    document.getElementById("deleteMessage").textContent =
        `Bạn có chắc chắn muốn xóa ngày "${selectedDay}" không?`;
    $("#deleteSingleModal").modal("show");
}
