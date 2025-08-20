// const API = "http://localhost:8002/api/reports/teacher-load";
// const API_DETAIL = "http://localhost:8002/api/reports/teacher-load/detail";

(function () {
    const API = "http://localhost:8002/api/reports/teacher-load";
    const API_DETAIL = "http://localhost:8002/api/reports/teacher-load/detail";

    const $ = (s) => document.querySelector(s);
    const $$ = (s) => Array.from(document.querySelectorAll(s));

    function safeBind(el, evt, handler) {
        if (!el) return;
        el.addEventListener(evt, handler);
    }

    function setMsg(text, ok = true) {
        const el = $("#report-msg");
        if (!el) return;
        el.textContent = text || "";
        el.className = "text-sm mt-3 " + (ok ? "text-emerald-600" : "text-rose-600");
    }

    function objToKVLines(obj) {
        if (!obj) return "—";
        return Object.entries(obj)
            .sort((a, b) => b[1] - a[1])
            .map(
                ([k, v]) =>
                    `<div class="leading-6"><span class="font-mono">${k}</span>: <span class="font-semibold">${v}</span></div>`
            )
            .join("");
    }

    function rowHTML(item) {
        const util = item.utilization != null ? `${item.utilization}%` : "—";
        const overloadClass =
            item.overload > 0 ? "text-rose-600 font-semibold" : "text-slate-700";
        return `
      <tr class="border-b hover:bg-slate-50">
        <td class="px-3 py-2">${item.teacher_code}</td>
        <td class="px-3 py-2">${item.teacher_name}</td>
        <td class="px-3 py-2">${item.total_periods}</td>
        <td class="px-3 py-2">${item.capacity ?? "—"}</td>
        <td class="px-3 py-2">${util}</td>
        <td class="px-3 py-2 ${overloadClass}">${item.overload}</td>
        <td class="px-3 py-2">${objToKVLines(item.by_subject)}</td>
        <td class="px-3 py-2">${objToKVLines(item.by_class)}</td>
        <td class="px-3 py-2">${objToKVLines(item.by_day)}</td>
        <td class="px-3 py-2">${objToKVLines(item.by_session)}</td>
        <td class="px-3 py-2">
          <button class="btn-detail px-3 py-1 rounded bg-slate-800 text-white print-hide" data-id="${item.teacher_code}" type="button">Chi tiết</button>
        </td>
      </tr>
    `;
    }

    async function loadReport() {
        const btn = $("#btn-load");
        const tbBody = $("#tb-body");
        const fSubject = $("#f-subject");
        const fClass = $("#f-class");
        const fDay = $("#f-day");
        const fSession = $("#f-session");

        if (!tbBody) return;

        // UI state
        if (btn) {
            btn.disabled = true;
            btn.textContent = "Đang tải…";
        }
        setMsg("");

        try {
            const params = new URLSearchParams();
            if (fSubject && fSubject.value.trim())
                params.set("subject", fSubject.value.trim());
            if (fClass && fClass.value.trim())
                params.set("class_name", fClass.value.trim());
            if (fDay && fDay.value) params.set("day_of_week", fDay.value);
            if (fSession && fSession.value) params.set("session", fSession.value);

            const url = `${API}?${params.toString()}`;
            console.debug("[teacher-load] fetch:", url);
            const res = await fetch(url);

            if (!res.ok) {
                const err = await res
                    .json()
                    .catch(() => ({ detail: res.statusText || "HTTP Error" }));
                console.error("[teacher-load] HTTP error", res.status, err);
                tbBody.innerHTML = `<tr><td colspan="11" class="px-3 py-3 text-rose-600 border-gray-400">Không tải được báo cáo: ${err.detail || res.statusText}</td></tr>`;
                setMsg(`Lỗi: ${err.detail || res.statusText}`, false);
                return;
            }

            const data = await res.json();
            console.debug("[teacher-load] data:", data);

            tbBody.innerHTML =
                (data && data.length
                    ? data.map(rowHTML).join("")
                    : `<tr><td colspan="11" class="px-3 py-3 text-slate-500 border-gray-400">Không có dữ liệu.</td></tr>`);
            setMsg(`Tổng số ${data?.length || 0} giáo viên.`);
        } catch (e) {
            console.error("[teacher-load] exception:", e);
            setMsg(`Lỗi kết nối: ${e?.message || e}`, false);
            const tbBody = $("#tb-body");
            if (tbBody)
                tbBody.innerHTML = `<tr><td colspan="11" class="px-3 py-3 text-rose-600 border-gray-400">Không tải được báo cáo (network).</td></tr>`;
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = "Tải báo cáo";
            }
        }
    }

    function bindFilterSearch() {
        const sText = $("#s-text");
        if (!sText) return;
        sText.addEventListener("input", () => {
            const q = (sText.value || "").toLowerCase().trim();
            $$("#tb-body tr").forEach((tr) => {
                const text = tr.innerText.toLowerCase();
                tr.style.display = text.includes(q) ? "" : "none";
            });
        });
    }

    function bindDetailModal() {
        const tbBody = $("#tb-body");
        const modal = $("#detail");
        const btnClose = $("#btn-close");
        const detailTitle = $("#detail-title");
        const detailBody = $("#detail-body");

        safeBind(tbBody, "click", async (e) => {
            const btn = e.target.closest(".btn-detail");
            if (!btn) return;
            const id = btn.getAttribute("data-id");
            try {
                const res = await fetch(
                    `${API_DETAIL}?teacher_code=${encodeURIComponent(id)}`
                );
                if (!res.ok) {
                    const err = await res
                        .json()
                        .catch(() => ({ detail: res.statusText || "HTTP Error" }));
                    alert("Không tải được chi tiết: " + (err.detail || res.statusText));
                    return;
                }
                const d = await res.json();
                if (detailTitle)
                    detailTitle.textContent = `${d.teacher_code} - ${d.teacher_name} | Tổng: ${d.total_periods} | Quota: ${d.capacity}`;
                if (detailBody)
                    detailBody.innerHTML = (d.details || [])
                        .map(
                            (r) => `
            <tr class="border-b">
              <td class="px-3 py-2">${r.class_name}</td>
              <td class="px-3 py-2">${r.subject_code} - ${r.subject_name}</td>
              <td class="px-3 py-2">${r.day_of_week}</td>
              <td class="px-3 py-2">${r.session}</td>
              <td class="px-3 py-2">${r.period}</td>
              <td class="px-3 py-2">${r.slot_id}</td>
            </tr>`
                        )
                        .join("");
                if (modal) modal.classList.remove("hidden");
            } catch (e) {
                console.error("[teacher-load] detail error:", e);
                alert("Lỗi mạng khi tải chi tiết.");
            }
        });

        safeBind(btnClose, "click", () => modal && modal.classList.add("hidden"));
        safeBind(modal, "click", (e) => {
            if (e.target === modal) modal.classList.add("hidden");
        });
    }

    // function bindDownloadReport() {
    //     const downloadBtn = $("#downloadReport");
    //     safeBind(downloadBtn, "click", function () {
    //         const fSubject = $("#f-subject");
    //         const fClass = $("#f-class");
    //         const fDay = $("#f-day");
    //         const fSession = $("#f-session");
    //         const searchValue = $("#s-text")?.value?.trim();

    //         const params = new URLSearchParams();
    //         if (fSubject && fSubject.value.trim())
    //             params.set("subject", fSubject.value.trim());
    //         if (fClass && fClass.value.trim())
    //             params.set("class_name", fClass.value.trim());
    //         if (fDay && fDay.value) params.set("day_of_week", fDay.value);
    //         if (fSession && fSession.value) params.set("session", fSession.value);
    //         if (searchValue) params.set("searchValue", searchValue);

    //         const url = `http://localhost:8002/api/reports/teacher_load_pdf?${params.toString()}`;
    //         console.debug("[teacher-load] download URL:", url);

    //         fetch(url)
    //             .then(res => {
    //                 if (!res.ok) throw new Error("Không thể tạo báo cáo");
    //                 return res.blob();
    //             })
    //             .then(blob => {
    //                 const link = document.createElement('a');
    //                 link.href = URL.createObjectURL(blob);
    //                 link.download = 'teacher_load_report.pdf';
    //                 link.click();
    //                 URL.revokeObjectURL(link.href);
    //             })
    //             .catch(err => alert(err.message));
    //     });
    // }

    function bindDownloadReport() {
        const btn = $("#downloadReport");
        if (!btn) return;

        btn.addEventListener("click", () => {
            // Gọi in, bảng đã có sẵn trên DOM
            window.print();
        });
    }

    function boot() {
        // Gắn listener nút bấm
        safeBind($("#btn-load"), "click", (e) => {
            e.preventDefault();
            loadReport();
        });

        // Gắn các tiện ích khác
        bindFilterSearch();
        bindDetailModal();
        bindDownloadReport();

        // Tải lần đầu
        loadReport();
    }

    // Đảm bảo chạy sau khi DOM sẵn sàng
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();


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