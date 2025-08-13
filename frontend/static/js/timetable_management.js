// ====== CONFIG: Update these endpoints if needed ======
const API_CLASSES = "http://localhost:8000/api/timetables/classes";
const API_TEACHERS = "http://localhost:8000/api/timetables/teachers";
const API_TIMETABLE = "http://localhost:8000/api/timetables/view";
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
    // gom theo subject_code để màu ổn định, nhưng hiển thị subject_name
    const byCode = new Map();
    for (const x of timetables) {
        if (!byCode.has(x.subject_code)) {
            byCode.set(x.subject_code, x.subject_name || x.subject_code);
        }
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
            </div>
        `;
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
    const items = applyFilters(timetables);

    // group theo class để hiển thị bảng mỗi lớp
    const byClass = {};
    for (const it of items) {
        if (!byClass[it.class_name]) byClass[it.class_name] = [];
        byClass[it.class_name].push(it);
    }

    const wrapper = document.getElementById("gridWrapper");
    const classNames = Object.keys(byClass).sort();
    if (classNames.length === 0) {
        wrapper.innerHTML = `<div class="p-8 text-center text-slate-500">Không có dữ liệu theo bộ lọc.</div>`;
        return;
    }

    wrapper.innerHTML = classNames.map(className => {
        const records = byClass[className];

        // Build map slot -> cells
        const cellMap = new Map();
        for (const rec of records) {
            const key = gridKey(rec.day_of_week, rec.session, rec.period);
            if (!cellMap.has(key)) cellMap.set(key, []);
            cellMap.get(key).push(rec);
        }

        // Bảng: cột ngày (5), mỗi ngày 2 buổi x 5 tiết = 10 hàng
        // Ta dựng header theo ngày, hàng theo buổi+tiết
        const header = `
          <thead class="sticky-top bg-white print-bg">
            <tr>
              <th class="sticky-left bg-white print-bg border-b px-4 py-3 text-left">Lớp: ${className}</th>
              ${DAYS.map(d => `<th class="border-b px-4 py-3 text-center font-semibold">${d}</th>`).join("")}
            </tr>
          </thead>
        `;

        let bodyRows = "";
        for (const session of ["morning", "afternoon"]) {
            for (let p = 1; p <= PERIODS_PER_SESSION; p++) {
                bodyRows += `<tr>`;
                // Cột trái: nhãn buổi + tiết
                bodyRows += `<td class="sticky-left bg-white print-bg border-t px-3 py-2 text-sm text-slate-600">
                <div class="font-medium">${SESSION_LABELS[session]}</div>
                <div class="text-xs">Tiết ${p}</div>
            </td>`;
                // Mỗi cột theo ngày
                for (const day of DAYS) {
                    const key = gridKey(day, session, p);
                    const cellItems = cellMap.get(key) || [];
                    const html = cellItems.map(ci => {
                        const color = colorForSubjectKey(ci.subject_code);
                        return `
                    <div class="cell p-2 rounded-xl border border-slate-200 hover:shadow transition">
                        <div class="badge ${color} print-bg inline-block mb-1">
                        ${subjectLabel(ci.subject_code, ci.subject_name)}
                        </div>
                        <div class="text-sm font-medium">
                        ${ci.teacher_name || ci.teacher_code}
                        </div>
                    </div>
                    `;
                    }).join("");

                    bodyRows += `<td class="align-top border-t px-2 py-2">${html || `<div class="cell rounded-xl bg-slate-50 border border-dashed border-slate-200"></div>`}</td>`;
                }
                bodyRows += `</tr>`;
            }
        }

        return `
          <div class="border-b last:border-b-0">
            <table class="w-full border-separate" style="border-spacing:0">
              ${header}
              <tbody>
                ${bodyRows}
              </tbody>
            </table>
          </div>
        `;
    }).join("");
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
    document.getElementById("btnCSV").addEventListener("click", exportCSV);
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

boot();