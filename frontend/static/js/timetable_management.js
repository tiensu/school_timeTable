// ====== CONFIG: Update these endpoints if needed ======
const API_CLASSES = "http://localhost:8002/api/timetables/classes";
const API_TEACHERS = "http://localhost:8002/api/timetables/teachers";
const API_TIMETABLE = "http://localhost:8002/api/timetables/view";
// ======================================================

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const SESSION_LABELS = { morning: "Sáng", afternoon: "Chiều" };
const PERIODS_PER_SESSION = 5; // khớp seed của bạn
const SUBJECT_COLORS = [
    "bg-emerald-100 text-emerald-800",
    "bg-blue-100 text-blue-800",
    "bg-amber-100 text-amber-800",
    "bg-violet-100 text-violet-800",
    "bg-rose-100 text-rose-800",
    "bg-cyan-100 text-cyan-800",
    "bg-lime-100 text-lime-800",
    "bg-fuchsia-100 text-fuchsia-800",
    "bg-indigo-100 text-indigo-800",
    "bg-teal-100 text-teal-800",
];

// Global state
let classes = [];
let teachers = [];
let timetables = []; // normalized
let subjectColorMap = new Map();
let viewMode = "pretty"; // "pretty" | "compactGrade"

function subjectLabel(code, name) {
    return name || code; // có tên thì dùng tên, không thì fallback mã
}

function colorForSubjectKey(code) {
    // dùng code làm key để giữ màu ổn định
    if (!subjectColorMap.has(code)) {
        const idx = subjectColorMap.size % SUBJECT_COLORS.length;
        subjectColorMap.set(code, SUBJECT_COLORS[idx]);
    }
    return subjectColorMap.get(code);
}

function gridKey(day, session, period) {
    return `${day}-${session}-${period}`;
}

function normalizeItem(item) {
    // Hỗ trợ 2 dạng: có slot lồng hoặc phẳng
    const slot = item.slot || {
        day_of_week: item.day_of_week,
        session: item.session,
        period: item.period
    };
    return {
        class_name: item.class_name,
        subject_code: item.subject_code,
        subject_name: item.subject_name,   // 👈 thêm
        teacher_code: item.teacher_code,
        teacher_name: item.teacher_name,   // 👈 thêm
        day_of_week: slot.day_of_week,
        session: slot.session,
        period: slot.period
    };
}

function norm(s) {
    return (s || "")
        .toString()
        .toLowerCase()
        .normalize('NFD')
        .replace(/\p{Diacritic}/gu, ''); // bỏ dấu tiếng Việt
}

function getGradeFromClassName(name) {
    // Lấy 2 chữ số đầu làm khối: "10A1" -> 10
    const m = String(name || "").match(/^(\d{2})/);
    return m ? m[1] : "00";
}

function shortTeacherLabel(it) {
    const nm = it.teacher_name || it.teacher_code || "";
    const stripped = nm.replace(/^Giáo viên\s*/i, "").trim();
    return "GV. " + stripped;   // → “GV. 039” / “GV. Nguyễn Văn A”
}


// Viết tắt môn: lấy chữ cái đầu của các từ, từ cuối giữ nguyên (viết hoa chữ cái đầu), nối không khoảng trắng.
function cap(s) { return s ? (s[0].toUpperCase() + s.slice(1)) : ""; }

function abbrSubjectName(it) {
    const raw = (it.subject_name || "").trim();
    if (raw) {
        const parts = raw.split(/\s+/);
        if (parts.length === 1) return cap(parts[0]);   // 1 từ => giữ nguyên
        const last = cap(parts.pop());                  // từ cuối GIỮ NGUYÊN
        const initials = parts.map(w => (w[0] || "").toUpperCase()).join(""); // chữ cái đầu các từ trước
        return (initials + last).replace(/\s+/g, "");
    }
    // Fallback code: "LIT_10" -> "LIT10"
    const code = it.subject_code || "";
    const m = code.match(/^([A-Z]+)_(\d+)/);
    return m ? (m[1] + m[2]) : code;
}


function renderGridCompactByGrade() {
    // Lọc theo giáo viên + search; bỏ filter theo lớp để hiển thị toàn bộ khối.
    const tcode = document.getElementById("filterTeacher").value.trim();
    const qraw = document.getElementById("searchBox").value.trim();
    const q = norm(qraw);

    const items = timetables.filter(it => {
        if (tcode && it.teacher_code !== tcode) return false;
        if (q) {
            const hay = [it.class_name, it.subject_code, it.subject_name, it.teacher_code, it.teacher_name]
                .map(norm).join(" ");
            if (!hay.includes(q)) return false;
        }
        return true;
    });

    // Nhóm lớp theo khối (10/11/12)
    const byGrade = new Map(); // grade -> [classNames]
    classes.forEach(c => {
        const g = getGradeFromClassName(c.name);
        if (!byGrade.has(g)) byGrade.set(g, []);
        byGrade.get(g).push(c.name);
    });

    // Nếu người dùng chọn 1 lớp, chỉ hiển thị khối của lớp đó
    const sel = document.getElementById("filterClass").value.trim();
    if (sel) {
        const gSel = getGradeFromClassName(sel);
        const only = new Map();
        only.set(gSel, (byGrade.get(gSel) || []).slice().sort());
        byGrade.clear();
        only.forEach((v, k) => byGrade.set(k, v));
    } else {
        // sort class trong từng khối
        for (const [g, arr] of byGrade.entries()) byGrade.set(g, arr.slice().sort());
    }

    const wrapper = document.getElementById("gridWrapper");
    if (!byGrade.size) {
        wrapper.innerHTML = `<div class="p-8 text-center text-slate-500">Không có dữ liệu để hiển thị.</div>`;
        return;
    }

    // Map tra cứu nhanh record theo (class, day, session, period)
    const key4 = (cn, d, s, p) => `${cn}|${d}|${s}|${p}`;
    const store = new Map();
    for (const it of items) {
        const k = key4(it.class_name, it.day_of_week, it.session, it.period);
        (store.get(k) || store.set(k, []).get(k)).push(it);
    }

    let htmlAll = "";
    const orderedGrades = Array.from(byGrade.keys()).sort(); // 10,11,12

    for (const grade of orderedGrades) {
        const classList = byGrade.get(grade);
        if (!classList || !classList.length) continue;

        // THEAD: Thứ | Tiết | ...các lớp
        const thead = `
      <thead>
        <tr>
          <th class="text-center">Thứ</th>
          <th class="text-center">Tiết</th>
          ${classList.map(cn => `<th class="text-center font-semibold">${cn}</th>`).join("")}
        </tr>
      </thead>`;

        let tbody = "";
        for (const day of DAYS) {
            const rfd = rowsForDay();
            rfd.forEach((r, idx) => {
                tbody += `<tr>`;
                if (idx === 0) {
                    const thuNum = { Monday: "2", Tuesday: "3", Wednesday: "4", Thursday: "5", Friday: "6" }[day] || day;
                    tbody += `<td rowspan="${rfd.length}" class="text-center align-middle"><strong>${thuNum}</strong></td>`;
                }
                tbody += `<td class="text-center">${r.label}</td>`;
                for (const cls of classList) {
                    const k = key4(cls, day, r.session, r.period);
                    const arr = store.get(k) || [];
                    const lines = arr.map(a => `${abbrSubjectName(a)} – ${shortTeacherLabel(a)}`);
                    tbody += `<td class="text-sm">${lines.join("<br>") || ""}</td>`;
                }
                tbody += `</tr>`;
            });
        }

        htmlAll += `
      <h5 class="mt-4 mb-2 font-semibold">Khối ${grade}</h5>
      <div class="border rounded-2xl overflow-auto">
        <table class="tkb-compact-table">
          ${thead}
          <tbody>${tbody}</tbody>
        </table>
      </div>
      <div class="page-break"></div>
    `;
    }

    wrapper.innerHTML = htmlAll;
}


function rowsForDay() {
    const rows = [];
    for (let p = 1; p <= PERIODS_PER_SESSION; p++) rows.push({ session: "morning", period: p, label: `S${p}` });
    for (let p = 1; p <= PERIODS_PER_SESSION; p++) rows.push({ session: "afternoon", period: p, label: `C${p}` });
    return rows;
}

function shortSubjectLabel(it) {
    // Dùng subject_name nếu có; nếu subject_code dạng "TOAN_10" -> "Toán 10"
    if (it.subject_name) return it.subject_name;
    const code = it.subject_code || "";
    const m = code.match(/^([A-Z]+)_(\d+)/);
    if (!m) return code;
    // map vài mã phổ biến
    const map = {
        TOAN: "Toán", LIT: "Ngữ Văn", ENG: "Tiếng Anh", PHYS: "Vật Lý", CHEM: "Hóa",
        BIO: "Sinh Học", HIST: "Lịch Sử", GEO: "Địa Lí", CIV: "Giáo Dục Công Dân",
        IT: "Tin Học", PE: "Thể Dục", TECH: "Công Nghệ", DEF: "GDQP"
    };
    const base = map[m[1]] || m[1];
    return `${base} ${m[2]}`;
}

function sessionPeriodRows() {
    // tạo danh sách hàng: [{session, period, label}]
    const rows = [];
    for (let p = 1; p <= PERIODS_PER_SESSION; p++) rows.push({ session: "morning", period: p, label: `S${p}` });
    for (let p = 1; p <= PERIODS_PER_SESSION; p++) rows.push({ session: "afternoon", period: p, label: `C${p}` });
    return rows;
}

async function fetchJSON(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Fetch ${url} failed: ${res.status}`);
    return res.json();
}

function populateFilters() {
    const selClass = document.getElementById("filterClass");
    selClass.innerHTML = `<option value="">— Tất cả —</option>` + classes.map(c => `<option value="${c.name}">${c.name}</option>`).join("");

    const selTeacher = document.getElementById("filterTeacher");
    selTeacher.innerHTML = `<option value="">— Tất cả —</option>` + teachers.map(t => `<option value="${t.code}">${t.name || t.code}</option>`).join("");
}

function buildLegend() {
    const legend = document.getElementById("legend");
    // Ẩn hoàn toàn legend ở chế độ compact theo khối
    if (viewMode === "compactGrade") {
        legend.classList.add("d-none");
        legend.innerHTML = "";
        return;
    }
    legend.classList.remove("d-none");

    // (giữ nguyên phần render legend cũ)
    const byCode = new Map();
    for (const x of timetables) {
        if (!byCode.has(x.subject_code)) byCode.set(x.subject_code, x.subject_name || x.subject_code);
    }
    const pairs = Array.from(byCode.entries()).sort((a, b) => a[1].localeCompare(b[1]));
    legend.innerHTML = `
    <div class="p-3 bg-white rounded-2xl border border-slate-200">
      <div class="font-semibold mb-2">Mã màu theo môn</div>
      <div class="flex flex-wrap gap-2">
        ${pairs.map(([code, name]) => {
        const c = colorForSubjectKey(code);
        return `<span class="chip ${c} print-bg" title="${code}">${name}</span>`;
    }).join("")}
      </div>
    </div>`;
}

function applyFilters(items) {
    const cls = document.getElementById("filterClass").value.trim();
    const tcode = document.getElementById("filterTeacher").value.trim();
    //   const q = document.getElementById("searchBox").value.trim().toLowerCase();
    const qraw = document.getElementById("searchBox").value.trim();
    const q = norm(qraw);

    return items.filter(it => {
        if (cls && it.class_name !== cls) return false;
        if (tcode && it.teacher_code !== tcode) return false;
        if (q) {
            const haystack = [
                it.class_name,
                it.subject_code,
                it.subject_name,   // ⬅️
                it.teacher_code,
                it.teacher_name    // ⬅️
            ].map(norm).join(" ");
            if (!haystack.includes(q)) return false;
        }
        return true;
    });
}

function renderGrid() {
    if (viewMode === "compactGrade") {
        renderGridCompactByGrade();
        return;
    } else {
        // chế độ thẻ màu (đang có)
        const items = applyFilters(timetables);

        const byClass = {};
        for (const it of items) (byClass[it.class_name] ||= []).push(it);

        const wrapper = document.getElementById("gridWrapper");
        const classNames = Object.keys(byClass).sort();
        if (!classNames.length) {
            wrapper.innerHTML = `<div class="p-8 text-center text-slate-500">Không có dữ liệu theo bộ lọc.</div>`;
            return;
        }

        wrapper.innerHTML = classNames.map(className => {
            const records = byClass[className];
            const cellMap = new Map();
            for (const rec of records) {
                const key = gridKey(rec.day_of_week, rec.session, rec.period);
                (cellMap.get(key) || cellMap.set(key, []).get(key)).push(rec);
            }

            const header = `
        <thead class="sticky-top bg-white print-bg">
          <tr>
            <th class="sticky-left bg-white print-bg border-b px-4 py-3 text-left">Lớp: ${className}</th>
            ${DAYS.map(d => `<th class="border-b px-4 py-3 text-center font-semibold">${d}</th>`).join("")}
          </tr>
        </thead>`;

            let bodyRows = "";
            for (const session of ["morning", "afternoon"]) {
                for (let p = 1; p <= PERIODS_PER_SESSION; p++) {
                    bodyRows += `<tr>`;
                    bodyRows += `<td class="sticky-left bg-white print-bg border-t px-3 py-2 text-sm text-slate-600">
                        <div class="font-medium">${SESSION_LABELS[session]}</div>
                        <div class="text-xs">Tiết ${p}</div>
                      </td>`;
                    for (const day of DAYS) {
                        const key = gridKey(day, session, p);
                        const cellItems = cellMap.get(key) || [];
                        const html = cellItems.map(ci => {
                            const color = colorForSubjectKey(ci.subject_code);
                            return `<div class="cell p-2 rounded-xl border border-slate-200 hover:shadow transition">
                        <div class="badge ${color} print-bg inline-block mb-1">
                          ${subjectLabel(ci.subject_code, ci.subject_name)}
                        </div>
                        <div class="text-sm font-medium">${ci.teacher_name || ci.teacher_code}</div>
                      </div>`;
                        }).join("");

                        bodyRows += `<td class="align-top border-t px-2 py-2">${html || `<div class="cell rounded-xl bg-slate-50 border border-dashed border-slate-200"></div>`}</td>`;
                    }
                    bodyRows += `</tr>`;
                }
            }

            return `<div class="border-b last:border-b-0">
                <table class="w-full border-separate" style="border-spacing:0">
                  ${header}
                  <tbody>${bodyRows}</tbody>
                </table>
              </div>`;
        }).join("");
    }
}


function exportCSV() {
    // xuất theo danh sách dòng
    const items = applyFilters(timetables);
    const rows = [["class_name", "subject_code", "teacher_code", "day_of_week", "session", "period"]];
    items.forEach(i => rows.push([i.class_name, i.subject_code, i.teacher_code, i.day_of_week, i.session, String(i.period)]));
    const csv = rows.map(r => r.map(x => `"${String(x).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "timetable.csv";
    a.click();
    URL.revokeObjectURL(url);
}

function setupEvents() {
    document.getElementById("filterClass").addEventListener("change", renderGrid);
    document.getElementById("filterTeacher").addEventListener("change", renderGrid);
    document.getElementById("searchBox").addEventListener("input", () => {
        // debounce nhẹ
        clearTimeout(window.__sb);
        window.__sb = setTimeout(renderGrid, 150);
    });
    document.getElementById("btnPrint").addEventListener("click", () => window.print());
    // document.getElementById("btnCSV").addEventListener("click", exportCSV);

    // Toggle view mode
    document.getElementById("modePrettyLabel").addEventListener("click", () => {
        viewMode = "pretty";
        document.getElementById("modePrettyLabel").classList.add("active");
        document.getElementById("modeCompactGradeLabel").classList.remove("active");
        renderGrid();
    });
    document.getElementById("modeCompactGradeLabel").addEventListener("click", () => {
        viewMode = "compactGrade";
        document.getElementById("modeCompactGradeLabel").classList.add("active");
        document.getElementById("modePrettyLabel").classList.remove("active");
        renderGrid();
    });



}

async function boot() {
    setupEvents();
    try {
        const [cls, tchs, tts] = await Promise.all([
            fetchJSON(API_CLASSES),
            fetchJSON(API_TEACHERS),
            fetchJSON(API_TIMETABLE),
        ]);

        // Chuẩn hóa danh sách
        classes = cls;
        teachers = tchs;
        timetables = tts.map(normalizeItem);

        populateFilters();
        buildLegend();
        renderGrid();
    } catch (err) {
        console.error(err);
        document.getElementById("gridWrapper").innerHTML =
            `<div class="p-8 text-center text-rose-600">Không tải được dữ liệu. Kiểm tra API endpoint & CORS.</div>`;
    }
}

function shortSubjectLabel(it) {
    if (it.subject_name) return it.subject_name;
    const code = it.subject_code || "";
    const m = code.match(/^([A-Z]+)_(\d+)/);
    if (!m) return code;
    const map = {
        TOAN: "Toán", LIT: "Ngữ Văn", ENG: "Tiếng Anh", PHYS: "Vật Lý", CHEM: "Hóa",
        BIO: "Sinh Học", HIST: "Lịch Sử", GEO: "Địa Lí", CIV: "GDCD",
        IT: "Tin Học", PE: "Thể Dục", TECH: "Công Nghệ", DEF: "GDQP"
    };
    const base = map[m[1]] || m[1];
    return `${base} ${m[2]}`;
}
function rowsForDay() {
    // 10 hàng: Sáng 1..5, Chiều 1..5
    const rows = [];
    for (let p = 1; p <= PERIODS_PER_SESSION; p++) rows.push({ session: "morning", period: p, label: `${p}` });
    for (let p = 1; p <= PERIODS_PER_SESSION; p++) rows.push({ session: "afternoon", period: p, label: `${p}` });
    return rows;
}

function renderGridCompactAllClasses() {
    // Lọc theo teacher + search, nhưng BỎ filter lớp để hiển thị tất cả
    const tcode = document.getElementById("filterTeacher").value.trim();
    const qraw = document.getElementById("searchBox").value.trim();
    const q = norm(qraw);

    const items = timetables.filter(it => {
        if (tcode && it.teacher_code !== tcode) return false;
        if (q) {
            const hay = [it.class_name, it.subject_code, it.subject_name, it.teacher_code, it.teacher_name].map(norm).join(" ");
            if (!hay.includes(q)) return false;
        }
        return true;
    });

    // Danh sách cột (lớp)
    let classList = classes.map(c => c.name).sort();
    // Nếu người dùng cố tình chọn 1 lớp, ta vẫn tôn trọng:
    const sel = document.getElementById("filterClass").value.trim();
    if (sel) classList = [sel];

    // Lập map (class,day,session,period) -> danh sách record
    const key4 = (cn, d, s, p) => `${cn}|${d}|${s}|${p}`;
    const m = new Map();
    for (const it of items) {
        const k = key4(it.class_name, it.day_of_week, it.session, it.period);
        (m.get(k) || m.set(k, []).get(k)).push(it);
    }

    const wrapper = document.getElementById("gridWrapper");
    if (!classList.length) {
        wrapper.innerHTML = `<div class="p-8 text-center text-slate-500">Không có lớp để hiển thị.</div>`;
        return;
    }

    // Header: 2 cột trái (“Thứ”, “Tiết”), rồi các lớp
    const thead = `
    <thead class="bg-white print-bg">
      <tr>
        <th class="border-b px-2 py-2 text-center" style="width:60px">Thứ</th>
        <th class="border-b px-2 py-2 text-center" style="width:60px">Tiết</th>
        ${classList.map(cn => `<th class="border-b px-2 py-2 text-center font-semibold">${cn}</th>`).join("")}
      </tr>
    </thead>`;

    let tbody = "";
    for (const day of DAYS) {
        const dayRows = rowsForDay();
        dayRows.forEach((row, idx) => {
            tbody += `<tr>`;
            // Ô "Thứ" gộp 10 hàng
            if (idx === 0) {
                const thu = { Monday: "2", Tuesday: "3", Wednesday: "4", Thursday: "5", Friday: "6" }[day] || day;
                tbody += `<td class="border-t px-2 py-1 text-center align-middle" rowspan="${dayRows.length}">
                    <strong>${thu}</strong>
                  </td>`;
            }
            // Ô "Tiết": hiển thị S/C
            const label = idx < PERIODS_PER_SESSION ? `S${row.label}` : `C${row.label}`;
            tbody += `<td class="border-t px-2 py-1 text-center">${label}</td>`;

            // Các cột lớp
            for (const cn of classList) {
                const k = key4(cn, day, row.session, row.period);
                const arr = m.get(k) || [];
                const lines = arr.map(a => `${shortSubjectLabel(a)} – ${shortTeacherLabel(a)}`);
                tbody += `<td class="border-t px-2 py-1 text-sm">${lines.join("<br>") || ""}</td>`;
            }
            tbody += `</tr>`;
        });
    }

    // Render
    wrapper.innerHTML = `
    <div class="border rounded-2xl overflow-hidden">
      <table class="w-full border-separate text-sm" style="border-spacing:0">
        ${thead}
        <tbody>${tbody}</tbody>
      </table>
    </div>
  `;
}


function renderErrorTable(subjectMissing, classSubjectMissing) {
    let html = `<strong>❌ Không thể tạo thời khóa biểu do thiếu giáo viên.</strong>`;

    // Thiếu theo môn học
    if (subjectMissing && Object.keys(subjectMissing).length > 0) {
        html += `<p class="mt-2"><strong>Thiếu theo môn học:</strong></p>`;
        html += `<table class="table table-sm table-bordered tkb-missing-table">
                    <colgroup>
                        <col style="width: 70%;">
                        <col style="width: 30%;">
                    </colgroup>
                    <thead><tr><th>Môn</th><th>Số tiết thiếu</th></tr></thead><tbody>`;
        for (const [subj, miss] of Object.entries(subjectMissing)) {
            html += `<tr><td>${subj}</td><td>${miss}</td></tr>`;
        }
        html += `</tbody></table>`;
    }

    // Thiếu theo lớp – môn
    if (classSubjectMissing && Object.keys(classSubjectMissing).length > 0) {
        html += `<p><strong>Thiếu theo lớp – môn:</strong></p>`;
        html += `<table class="table table-sm table-bordered tkb-missing-table">
                    <colgroup>
                        <col style="width: 70%;">
                        <col style="width: 30%;">
                    </colgroup>
                    <thead><tr><th>Lớp – Môn</th><th>Số tiết thiếu</th></tr></thead><tbody>`;
        for (const [clsSubj, miss] of Object.entries(classSubjectMissing)) {
            html += `<tr><td>${clsSubj}</td><td>${miss}</td></tr>`;
        }
        html += `</tbody></table>`;
    }

    $("#tkbError").removeClass("d-none").html(html);
}

document.getElementById("modeCompactGradeLabel").addEventListener("click", () => {
    viewMode = "compactGrade";
    document.getElementById("modeCompactGradeLabel").classList.add("active");
    document.getElementById("modePrettyLabel").classList.remove("active");
    buildLegend();    // Ẩn legend ở compact
    renderGrid();
});

document.getElementById("modePrettyLabel").addEventListener("click", () => {
    viewMode = "pretty";
    document.getElementById("modePrettyLabel").classList.add("active");
    document.getElementById("modeCompactGradeLabel").classList.remove("active");
    buildLegend();    // Hiện legend lại ở pretty
    renderGrid();
});

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

$(document).ready(function () {
    $("#btnUpdateTKB").on("click", function () {
        const $btn = $(this);
        const $spinner = $("#spinnerUpdate");
        const $text = $("#btnUpdateText");

        // Hiển thị trạng thái xử lý
        $btn.prop("disabled", true);
        $spinner.removeClass("d-none");
        $text.html(" Đang cập nhật...");

        $.ajax({
            url: "http://localhost:8002/api/timetables/gen_timetable",
            type: "POST",
            headers: {
                "Authorization": "Bearer " + (localStorage.getItem("access_token") || "")
            },
            contentType: "application/json",
            success: function (data) {
                // Reload lại trang để tải dữ liệu mới
                location.reload();
            },
            error: function (xhr) {
                const data = xhr.responseJSON?.detail;
                if (data && data.subject_missing && data.class_subject_missing) {
                    renderErrorTable(data.subject_missing, data.class_subject_missing);
                } else {
                    const errorMsg = typeof data === "string" ? data : "Cập nhật thất bại. Vui lòng thử lại.";
                    $("#tkbError").removeClass("d-none").html("❌ " + errorMsg);
                }
            },
            complete: function () {
                // Kết thúc trạng thái xử lý (trường hợp error)
                $btn.prop("disabled", false);
                $spinner.addClass("d-none");
                $text.html('<i class="fas fa-sync-alt mr-1"></i> Cập Nhật TKB');
            }
        });
    });
});


boot();