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
        const res = await fetch(`http://localhost:8000/classes?skip=${skip}&limit=${pageSize}&search=${searchParam}`);
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
                <td><input type="checkbox" class="row-checkbox" value="${cls.id}"></td>
                <td>${cls.index}</td>
                <td>${cls.name}</td>
                <td>${cls.grade}</td>
                <td>${cls.student_count}</td>
                <td>
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
            hintText.textContent = `Hiển thị 0 trên tổng số 0 lớp học`;
        } else {
            hintText.textContent = `Hiển thị từ ${startEntry} đến ${endEntry} trên tổng số ${total} lớp học`;
        }

    } catch (err) {
        showToast("Lỗi khi tải danh sách lớp học", "danger");
        console.error(err);
    }
}

function enableEdit(el, classId) {
    const row = el.closest("tr");
    const editableIndexes = [2, 3, 4]; // Chỉ edit Name, Grade, Student Count
    row.querySelectorAll("td").forEach((td, index) => {
        if (editableIndexes.includes(index)) {
            const value = td.textContent.trim();
            td.innerHTML = `<input type="text" class="form-control form-control-sm" value="${value}">`;
        }
    });

    row.querySelector(".edit").style.display = "none";
    row.querySelector(".save").style.display = "inline-block";
    row.querySelector(".delete").style.display = "none";
}

async function saveEdit(el, classId) {
    const row = el.closest("tr");
    const inputs = row.querySelectorAll("td input");
    const name = inputs[1].value;
    const grade = parseInt(inputs[2].value);
    const student_count = parseInt(inputs[3].value);
    const updatedValues = {
        name: name,
        grade: grade,
        student_count: student_count
    };
    console.log("Updated values:", updatedValues);
    if (!validateClassData(name, grade, student_count)) return;

    const res = await fetch(`http://localhost:8000/classes/${classId}`, {
        method: "PUT",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedValues)
    });
    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Lỗi khi xóa lớp.");
    }
    const result = await res.json();
    showToast(result.message || "Đã cập nhật lớp");

    // Set lại từng cell bằng đúng giá trị bạn vừa dùng
    // Quay lại hiển thị bình thường
    row.querySelectorAll("td:not(:first-child):not(:last-child)").forEach((td, idx) => {
        if (idx === 1) td.innerHTML = updatedValues.name;
        if (idx === 2) td.innerHTML = updatedValues.grade;
        if (idx === 3) td.innerHTML = updatedValues.student_count;
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

async function addClass() {
    const name = document.getElementById("className").value.trim();
    const grade = parseInt(document.getElementById("classGrade").value);
    const size = parseInt(document.getElementById("classSize").value);

    if (!validateClassData(name, grade, size)) return;

    try {
        const response = await fetch("http://localhost:8000/classes", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name: name,
                grade: grade,
                student_count: size
            })
        });

        if (!response.ok) {
            const error = await response.json();
            showToast(error.detail || "Lỗi khi thêm lớp.", "danger");
            return;
        }

        // Đóng modal (nếu dùng Bootstrap 3)
        $("#addClassModal").modal("hide");

        // Reset form
        document.getElementById("classForm").reset();

        // Refresh bảng
        fetchClasses();
    } catch (err) {
        console.error("❌ Thêm lớp thất bại:", err);
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
        const res = await fetch("http://localhost:8000/classes/import", {
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

function validateClassData(name, grade, student_count) {
    if (!name || name.trim() === "") {
        showToast("Tên lớp không được để trống", "danger");
        return false;
    }
    if (isNaN(grade) || grade < 1 || grade > 12) {
        showToast("Khối lớp phải là số từ 1 đến 12", "danger");
        return false;
    }
    if (isNaN(student_count) || student_count < 1 || student_count > 100) {
        showToast("Sĩ số lớp phải là số từ 1 đến 100", "danger");
        return false;
    }
    return true;
}

async function deleteClassById(classId) {

    try {
        const res = await fetch(`http://localhost:8000/classes/${classId}`, {
            method: 'DELETE'
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || "Lỗi khi xóa lớp.");
        }
        const result = await res.json();
        // console.log("result: ", result)
        showToast(result.message, "success");
        fetchClasses(currentPage); // reload lại bảng
    } catch (err) {
        console.error("❌ Xóa lớp thất bại:", err);
        alert("Lỗi: " + err.message);
    }
}

function showDeleteModal(classId, className) {
    document.getElementById("deleteClassId").value = classId;
    document.getElementById("deleteMessage").textContent =
        `Bạn có chắc chắn muốn xóa lớp "${className}" không?`;
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

async function deleteSelectedClasses() {
    const selectedIds = Array.from(document.querySelectorAll('.row-checkbox:checked'))
        .map(cb => parseInt(cb.value));

    if (selectedIds.length === 0) {
        // alert("Vui lòng chọn ít nhất 1 lớp để xóa.");
        showToast("Vui lòng chọn ít nhất 1 lớp để xóa.", "danger")
        return;
    }
    console.log("selectedIds:", selectedIds)
    try {
        const res = await fetch("http://localhost:8000/classes/delete-multiple", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ class_ids: selectedIds })
        });

        const result = await res.json();
        // Đóng modal
        $('#confirmDeleteModal').modal('hide');
        showToast("Xóa lớp thành công", "success");  // màu xanh

        $("#selectAll").prop("checked", false);

        fetchClasses(currentPage);  // Refresh danh sách
    } catch (err) {
        showToast("Xảy ra lỗi khi xóa", "danger");   // màu đỏ
    }
}

$(document).ready(function () {
    $("#confirmDeleteBtn").click(function () {
        deleteSelectedClasses()
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
        fetchClasses(1); // Tải lại trang đầu tiên với từ khóa tìm kiếm mới
    });

    $("#confirmDeleteSingleBtn").click(function () {
        const classId = document.getElementById("deleteClassId").value;
        deleteClassById(classId);
        $("#deleteSingleModal").modal("hide");
    });

    $("#pageSizeSelector").click(function () {
        pageSize = parseInt(this.value);
        fetchClasses(1); // Load lại từ trang đầu tiên
    });
});

$(document).ready(fetchClasses(1)); // Load trang đầu tiên khi DOM sẵn sàng
