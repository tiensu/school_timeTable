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

async function fetchSubjects(page = 1) {
    currentPage = page;
    const skip = (page - 1) * pageSize;
    const searchParam = encodeURIComponent(currentSearch);

    try {
        const res = await fetch(`http://localhost:8002/subjects?skip=${skip}&limit=${pageSize}&search=${searchParam}`);
        const result = await res.json();

        const data = result.data;
        console.log("Fetched subjects:", result);
        const total = result.total;
        // const total = 100; // Giả sử tổng số môn học là 100, bạn có thể thay bằng giá trị thực từ backend
        const totalPages = Math.ceil(total / pageSize);

        // render bảng
        const table = document.querySelector("#classTableBody");
        table.innerHTML = "";
        data.forEach(cls => {
            table.innerHTML += `
            <tr class="text-center">
                <td><input type="checkbox" class="row-checkbox" value="${cls.id}"></td>
                <td style="vertical-align: middle;">${cls.index}</td>
                <td style="vertical-align: middle;">${cls.name}</td>
                <td style="vertical-align: middle;">${cls.code}</td>
                <td style="vertical-align: middle;">${cls.lesson_per_week}</td>
                <td style="vertical-align: middle;">${cls.teachers_name.join("<br>") || "Không có"}</td>
                <td style="vertical-align: middle;">
                <a href="javascript:void(0)" class="edit" onclick="enableEdit(this, ${cls.id})">
                    <i class="material-icons" data-toggle="tooltip" title="Sửa">&#xE254;</i>
                </a>
                <a href="javascript:void(0)" class="save" style="display: none;" onclick="saveEdit(this, ${cls.id})">
                    <i class="material-icons" data-toggle="tooltip" title="Lưu">&#xE161;</i>
                </a>
                <a href="#" class="delete" onclick="showDeleteModal(${cls.id}, '${cls.name}')"><i class="material-icons" title="Delete">&#xE872;</i>
                </a>
                </td>

            </tr>
        `;
        });

        // render phân trang
        renderPagination(totalPages, currentPage);
        
        document.getElementById("selectAll").checked = false;

        // ✅ Cập nhật hint text
        const startEntry = skip + 1;
        const endEntry = Math.min(skip + data.length, total);
        const hintText = document.getElementById("hintText");
        if (total === 0) {
            hintText.textContent = `Hiển thị 0 trên tổng số 0 môn học`;
        } else {
            hintText.textContent = `Hiển thị từ ${startEntry} đến ${endEntry} trên tổng số ${total} môn học`;
        }

    } catch (err) {
        showToast("Lỗi khi tải danh sách môn học", "danger");
        console.error(err);
    }
}

function enableEdit(el, subjectId) {
    const row = el.closest("tr");
    const editableIndexes = [2, 3, 4, 5, 6, 7, 8, 9]; // Chỉ edit Name, Code, Number of Periods, Required, Subject Group, Exam Required, Description, Status
    row.querySelectorAll("td").forEach((td, index) => {
        if (index === 6 || index === 7) {
            td.innerHTML = `<select class="form-control form-control-sm">
                <option value="true" ${td.textContent.trim() === "Có" ? "selected" : ""}>Có</option>
                <option value="false" ${td.textContent.trim() === "Không" ? "selected" : ""}>Không</option>
            </select>`;
        } else if (index === 9) {
            td.innerHTML = `<select class="form-control form-control-sm">
                <option value="active" ${td.textContent.trim() === "Đang dạy" ? "selected" : ""}>Đang dạy</option>
                <option value="inactive" ${td.textContent.trim() === "Tạm dừng" ? "selected" : ""}>Tạm dừng</option>
            </select>`;
        } else if (editableIndexes.includes(index)) {
            const value = td.textContent.trim();
            td.innerHTML = `<input type="text" class="form-control form-control-sm" value="${value}">`;
        }
    });

    row.querySelector(".edit").style.display = "none";
    row.querySelector(".save").style.display = "inline-block";
    row.querySelector(".delete").style.display = "none";
}

async function saveEdit(el, subjectId) {
    const row = el.closest("tr");
    const inputs = row.querySelectorAll("td input");
    const selects = row.querySelectorAll("td select");
    const name = inputs[1].value.trim();
    const code = inputs[2].value.trim();
    const num_periods_per_week = parseInt(inputs[3].value.trim());
    const subject_group = inputs[4].value.trim() || null; // Có thể để trống
    const required = selects[0].value.trim();
    const exam_required = selects[1].value.trim();
    const description = inputs[5].value.trim() || null; // Có thể để trống
    const status = selects[2].value.trim(); // Mặc định là "active"
    const updatedValues = {
        name: name,
        code: code,
        num_periods_per_week: num_periods_per_week,
        required: required,
        subject_group: subject_group,
        exam_required: exam_required,
        description: description,
        status: status
    };
    console.log("Updated values:", updatedValues);
    if (!validateSubjectData(name, code, num_periods_per_week, required, subject_group, exam_required, description, status)) return;

    const res = await fetch(`http://localhost:8002/subjects/${subjectId}`, {
        method: "PUT",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedValues)
    });
    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Lỗi khi cập nhật thông tin môn học.");
    }
    const result = await res.json();
    showToast(result.message || "Đã cập nhật môn học");

    // Set lại từng cell bằng đúng giá trị bạn vừa dùng
    // Quay lại hiển thị bình thường
    row.querySelectorAll("td:not(:first-child):not(:last-child)").forEach((td, idx) => {
        if (idx === 1) td.innerHTML = updatedValues.name;
        if (idx === 2) td.innerHTML = updatedValues.code;
        if (idx === 3) td.innerHTML = updatedValues.num_periods_per_week;
        if (idx === 4) td.innerHTML = updatedValues.subject_group || "";
        if (idx === 5) td.innerHTML = updatedValues.required === "true" ? "Có" : "Không";
        if (idx === 6) td.innerHTML = updatedValues.exam_required === "true" ? "Có" : "Không";
        if (idx === 7) td.innerHTML = updatedValues.description || "";
        if (idx === 8) td.innerHTML = updatedValues.status === "active" ? "Đang dạy" : "Tạm dừng";
    });

    row.querySelector(".edit").style.display = "inline-block";
    row.querySelector(".save").style.display = "none";
    row.querySelector(".delete").style.display = "inline-block";
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
                fetchSubjects(page);
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

async function addSubject() {
    const name = document.getElementById("subjectName").value.trim();
    const code = document.getElementById("subjectCode").value.trim();
    const num_periods_per_week = parseInt(document.getElementById("subjectPeriods").value.trim());
    const required = document.getElementById("subjectRequired").value.trim();
    const subject_group = document.getElementById("subjectGroup").value.trim() || null;
    const exam_required = document.getElementById("subjectExam").value.trim();
    const description = document.getElementById("subjectDescription").value.trim() || null;
    const status = document.getElementById("subjectStatus").value.trim();
    console.log("Adding subject with values:", {
        name, code, num_periods_per_week, required, subject_group, exam_required, description, status
    });

    if (!validateSubjectData(name, code, num_periods_per_week, required, subject_group, exam_required, description, status)) return;

    try {
        const response = await fetch("http://localhost:8002/subjects", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name: name,
                code: code,
                num_periods_per_week: num_periods_per_week,
                required: required,
                subject_group: subject_group,
                exam_required: exam_required,
                description: description,
                status: status
            })
        });

        if (!response.ok) {
            const error = await response.json();
            showToast(error.detail || "Lỗi khi thêm môn học.", "danger");
            return;
        }

        // Đóng modal (nếu dùng Bootstrap 3)
        $("#addSubjectModal").modal("hide");

        // Reset form
        document.getElementById("subjectForm").reset();

        // Refresh bảng
        fetchSubjects();
    } catch (err) {
        console.error("❌ Thêm môn học thất bại:", err);
        alert("Lỗi: " + err.message);
    }
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
        const res = await fetch("http://localhost:8002/subjects/import", {
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
            result.duplicated.forEach(dup => {
                showToast(dup, "warning");
            });
        }
        if (result.errors.length > 0) {
            result.errors.forEach(error => {
                showToast(error, "danger");
            });
        }

        fetchSubjects(); // Load lại danh sách môn học
        fileInput.value = ""; // Reset <input type="file">
        document.getElementById("fileName").value = "";  // Xóa tên file hiển thị
    } catch (error) {
        console.log("error: ", error)
        showToast("Đã xảy ra lỗi khi import file", "danger");
    }
}

function goToPage(page) {
    currentPage = page;
    fetchSubjects();
}

function validateSubjectData(name, code, num_periods_per_week, required, subject_group, exam_required, description, status) {
    if (!name || name.trim() === "") {
        showToast("Tên môn học không được để trống", "danger");
        return false;
    }
    if (!code || code.trim() === "") {
        showToast("Mã môn học không được để trống", "danger");
        return false;
    }
    if (isNaN(num_periods_per_week) || num_periods_per_week < 1) {
        showToast("Số tiết trên tuần phải là số dương", "danger");
        return false;
    }
    if (required === undefined) {
        showToast("Trạng thái bắt buộc không được để trống", "danger");
        return false;
    }
    if (!subject_group || subject_group.trim() === "") {
        showToast("Nhóm môn học không được để trống", "danger");
        return false;
    }
    if (exam_required === undefined) {
        showToast("Trạng thái thi không được để trống", "danger");
        return false;
    }
    if (!description || description.trim() === "") {
        showToast("Mô tả không được để trống", "danger");
        return false;
    }
    if (!status || status.trim() === "") {
        showToast("Trạng thái không được để trống", "danger");
        return false;
    }
    return true;
}

async function deleteSubjectById(subjectId) {

    try {
        const res = await fetch(`http://localhost:8002/subjects/${subjectId}`, {
            method: 'DELETE'
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || "Lỗi khi xóa môn học.");
        }
        const result = await res.json();
        // console.log("result: ", result)
        showToast(result.message, "success");
        fetchSubjects(currentPage); // reload lại bảng
    } catch (err) {
        console.error("❌ Xóa môn học thất bại:", err);
        alert("Lỗi: " + err.message);
    }
}

function showDeleteModal(subjectId, subjectName) {
    document.getElementById("deleteSubjectId").value = subjectId;
    document.getElementById("deleteMessage").textContent =
        `Bạn có chắc chắn muốn xóa môn học "${subjectName}" không?`;
    $("#deleteSingleModal").modal("show");
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

async function deleteSelectedSubjects() {
    const selectedIds = Array.from(document.querySelectorAll('.row-checkbox:checked'))
        .map(cb => parseInt(cb.value));

    if (selectedIds.length === 0) {
        // alert("Vui lòng chọn ít nhất 1 môn học để xóa.");
        showToast("Vui lòng chọn ít nhất 1 môn học để xóa.", "danger")
        return;
    }
    console.log("selectedIds:", selectedIds)
    try {
        const res = await fetch("http://localhost:8002/subjects/delete-multiple", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ subject_ids: selectedIds })
        });

        const result = await res.json();
        // Đóng modal
        $('#confirmDeleteModal').modal('hide');
        showToast("Xóa môn học thành công.", "success");  // màu xanh

        $("#selectAll").prop("checked", false);

        fetchSubjects(currentPage);  // Refresh danh sách
    } catch (err) {
        showToast("Xảy ra lỗi khi xóa môn học.", "danger");   // màu đỏ
    }
}

$(document).ready(function () {
    $("#confirmDeleteBtn").click(function () {
        deleteSelectedSubjects()
    });

    // Khi click vào checkbox "Chọn tất cả"
    $("#selectAll").on("change", function () {
        $(".row-checkbox").prop("checked", this.checked);
    });

    // Khi một checkbox dòng bị thay đổi
    $(document).on("change", ".row-checkbox", function () {
        const all = $(".row-checkbox").length;
        const checked = $(".row-checkbox:checked").length;
        $("#selectAll").prop("checked", all === checked);
    });

    $("#searchInput").keyup(function () {
        const searchValue = $(this).val().trim();
        currentSearch = searchValue; // Cập nhật biến tìm kiếm
        fetchSubjects(1); // Tải lại trang đầu tiên với từ khóa tìm kiếm mới
    });

    $("#confirmDeleteSingleBtn").click(function () {
        const subjectId = document.getElementById("deleteSubjectId").value;
        deleteSubjectById(subjectId);
        $("#deleteSingleModal").modal("hide");
    });

    $("#pageSizeSelector").click(function () {
        pageSize = parseInt(this.value);
        fetchSubjects(1); // Load lại từ trang đầu tiên
    });
});

$(document).ready(fetchSubjects(1)); // Load trang đầu tiên khi DOM sẵn sàng

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
