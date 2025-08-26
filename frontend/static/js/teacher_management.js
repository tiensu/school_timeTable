const token = localStorage.getItem("access_token");
if (!token) {
    window.location.href = "/login.html";
}

let selectedFile = null;
let currentPage = 1;
let pageSize = 5;
let currentSearch = ""; // Biến để lưu từ khoá tìm kiếm

function handleFileSelected(input) {
    if (input.files.length > 0) {
        selectedFile = input.files[0];
        document.getElementById("fileName").value = selectedFile.name;
    }
}

function formatSlot(slotStr) {
    // slotStr dạng: "Saturday-morning-1"
    const days = {
        "Monday": "Thứ 2",
        "Tuesday": "Thứ 3",
        "Wednesday": "Thứ 4",
        "Thursday": "Thứ 5",
        "Friday": "Thứ 6",
        "Saturday": "Thứ 7",
        "Sunday": "Chủ nhật"
    };
    const sessions = {
        "morning": "sáng",
        "afternoon": "chiều"
    };
    const [day, session, period] = slotStr.split("-");
    return `Tiết ${period}, ${sessions[session] || session} ${days[day] || day}`;
}

// Hàm gom slot đủ 5 tiết thành 1 dòng
function formatSlotsDisplay(slots) {
    // Gom các slot theo ngày/buổi
    const slotMap = {};
    slots.forEach(slotStr => {
        const [day, session, period] = slotStr.split("-");
        const key = `${day}-${session}`;
        if (!slotMap[key]) slotMap[key] = [];
        slotMap[key].push(period);
    });

    const days = {
        "Monday": "Thứ 2",
        "Tuesday": "Thứ 3",
        "Wednesday": "Thứ 4",
        "Thursday": "Thứ 5",
        "Friday": "Thứ 6",
        "Saturday": "Thứ 7",
        "Sunday": "Chủ nhật"
    };
    const sessions = {
        "morning": "Sáng",
        "afternoon": "Chiều"
    };

    const result = [];
    for (const key in slotMap) {
        const [day, session] = key.split("-");
        if (slotMap[key].length === 5) {
            result.push(`${sessions[session] || session} ${days[day] || day}`);
        } else {
            slotMap[key].forEach(period => {
                result.push(`Tiết ${period}, ${sessions[session] || session} ${days[day] || day}`);
            });
        }
    }
    return result;
}

async function fetchTeachers(page = 1) {
    currentPage = page;
    const skip = (page - 1) * pageSize;
    const searchParam = encodeURIComponent(currentSearch);

    try {
        const res = await fetch(`http://localhost:8002/teachers?skip=${skip}&limit=${pageSize}&search=${searchParam}`);
        const result = await res.json();
        let data = result.data;
        // Sắp xếp giáo viên theo tên alphabet
        data = data.sort((a, b) => a.name.localeCompare(b.name, 'vi', {sensitivity: 'base'}));
        const total = result.total;
        const totalPages = Math.ceil(total / pageSize);

        // render bảng
        const table = document.querySelector("#teacherTableBody");
        table.innerHTML = "";
        data.forEach((cls, idx) => {
            table.innerHTML += `
            <tr class="text-center">
                <td style="vertical-align: middle;">${skip + idx + 1}</td>
                <td style="vertical-align: middle;">${cls.code.substring(10)}</td>
                <td style="vertical-align: middle;">${cls.name}</td>
                <td style="vertical-align: middle;">${cls.class_advisor}</td>
                <td style="vertical-align: middle;">${cls.subj_class.join(",<br>")}</td>
                <td style="vertical-align: middle;">${cls.max_weekly_lessons}</td>
                <td style="vertical-align: middle;">${cls.max_weekly_x > 0? cls.max_weekly_x : ""}</td>
                <td style="white-space: pre-line; vertical-align: middle;">${
                    formatSlotsDisplay(cls.unavailable_slots).join("<br>")
                }</td>

            </tr>
        `;
        });

        // render phân trang
        renderPagination(totalPages, currentPage);

        // ✅ Cập nhật hint text
        const startEntry = skip + 1;
        const endEntry = Math.min(skip + data.length, total);
        const hintText = document.getElementById("hintText");
        if (total === 0) {
            hintText.textContent = `Hiển thị 0 trên tổng số 0 giáo viên`;
        } else {
            hintText.textContent = `Hiển thị từ ${startEntry} đến ${endEntry} trên tổng số ${total} giáo viên.`;
        }

    } catch (err) {
        showToast("Lỗi khi tải danh sách giáo viên", "danger");
        console.error(err);
    }
}

function renderPagination(totalPages, currentPage) {
    const container = document.getElementById("pagination");
    container.innerHTML = ""; // Xóa cũ
    container.teacherName = "pagination"; // Đảm bảo đúng teacher Bootstrap 4

    // Tạo 1 nút trang (li > a)
    function createPageButton(text, page, isActive = false, isDisabled = false) {
        const li = document.createElement("li");
        li.className = "page-item";
        if (isActive) li.classList.add("active");
        if (isDisabled) li.classList.add("disabled");

        const a = document.createElement("a");
        a.className = "page-link";
        a.href = "#";
        a.textContent = text;
        a.onclick = function (e) {
            e.preventDefault();
            if (!isDisabled && page !== currentPage) {
                fetchTeachers(page);
            }
        };

        li.appendChild(a);
        return li;
    }

    // Previous
    container.appendChild(createPageButton("Previous", currentPage - 1, false, currentPage === 1));

    // Nếu ít trang, hiển thị tất cả
    if (totalPages <= 10) {
        for (let i = 1; i <= totalPages; i++) {
            container.appendChild(createPageButton(i, i, i === currentPage));
        }
    } else {
        // Trang đầu tiên
        container.appendChild(createPageButton(1, 1, currentPage === 1));

        // Dấu ...
        if (currentPage > 4) {
            const li = document.createElement("li");
            li.teacherName = "page-item disabled";
            li.innerHTML = `<span teacher="page-link">...</span>`;
            container.appendChild(li);
        }

        // Các nút ở giữa
        const start = Math.max(2, currentPage - 1);
        const end = Math.min(totalPages - 1, currentPage + 1);

        for (let i = start; i <= end; i++) {
            container.appendChild(createPageButton(i, i, i === currentPage));
        }

        // Dấu ...
        if (currentPage < totalPages - 3) {
            const li = document.createElement("li");
            li.teacherName = "page-item disabled";
            li.innerHTML = `<span teacher="page-link">...</span>`;
            container.appendChild(li);
        }

        // Trang cuối
        container.appendChild(createPageButton(totalPages, totalPages, currentPage === totalPages));
    }

    // Next
    container.appendChild(createPageButton("Next", currentPage + 1, false, currentPage === totalPages));
}

async function uploadExcel() {
    const fileInput = document.getElementById("excelFile");
    const file = fileInput.files[0];
    if (!file) {
        showToast("Vui lòng chọn file Excel", "danger");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("http://localhost:8002/teachers/import", {
            method: "POST",
            body: formData,
        });

        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || "Lỗi khi import file danh sách lớp.");
        }

        const result = await res.json();
        console.log("result import: ", result)
        showToast(result.message || "Import thành công", "success");
        if (result.duplicated.length > 0) {
            result.duplicated.forEach(dup => {
                showToast(dup, "warning");
            });
        }
        if (result.errors.length > 0) {
            result.errors.forEach(error => {
                showToast(error, "danger");
            });
        }

        fetchTeachers(); // Load lại danh sách giáo viên
        fileInput.value = ""; // Reset <input type="file">
        document.getElementById("fileName").value = "";  // Xóa tên file hiển thị
    } catch (error) {
        console.log("error: ", error)
        showToast("Đã xảy ra lỗi khi import file", "danger");
    }
}

function goToPage(page) {
    currentPage = page;
    fetchTeachers();
}

function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.teacherName = `toast-message bg-${type}`;

    // Màu nền theo loại thông báo
    let bgColor = "#28a745"; // success
    if (type === "danger") bgColor = "#dc3545";
    else if (type === "warning") bgColor = "#ffc107";

    toast.innerHTML = `
    <div style="
      min-width: 200px;
      margin-top: 10px;
      padding: 12px 20px;
      color: black;
      border-radius: 5px;
      font-size: 14px;
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
    }, type === "danger" || "warning" ? 10000 : 3000); // Thông báo lỗi hiển thị lâu hơn
}


$(document).ready(function () {

    $("#searchInput").keyup(function () {
        const searchValue = $(this).val().trim();
        currentSearch = searchValue; // Cập nhật biến tìm kiếm
        fetchTeachers(1); // Tải lại trang đầu tiên với từ khóa tìm kiếm mới
    });

    $("#pageSizeSelector").click(function () {
        pageSize = parseInt(this.value);
        fetchTeachers(1); // Load lại từ trang đầu tiên
    });
});

$(document).ready(fetchTeachers(1)); // Load trang đầu tiên khi DOM sẵn sàng

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
