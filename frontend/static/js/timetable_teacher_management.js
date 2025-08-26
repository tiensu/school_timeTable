// ====== CONFIG: Update these endpoints if needed ======
const API_CLASSES = "http://localhost:8002/api/timetables/teachers/classes";
const API_TEACHERS = "http://localhost:8002/api/timetables/teachers/teachers";
const API_TIMETABLE = "http://localhost:8002/api/timetables/teachers/view";
// ======================================================

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const SESSION_LABELS = { morning: "Sáng" };
const PERIODS_PER_SESSION = 5;
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

let classes = [];
let teachers = [];
let timetables = [];
let subjectColorMap = new Map();
let viewMode = "pretty"; // "pretty" | "compactTeacher"

function subjectLabel(code, name) {
    // Bỏ số (10, 11, 12) ở cuối tên môn học
    if (name) {
        return name.replace(/\s*(10|11|12)\s*$/, "").trim();
    }
    // Nếu không có tên, dùng code và cũng bỏ số ở cuối nếu có
    return code.replace(/(10|11|12)$/, "");
}

function colorForSubjectKey(code) {
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
    const slot = item.slot || {
        day_of_week: item.day_of_week,
        session: item.session,
        period: item.period
    };
    return {
        class_name: item.class_name,
        subject_code: item.subject_code,
        subject_name: item.subject_name,
        teacher_code: item.teacher_code,
        teacher_name: item.teacher_name,
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
        .replace(/\p{Diacritic}/gu, '');
}

function shortTeacherLabel(it) {
    const nm = it.teacher_name || it.teacher_code || "";
    return nm.replace(/^Giáo viên\s*/i, "").trim();
}

// Viết tắt tên giáo viên: "GV. Ngô Thị Oanh" -> "NT.Oanh"
function shortTeacherLabelCompact(it) {
    const name = (it.teacher_name || it.teacher_code || "").replace(/^Giáo viên\s*/i, "").trim();
    if (!name || /^\d+$/.test(name)) return name;
    const parts = name.split(/\s+/);
    if (parts.length === 1) return parts[0];
    const last = parts.pop();
    const initials = parts.map(w => w[0].toUpperCase()).join("");
    return `${initials}.${last}`;
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

// Viết tắt môn: lấy chữ cái đầu của các từ, từ cuối giữ nguyên (viết hoa chữ cái đầu), nối không khoảng trắng.
// Bỏ 2 chữ số đầu (10, 11, 12) nếu có trong tên môn học viết tắt
function abbrSubjectName(it) {
    const raw = (it.subject_name || "").trim();
    if (raw) {
        const parts = raw.split(/\s+/);
        if (parts.length === 1) {
            // Nếu là "Toán 10" hoặc "LIT 12" thì bỏ số
            return raw.replace(/^(10|11|12)\b/, "").replace(/\s*(10|11|12)$/, "").trim();
        }
        const last = parts.pop();
        // Nếu last là số khối thì bỏ
        const lastClean = last.match(/^(10|11|12)$/) ? "" : last;
        const initials = parts.map(w => (w[0] || "").toUpperCase()).join("");
        return (initials + lastClean).replace(/\s+/g, "");
    }
    const code = it.subject_code || "";
    // Nếu code kết thúc bằng 2 số thì bỏ
    return code.replace(/(10|11|12)$/, "");
}

function applyFilters(items) {
    const cls = document.getElementById("filterClass").value.trim();
    const tcode = document.getElementById("filterTeacher").value.trim();
    const qraw = document.getElementById("searchBox").value.trim();
    const q = norm(qraw);

    return items.filter(it => {
        if (cls && it.class_name !== cls) return false;
        if (tcode && it.teacher_code !== tcode) return false;
        if (q) {
            const haystack = [
                it.class_name,
                it.subject_code,
                it.subject_name,
                it.teacher_code,
                it.teacher_name
            ].map(norm).join(" ");
            if (!haystack.includes(q)) return false;
        }
        return true;
    });
}

function populateFilters() {
    const selClass = document.getElementById("filterClass");
    // Sắp xếp lớp theo thứ tự tự nhiên (natural sort)
    const sortedClasses = [...classes].sort((a, b) => {
        const nameA = a.name || "";
        const nameB = b.name || "";
        // Tách phần số ở cuối tên lớp
        const matchA = nameA.match(/(\d+)$/);
        const matchB = nameB.match(/(\d+)$/);
        if (matchA && matchB) {
            const prefixA = nameA.slice(0, matchA.index);
            const prefixB = nameB.slice(0, matchB.index);
            if (prefixA === prefixB) {
                return Number(matchA[1]) - Number(matchB[1]);
            }
            return prefixA.localeCompare(prefixB);
        }
        return nameA.localeCompare(nameB);
    });
    selClass.innerHTML = `<option value="">— Tất cả —</option>` + sortedClasses.map(c => `<option value="${c.name}">${c.name}</option>`).join("");

    const selTeacher = document.getElementById("filterTeacher");
    // Sắp xếp giáo viên theo tên (hoặc code nếu không có tên)
    const sortedTeachers = [...teachers].sort((a, b) => {
        const nameA = (a.name || a.code || "").toString().toLowerCase();
        const nameB = (b.name || b.code || "").toString().toLowerCase();
        return nameA.localeCompare(nameB);
    });
    selTeacher.innerHTML = `<option value="">— Tất cả —</option>` + sortedTeachers.map(t => `<option value="${t.code}">${t.name || t.code}</option>`).join("");
}

function buildLegend() {
    const legend = document.getElementById("legend");
    if (viewMode === "compactTeacher") {
        legend.classList.add("d-none");
        legend.innerHTML = "";
        return;
    }
    legend.classList.remove("d-none");

    const byCode = new Map();
    for (const x of timetables) {
        if (!byCode.has(x.subject_code)) byCode.set(x.subject_code, x.subject_name || x.subject_code);
    }
    const pairs = Array.from(byCode.entries()).sort((a, b) =>
        (a[1] || "").toString().localeCompare((b[1] || "").toString())
    );
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

function renderGrid() {
    if (viewMode === "compactTeacher") {
        renderGridCompactByTeacher();
        return;
    } else {
        // Chế độ thẻ màu: hiển thị từng giáo viên
        const items = applyFilters(timetables);

        const byTeacher = {};
        for (const it of items) (byTeacher[it.teacher_code] ||= []).push(it);

        const wrapper = document.getElementById("gridWrapper");
        const teacherCodes = Object.keys(byTeacher).sort();
        if (!teacherCodes.length) {
            wrapper.innerHTML = `<div class="p-8 text-center text-slate-500">Không có dữ liệu theo bộ lọc.</div>`;
            return;
        }

        wrapper.innerHTML = teacherCodes.map(teacherCode => {
            const records = byTeacher[teacherCode];
            const teacherName = records[0]?.teacher_name || teacherCode;
            const cellMap = new Map();
            for (const rec of records) {
                const key = gridKey(rec.day_of_week, rec.session, rec.period);
                (cellMap.get(key) || cellMap.set(key, []).get(key)).push(rec);
            }

            const header = `
<thead class="sticky-top bg-white print-bg">
  <tr>
    <th class="sticky-left bg-white print-bg border-b px-4 py-3 text-left">Giáo viên: ${teacherName}</th>
    ${DAYS.map(d => `<th class="border-b px-4 py-3 text-center font-semibold">${d}</th>`).join("")}
  </tr>
</thead>`;

            let bodyRows = "";
            for (const session of ["morning"]) {
                for (let p = 1; p <= PERIODS_PER_SESSION; p++) {
                    bodyRows += `<tr>`;
                    bodyRows += `<td class="sticky-left bg-white print-bg border-t px-3 py-2 text-slate-600">
                        <div class="font-medium">${SESSION_LABELS[session]}</div>
                        <div class="text-xs">Tiết ${p}</div>
                      </td>`;
                    for (const day of DAYS) {
                        const key = gridKey(day, session, p);
                        const cellItems = cellMap.get(key) || [];
                        // Nếu là tiết trực X (không có class_name và subject_name), hiển thị "Trực X" màu đỏ
                        const html = cellItems.map(ci => {
                            if (!ci.class_name && !ci.subject_name) {
                                return `<div class="cell p-2 rounded-xl border border-slate-200" style="background:#fee2e2;">
                            <span style="color:#e11d48;font-weight:bold">Trực X</span>
                        </div>`;
                            }
                            const color = colorForSubjectKey(ci.subject_code);
                            return `<div class="cell p-2 rounded-xl border border-slate-200 hover:shadow transition">
                        <div class="badge ${color} print-bg inline-block mb-1">
                          ${subjectLabel(ci.subject_code, ci.subject_name)}
                        </div>
                        <div class=" font-medium">Lớp: ${ci.class_name}</div>
                      </div>`;
                        }).join("");

                        bodyRows += `<td class="align-top border-t px-2 py-2" style="font-size:12px">${html || `<div class="cell rounded-xl bg-slate-50 border border-dashed border-slate-200"></div>`}</td>`;
                    }
                    bodyRows += `</tr>`;
                }
            }

            return `<div class="border-b last:border-b-0">
                <table class="w-full " style="border-spacing:0">
                  ${header}
                  <tbody>${bodyRows}</tbody>
                </table>
              </div>`;
        }).join("");
    }
}

function renderGridCompactByTeacher() {
    // Hiển thị grid tổng hợp cho tất cả giáo viên, mỗi bảng tối đa 10 giáo viên
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

    let teacherList = teachers.map(t => t.code).sort();
    const sel = document.getElementById("filterTeacher").value.trim();
    if (sel) teacherList = [sel];

    // Chia thành các nhóm 10 giáo viên
    const chunkSize = 10;
    const teacherChunks = [];
    for (let i = 0; i < teacherList.length; i += chunkSize) {
        teacherChunks.push(teacherList.slice(i, i + chunkSize));
    }

    const key4 = (tc, d, s, p) => `${tc}|${d}|${s}|${p}`;
    const m = new Map();
    for (const it of items) {
        const k = key4(it.teacher_code, it.day_of_week, it.session, it.period);
        (m.get(k) || m.set(k, []).get(k)).push(it);
    }

    const wrapper = document.getElementById("gridWrapper");
    if (!teacherList.length) {
        wrapper.innerHTML = `<div class="p-8 text-center text-slate-500">Không có giáo viên để hiển thị.</div>`;
        return;
    }

    let allTables = "";
    teacherChunks.forEach((chunk, idx) => {
        // Tính width cho mỗi cột giáo viên
        const teacherColWidth = Math.floor(100 / chunk.length);

        const thead = `
        <thead class="bg-white print-bg">
          <tr>
            <th class="border border-slate-400 px-2 py-2 text-center" style="width:60px">Thứ</th>
            <th class="border border-slate-400 px-2 py-2 text-center" style="width:60px">Tiết</th>
            ${chunk.map(tc => {
            const t = teachers.find(x => x.code === tc);
            // Tên giáo viên viết tắt
            return `<th class="border border-slate-400 px-2 py-2 text-center font-semibold" style="width:${teacherColWidth}%">${shortTeacherLabelCompact({ teacher_name: t?.name, teacher_code: tc })}</th>`;
        }).join("")}
          </tr>
        </thead>`;

        let tbody = "";
        for (const day of DAYS) {
            for (let p = 1; p <= PERIODS_PER_SESSION; p++) {
                tbody += `<tr>`;
                if (p === 1) {
                    const thu = { Monday: "2", Tuesday: "3", Wednesday: "4", Thursday: "5", Friday: "6", Saturday: "7" }[day] || day;
                    tbody += `<td class="border border-slate-400 px-2 py-1 text-center align-middle" rowspan="${PERIODS_PER_SESSION}">
                        <strong>${thu}</strong>
                      </td>`;
                }
                tbody += `<td class="border border-slate-400 px-2 py-1 text-center">S${p}</td>`;
                for (const tc of chunk) {
                    const k = key4(tc, day, "morning", p);
                    const arr = m.get(k) || [];
                    // Nếu là tiết trực X (không có class_name và subject_name), hiển thị "Trực X" màu đỏ
                    const lines = arr.map(a => {
                        if (!a.class_name && !a.subject_name) {
                            return `<span style="color:#e11d48;font-weight:bold">Trực X</span>`;
                        }
                        return `${abbrSubjectName(a)} – ${a.class_name}`;
                    });
                    tbody += `<td class="border border-slate-400 px-2 py-1" style="width:${teacherColWidth}%">${lines.join("<br>") || ""}</td>`;
                }
                tbody += `</tr>`;
            }
        }

        // Kiểm tra bảng này có dữ liệu không
        let hasData = false;
        for (const day of DAYS) {
            for (let p = 1; p <= PERIODS_PER_SESSION; p++) {
                for (const tc of chunk) {
                    const k = key4(tc, day, "morning", p);
                    const arr = m.get(k) || [];
                    if (arr.length > 0) {
                        hasData = true;
                        break;
                    }
                }
                if (hasData) break;
            }
            if (hasData) break;
        }

        // Nếu bảng này có dữ liệu thì mới hiển thị
        if (hasData) {
            allTables += `
        <div class="border border-slate-400 rounded-2xl overflow-hidden mb-6" style="border-width:2px;">
          <table class="w-full " style="border-spacing:0; font-size:12px;">
            ${thead}
            <tbody>${tbody}</tbody>
          </table>
        </div>
        `;
        }
    });

    wrapper.innerHTML = allTables;
}

function setupEvents() {
    document.getElementById("filterClass").addEventListener("change", renderGrid);
    document.getElementById("filterTeacher").addEventListener("change", renderGrid);
    document.getElementById("searchBox").addEventListener("input", () => {
        clearTimeout(window.__sb);
        window.__sb = setTimeout(renderGrid, 150);
    });
    document.getElementById("btnPrint").addEventListener("click", () => window.print());

    document.getElementById("modePrettyLabel").addEventListener("click", () => {
        viewMode = "pretty";
        document.getElementById("modePrettyLabel").classList.add("active");
        document.getElementById("modeCompactGradeLabel").classList.remove("active");
        buildLegend();
        renderGrid();
    });
    document.getElementById("modeCompactGradeLabel").addEventListener("click", () => {
        viewMode = "compactTeacher";
        document.getElementById("modeCompactGradeLabel").classList.add("active");
        document.getElementById("modePrettyLabel").classList.remove("active");
        buildLegend();
        renderGrid();
    });
}

async function fetchJSON(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Fetch ${url} failed: ${res.status}`);
    return res.json();
}

async function boot() {
    setupEvents();
    try {
        const [cls, tchs, tts] = await Promise.all([
            fetchJSON(API_CLASSES),
            fetchJSON(API_TEACHERS),
            fetchJSON(API_TIMETABLE),
        ]);
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

$(document).ready(function () {
    // Home functionality
    const homeBtn = document.getElementById("btnHome");
    if (homeBtn) {
        homeBtn.addEventListener("click", () => {
            window.location.href = "/home.html";
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
            window.location.href = "/login.html";
        });
    }
});

$(document).ready(function () {
    $("#btnUpdateTKB").on("click", function () {
        const $btn = $(this);
        const $spinner = $("#spinnerUpdate");
        const $text = $("#btnUpdateText");

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
            success: function () {
                location.reload();
            },
            error: function (xhr) {
                const data = xhr.responseJSON?.detail;
                const errorMsg = typeof data === "string" ? data : "Cập nhật thất bại. Vui lòng thử lại.";
                $("#tkbError").removeClass("d-none").html("❌ " + errorMsg);
            },
            complete: function () {
                $btn.prop("disabled", false);
                $spinner.addClass("d-none");
                $text.html('<i class="fas fa-sync-alt mr-1"></i> Cập Nhật TKB');
            }
        });
    });
});

boot();
// ...end of