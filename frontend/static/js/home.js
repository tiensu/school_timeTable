// Kiểm tra token khi load Dashboard
const token = localStorage.getItem("access_token");
if (!token) {
    window.location.href = "/login.html";  // hoặc URL login của bạn
}

// Hiển thị tên user
const username = localStorage.getItem("username") || "";
const role = localStorage.getItem("role") || "";
const currentUserEl = document.getElementById("currentUser");
if (currentUserEl) {
    currentUserEl.textContent = `${username} (${role})`;
}

// Logout
const logoutBtn = document.getElementById("btnLogout");
if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("username");
        localStorage.removeItem("role");
        localStorage.removeItem("menu");
        window.location.href = "/login.html"; // hoặc route login bạn dùng
    });
}

// Phân quyền
// const role = localStorage.getItem("role") || "";
// const token = localStorage.getItem("access_token");

if (!token) {
    window.location.href = "/login.html";
}

if (role === "user") {
    // Disable các tile bị hạn chế
    document.querySelectorAll('[data-role="restricted"]').forEach(tile => {
        tile.classList.add("disabled-tile");
        tile.addEventListener("click", e => e.preventDefault());
        tile.setAttribute("title", "Bạn không có quyền thực hiện chức năng này");
        tile.setAttribute("data-bs-toggle", "tooltip");
    });

    // Kích hoạt tooltip Bootstrap
    const tooltipList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipList.forEach(el => new bootstrap.Tooltip(el));
}

$(document).ready(function () {
    // Handle reset data
    $("#btnResetData").on("click", function () {
        document.getElementById("deleteMessage").textContent =
            `Bạn có chắc chắn muốn xóa tất cả dữ liệu không?`;
        $("#resetDataDialog").modal("show");
    });
    // Perform reset data
    $("#confirmResetDataBtn").on("click", function () {
        // Perform reset data
        $("#resetDataDialog").modal("hide");
        const $btn = $(this);
        const $spinner = $("#spinnerReset");
        const $text = $("#btnResetText");

        // Hiển thị trạng thái In Progress
        $btn.prop("disabled", true);
        $spinner.removeClass("d-none");
        $text.text(" Đang xử lý...");

        $.ajax({
            url: "http://localhost:8002/api/system/reset_data",
            type: "DELETE",
            headers: {
                "Authorization": "Bearer " + (localStorage.getItem("access_token") || "")
            },
            contentType: "application/json",
            success: function (data) {
                // Sau khi xóa xong, reload trang để cập nhật lại dữ liệu
                // location.reload();
                showToast("Đã xóa tất cả dữ liệu.", "success")
            },
            error: function (xhr) {
                const errorMsg = xhr.responseJSON?.detail || "Xóa dữ liệu thất bại. Vui lòng thử lại.";
                alert("❌ " + errorMsg);
            },
            complete: function () {
                // Trường hợp lỗi, kết thúc trạng thái xử lý
                $btn.prop("disabled", false);
                $spinner.addClass("d-none");
                $text.html('<i class="bi bi-building-x"></i> Reset Dữ Liệu');
            }
        });
    });

    // Handle import data
    $("#btnImportData").on("click", function () {
        $("#importFiles").click();
    });

    $("#importFiles").on("change", function (e) {
        const requiredFiles = {
            "classes_information.xlsx": "classes_information",
            "subjects_information.xlsx": "subjects_information",
            "teachers_information.xlsx": "teachers_information",
            "timetable_slots_information.xlsx": "timetable_slots_information"
        };

        const files = Array.from(e.target.files);

        // Map filename -> file
        const fileObjMap = {};
        files.forEach(file => {
            fileObjMap[file.name] = file;
        });

        // Kiểm tra thiếu file
        const uploadedFilenames = Object.keys(fileObjMap);
        const requiredFilenames = Object.keys(requiredFiles);
        const missing = requiredFilenames.filter(filename => !uploadedFilenames.includes(filename));

        if (missing.length > 0) {
            showToast("❌ Thiếu file: " + missing.join(", "), "danger");
            return;
        }

        // Tạo FormData và gán đúng key tên tham số backend
        const formData = new FormData();
        for (const [filename, backendFieldName] of Object.entries(requiredFiles)) {
            formData.append(backendFieldName, fileObjMap[filename]);
        }

        $.ajax({
            url: "http://localhost:8002/api/system/import_data",
            type: "POST",
            data: formData,
            processData: false,
            contentType: false,
            headers: {
                "Authorization": "Bearer " + (localStorage.getItem("access_token") || "")
            },
            success: function (res) {
                showToast("✅ Import thành công!", "success");
                // location.reload();
            },
            error: function (xhr) {
                const err = xhr.responseJSON?.detail || "Import thất bại.";
                showToast("❌ " + err, "danger");
            }
        });
        e.target.value = null; // Cho phép chọn lại cùng file lần sau
    });

});

function showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast-message bg-${type}`;

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
    }, 3000);
}

