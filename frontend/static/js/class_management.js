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

async function fetchClasses(page = 1) {
    currentPage = page;
    const skip = (page - 1) * pageSize;
    const searchParam = encodeURIComponent(currentSearch);

    try {
        const res = await fetch(`http://localhost:8002/classes?skip=${skip}&limit=${pageSize}&search=${searchParam}`);
        const result = await res.json();

        const data = result.data;
        // console.log("Fetched classes:", result);
        const total = result.total;
        // const total = 100; // Giả sử tổng số lớp là 100, bạn có thể thay bằng giá trị thực từ backend
        const totalPages = Math.ceil(total / pageSize);

        // render bảng
        const table = document.querySelector("#classTableBody");
        table.innerHTML = "";
        data.forEach(cls => {
            table.innerHTML += `
            <tr class="text-center">
                <td style="vertical-align: middle;">${cls.index}</td>
                <td style="vertical-align: middle;">${cls.name}</td>
                <td style="vertical-align: middle;">${cls.class_advisor || "Chưa có"}</td>
                <td style="vertical-align: middle;">${cls.specialized_class || "Không có"}</td>
                <td style="vertical-align: middle;">${cls.subjects_with_teachers.join("<br>") || "Không có"}</td>
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
            hintText.textContent = `Hiển thị 0 trên tổng số 0 lớp học`;
        } else {
            hintText.textContent = `Hiển thị từ ${startEntry} đến ${endEntry} trên tổng số ${total} lớp học`;
        }

    } catch (err) {
        showToast("Lỗi khi tải danh sách lớp học", "danger");
        console.error(err);
    }
}

function renderPagination(totalPages, currentPage) {
    const container = document.getElementById("pagination");
    container.innerHTML = ""; // Xóa cũ
    container.className = "pagination"; // Đảm bảo đúng class Bootstrap 4

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
                fetchClasses(page);
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
            li.className = "page-item disabled";
            li.innerHTML = `<span class="page-link">...</span>`;
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
            li.className = "page-item disabled";
            li.innerHTML = `<span class="page-link">...</span>`;
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
        const res = await fetch("http://localhost:8002/classes/import", {
            method: "POST",
            body: formData,
        });

        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || "Lỗi khi import file danh sách lớp.");
        }

        const result = await res.json();
        // console.log("result.duplicated: ", result.duplicated)
        showToast(result.message || "Import thành công", "success");
        if (result.duplicated.length > 0) {
            const existed_classes = result.duplicated.join(", ");
            const mes_dup = `Bỏ qua ${result.duplicated.length} lớp đã tồn tại: ${existed_classes}`;
            showToast(mes_dup, "warning");
        }
        
        fetchClasses(); // Load lại danh sách lớp
        fileInput.value = ""; // Reset <input type="file">
        document.getElementById("fileName").value = "";  // Xóa tên file hiển thị
    } catch (error) {
        console.log("error: ", error)
        showToast("Đã xảy ra lỗi khi import file", "danger");
    }
}

function goToPage(page) {
    currentPage = page;
    fetchClasses();
}

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

$(document).ready(function () {

    $("#searchInput").keyup(function () {
        const searchValue = $(this).val().trim();
        currentSearch = searchValue; // Cập nhật biến tìm kiếm
        fetchClasses(1); // Tải lại trang đầu tiên với từ khóa tìm kiếm mới
    });

    $("#pageSizeSelector").click(function () {
        pageSize = parseInt(this.value);
        fetchClasses(1); // Load lại từ trang đầu tiên
    });
});

$(document).ready(fetchClasses(1)); // Load trang đầu tiên khi DOM sẵn sàng

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