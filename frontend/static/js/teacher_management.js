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
        console.log("Fetched teachers:", data);
        const total = result.total;
        // const total = 100; // Giả sử tổng số lớp là 100, bạn có thể thay bằng giá trị thực từ backend
        const totalPages = Math.ceil(total / pageSize);

        // render bảng
        const table = document.querySelector("#teacherTableBody");
        table.innerHTML = "";
        data.forEach(cls => {
            table.innerHTML += `
            <tr class="text-center">
                <td><input type="checkbox" class="row-checkbox" value="${cls.id}"></td>
                <td>${cls.index}</td>
                <td>${cls.name}</td>
                <td>${cls.subject}</td>
                <td>${cls.phone}</td>
                <td>${cls.email}</td>
                <td>${cls.dob}</td>
                <td>${cls.address}</td>
                <td>${cls.max_weekly_lessons}</td>
                <td>${cls.available_morning ? "Có" : "Không"}</td>
                <td>${cls.available_afternoon ? "Có" : "Không"}</td>
                <td>${cls.unavailable_days}</td>
                <td>${cls.status}</td>
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
            hintText.textContent = `Hiển thị 0 trên tổng số 0 giáo viên`;
        } else {
            hintText.textContent = `Hiển thị từ ${startEntry} đến ${endEntry} trên tổng số ${total} giáo viên.`;
        }

    } catch (err) {
        showToast("Lỗi khi tải danh sách giáo viên", "danger");
        console.error(err);
    }
}

function enableEdit(el, teacherId) {
    const row = el.closest("tr");
    const editableIndexes = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]; // Các cột có thể chỉnh sửa
    row.querySelectorAll("td").forEach((td, index) => {
        if (index === 6) {
            // Chỉ cho phép chỉnh sửa ngày sinh
            // console.log("DoB: ", td.textContent.trim())
            const rawText = td.textContent.trim(); // "23/4/2000"
            const [d, m, y] = rawText.split('/');
            const formatted = `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
            console.log("formatted DoB: ", formatted);
            td.innerHTML = `<input type="date" class="form-control form-control-sm" value="${formatted}">`;
        } else if (index === 9 || index === 10) {
            // Chỉ cho phép chỉnh sửa các cột có thể chọn Có/Không
            const currentValue = td.textContent.trim();
            td.innerHTML = `<select class="form-control form-control-sm">
                <option value="true" ${currentValue === "Có" ? "selected" : ""}>Có</option>
                <option value="false" ${currentValue === "Không" ? "selected" : ""}>Không</option>
            </select>`;
        } else if (index === 11) {
            // Chỉ cho phép chỉnh sửa ngày không dạy được
            const currentValue = td.textContent.trim();
            const selectedNames = currentValue
                .split(",")
                .map(name => name.trim());
            console.log("selectedNames:", selectedNames);

            // Tạo một select với nhiều lựa chọn
            td.innerHTML = `
                <select id="people" name="people" multiple>
                    <option value="Thứ 2">Thứ 2</option>
                    <option value="Thứ 3">Thứ 3</option>
                    <option value="Thứ 4">Thứ 4</option>
                    <option value="Thứ 5">Thứ 5</option>
                    <option value="Thứ 6">Thứ 6</option>
                    <option value="Thứ 7">Thứ 7</option>
                </select>`;
            // Gán selected cho từng option trước khi khởi tạo plugin
            const selectEl = td.querySelector('#people');
            for (const option of selectEl.options) {
                if (selectedNames.includes(option.value)) {
                    option.selected = true; // hoặc option.setAttribute("selected", "selected");
                }
            }
            // Khởi tạo plugin multiSelect
            $(function () {
                $('#people').multiSelect();
            });


        } else if (index === 12) {
            // Chỉ cho phép chỉnh sửa trạng thái
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

async function saveEdit(el, teacherId) {
    const row = el.closest("tr");
    const inputs = row.querySelectorAll("td input");
    const name = inputs[1].value;
    const subject = inputs[2].value;
    const phone = inputs[3].value;
    const email = inputs[4].value;
    const dob = inputs[5].value;
    // Chuyển đổi định dạng ngày sinh từ "dd/mm/yyyy" sang "yyyy-mm-dd"
    const [y, m, d] = dob.split('-');
    dob_formated = `${d}/${m}/${y}`; // → "23/04/2000"
    const address = inputs[6].value;
    const maxWeeklyLessons = inputs[7].value;
    const availableMorning = inputs[8].value === "Có";
    const availableAfternoon = inputs[9].value === "Có";
    const unavailableDays = inputs[10].value.split(",").map(d => d.trim()); // Chuyển đổi chuỗi thành mảng
    const status = inputs[11].value;
    const updatedValues = {
        name: name,
        subject: subject,
        phone: phone,
        email: email,
        dob: dob_formated,
        address: address,
        status: status,
        max_weekly_lessons: parseInt(maxWeeklyLessons) || 18, // Mặc định là 18 nếu không nhập
        available_morning: availableMorning, // Chuyển đổi từ "Có" hoặc "Không" thành boolean
        available_afternoon: availableAfternoon, // Chuyển đổi từ "Có" hoặc "Không" thành boolean
        unavailable_days: unavailableDays   // Mảng ngày không dạy được
    };
    // console.log("Updated values:", updatedValues);
    if (!validateTeacherData(name, subject, phone, email, dob_formated, address)) return;

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
        if (idx === 1) td.innerHTML = updatedValues.name;
        if (idx === 2) td.innerHTML = updatedValues.subject;
        if (idx === 3) td.innerHTML = updatedValues.phone;
        if (idx === 4) td.innerHTML = updatedValues.email;
        if (idx === 5) td.innerHTML = updatedValues.dob;
        if (idx === 6) td.innerHTML = updatedValues.address;
        if (idx === 7) td.innerHTML = updatedValues.max_weekly_lessons;
        if (idx === 8) td.innerHTML = updatedValues.available_morning == "true" ? "Có" : "Không";
        if (idx === 9) td.innerHTML = updatedValues.available_afternoon == "true" ? "Có" : "Không";
        if (idx === 10) td.innerHTML = updatedValues.unavailable_days.join(", "); // Hiển thị mảng ngày không dạy được
        if (idx === 11) td.innerHTML = updatedValues.status;
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

async function addTeacher() {
    const name = document.getElementById("teacherName").value.trim();
    const subject = document.getElementById("teacherSubject").value.trim();
    const phone = document.getElementById("teacherPhone").value.trim();
    const email = document.getElementById("teacherEmail").value.trim();
    const dob = document.getElementById("teacherDoB").value.trim();
    const address = document.getElementById("teacherAddress").value.trim();

    if (!validateTeacherData(name, subject, phone, email, dob, address)) return;

    try {
        const response = await fetch("http://localhost:8000/teachers", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name: name,
                subject: subject,
                phone: phone,
                email: email,
                dob: dob,
                address: address
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
            const mes_dup = `Bỏ qua ${result.duplicated.length} giáo viên đã tồn tại: ${existed_teachers}`;
            showToast(mes_dup, "warning");
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

function validateTeacherData(name, subject, phone, email, dob, address) {
    // Kiểm tra tên
    if (!name || name.trim() === "") {
        showToast("Tên giáo viên không được để trống", "danger");
        return false;
    }

    // Kiểm tra môn dạy
    if (!subject || subject.trim() === "") {
        showToast("Môn dạy không được để trống", "danger");
        return false;
    }

    // Kiểm tra số điện thoại (10 chữ số, chỉ chứa số)
    const phoneRegex = /^[0-9]{10}$/;
    if (!phone || !phoneRegex.test(phone)) {
        showToast("Số điện thoại không hợp lệ (phải gồm 10 chữ số)", "danger");
        return false;
    }

    // Kiểm tra email (định dạng cơ bản)
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailRegex.test(email)) {
        showToast("Email không hợp lệ", "danger");
        return false;
    }

    // Kiểm tra ngày sinh
    console.log("dob: ", dob)
    if (!dob || isNaN(Date.parse(dob))) {
        showToast("Ngày sinh không hợp lệ", "danger");
        return false;
    }

    // Kiểm tra địa chỉ
    if (!address || address.trim() === "") {
        showToast("Địa chỉ không được để trống", "danger");
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
        `Bạn có chắc chắn muốn xóa giáo viên "${teacherName}" không?`;
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
        showToast("Vui lòng chọn ít nhất 1 giáo viên để xóa.", "danger")
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
        showToast("Xóa giáo viên thành công", "success");  // màu xanh

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
