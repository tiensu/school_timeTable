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

async function fetchTeachers(page = 1) {
    currentPage = page;
    const skip = (page - 1) * pageSize;
    const searchParam = encodeURIComponent(currentSearch);

    try {
        const res = await fetch(`http://localhost:8000/teachers?skip=${skip}&limit=${pageSize}&search=${searchParam}`);
        const result = await res.json();

        const data = result.data;
        console.log("Fetched teachers:", result);
        const total = result.total;
        // const total = 100; // Giả sử tổng số lớp là 100, bạn có thể thay bằng giá trị thực từ backend
        const totalPages = Math.ceil(total / pageSize);

        // render bảng
        const table = document.querySelector("#teacherTableBody");
        table.innerHTML = "";
        data.forEach(cls => {
            table.innerHTML += `
            <tr teacher="text-center">
                <td><input type="checkbox" teacher="row-checkbox" value="${cls.id}"></td>
                <td>${cls.index}</td>
                <td>${cls.name}</td>
                <td>${cls.grade}</td>
                <td>${cls.student_count}</td>
                <td>
                <a href="javascript:void(0)" teacher="edit" onclick="enableEdit(this, ${cls.id})">
                    <i teacher="material-icons" data-toggle="tooltip" title="Sửa">&#xE254;</i>
                </a>
                <a href="javascript:void(0)" teacher="save" style="display: none;" onclick="saveEdit(this, ${cls.id})">
                    <i teacher="material-icons" data-toggle="tooltip" title="Lưu">&#xE161;</i>
                </a>
                <a href="#" teacher="delete" onclick="showDeleteModal(${cls.id}, '${cls.name}')"><i teacher="material-icons" title="Delete">&#xE872;</i>
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

function enableEdit(el, teacherId) {
    const row = el.closest("tr");
    row.querySelectorAll("td:not(:first-child):not(:last-child)").forEach(td => {
        const value = td.textContent;
        td.innerHTML = `<input type="text" teacher="form-control form-control-sm" value="${value}">`;
    });

    // row.querySelector(".edit").teacherList.add("d-none");
    // row.querySelector(".save").teacherList.remove("d-none");
    row.querySelector(".edit").style.display = "none";
    row.querySelector(".save").style.display = "inline-block";
    row.querySelector(".delete").style.display = "none";
}

async function saveEdit(el, teacherId) {
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
    // console.log("Updated values:", updatedValues);
    if (!validateTeacherData(name, grade, student_count)) return;

    const res = await fetch(`http://localhost:8000/teachers/${teacherId}`, {
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
        if (idx === 0) td.innerHTML = updatedValues.name;
        if (idx === 1) td.innerHTML = updatedValues.grade;
        if (idx === 2) td.innerHTML = updatedValues.student_count;
    });

    row.querySelector(".edit").style.display = "inline-block";
    row.querySelector(".save").style.display = "none";
    row.querySelector(".delete").style.display = "inline-block";
}

function renderPagination(totalPages, currentPage) {
    const container = document.getElementById("pagination");
    container.innerHTML = ""; // Xóa cũ
    container.teacherName = "pagination"; // Đảm bảo đúng teacher Bootstrap 4

    // Tạo 1 nút trang (li > a)
    function createPageButton(text, page, isActive = false, isDisabled = false) {
        const li = document.createElement("li");
        li.teacherName = "page-item";
        if (isActive) li.teacherList.add("active");
        if (isDisabled) li.teacherList.add("disabled");

        const a = document.createElement("a");
        a.teacherName = "page-link";
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

async function addTeacher() {
    const name = document.getElementById("teacherName").value.trim();
    const grade = parseInt(document.getElementById("subject").value);
    const size = parseInt(document.getElementById("phone").value);

    if (!validateTeacherData(name, grade, size)) return;

    try {
        const response = await fetch("http://localhost:8000/teachers", {
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
            throw new Error(error.detail || "Lỗi khi thêm lớp.");
        }

        // Đóng modal (nếu dùng Bootstrap 3)
        $("#addTeacherModal").modal("hide");

        // Reset form
        document.getElementById("teacherForm").reset();

        // Refresh bảng
        fetchTeachers();
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
        const res = await fetch("http://localhost:8000/teachers/import", {
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
            const existed_teachers = result.duplicated.join(", ");
            const mes_dup = `Bỏ qua ${result.duplicated.length} lớp đã tồn tại: ${existed_teachers}`;
            showToast(mes_dup, "warning");
        }
        
        fetchTeachers(); // Load lại danh sách lớp
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

function validateTeacherData(name, grade, student_count) {
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

async function deleteTeacherById(teacherId) {

    try {
        const res = await fetch(`http://localhost:8000/teachers/${teacherId}`, {
            method: 'DELETE'
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || "Lỗi khi xóa lớp.");
        }
        const result = await res.json();
        // console.log("result: ", result)
        showToast(result.message, "success");
        fetchTeachers(currentPage); // reload lại bảng
    } catch (err) {
        console.error("❌ Xóa lớp thất bại:", err);
        alert("Lỗi: " + err.message);
    }
}

function showDeleteModal(teacherId, teacherName) {
    document.getElementById("deleteTeacherId").value = teacherId;
    document.getElementById("deleteMessage").textContent =
        `Bạn có chắc chắn muốn xóa lớp "${teacherName}" không?`;
    $("#deleteSingleModal").modal("show");
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
  }, 3000);
}


async function deleteSelectedTeachers() {
    const selectedIds = Array.from(document.querySelectorAll('.row-checkbox:checked'))
        .map(cb => parseInt(cb.value));

    if (selectedIds.length === 0) {
        // alert("Vui lòng chọn ít nhất 1 lớp để xóa.");
        showToast("Vui lòng chọn ít nhất 1 lớp để xóa.", "danger")
        return;
    }
    console.log("selectedIds:", selectedIds)
    try {
        const res = await fetch("http://localhost:8000/teachers/delete-multiple", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ teacher_ids: selectedIds })
        });

        const result = await res.json();
        // Đóng modal
        $('#confirmDeleteModal').modal('hide');
        showToast("Xóa lớp thành công", "success");  // màu xanh

        $("#selectAll").prop("checked", false);

        fetchTeachers(currentPage);  // Refresh danh sách
    } catch (err) {
        showToast("Xảy ra lỗi khi xóa", "danger");   // màu đỏ
    }
}

$(document).ready(function () {
    $("#confirmDeleteBtn").click(function () {
        deleteSelectedTeachers()
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
        fetchTeachers(1); // Tải lại trang đầu tiên với từ khóa tìm kiếm mới
    });

    $("#confirmDeleteSingleBtn").click(function () {
        const teacherId = document.getElementById("deleteTeacherId").value;
        deleteTeacherById(teacherId);
        $("#deleteSingleModal").modal("hide");
    });

    $("#pageSizeSelector").click(function () {
        pageSize = parseInt(this.value);
        fetchTeachers(1); // Load lại từ trang đầu tiên
    });
});

$(document).ready(fetchTeachers(1)); // Load trang đầu tiên khi DOM sẵn sàng
