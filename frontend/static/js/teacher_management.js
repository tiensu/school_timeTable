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
            // console.log("cls.unavailable_slots: ", cls.unavailable_slots);
            table.innerHTML += `
            <tr class="text-center">
                <td><input type="checkbox" class="row-checkbox" value="${cls.id}"></td>
                <td>${cls.index}</td>
                <td>${cls.code}</td>
                <td>${cls.name}</td>
                <td>${cls.subjects.join(", ")}</td>
                <td>${cls.max_weekly_lessons}</td>
                <td>${cls.available_morning ? "Có" : "Không"}</td>
                <td>${cls.available_afternoon ? "Có" : "Không"}</td>
                <td>${cls.unavailable_slots.join(", ")}</td>
                <td>${cls.status === "active" ? "Đang dạy" : "Tạm dừng"}</td>
                <td>
                <a href="javascript:void(0)" class="edit" onclick="enableEdit(this)">
                    <i class="material-icons" data-toggle="tooltip" title="Sửa">&#xE254;</i>
                </a>
                <a href="javascript:void(0)" class="save" style="display: none;" onclick="saveEdit(this, '${cls.code}')">
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

async function enableEdit(el) {
    const row = el.closest("tr");
    const editableIndexes = [2, 3, 4, 5, 6, 7, 8, 9]; // Các cột có thể chỉnh sửa
    // Get subjects list from backend
    const subjectsRes = await fetch("http://localhost:8000/subjects/names");
    const subjectsResult = await subjectsRes.json();
    const subjectsName = subjectsResult.subject_names;
    row.querySelectorAll("td").forEach((td, index) => {
        if (index === 4) {
            console.log("subjectsName: ", subjectsName);
            const currentValue = td.textContent.trim();
            const selectedSubject = currentValue
                .split(",")
                .map(name => name.trim());
            // Tạo HTML cho select box
            let selectHTML = `<select id="list_subject" class="form-control form-control-sm" multiple>`;
            subjectsName.forEach(name => {
                const selected = currentValue === name ? "selected" : "";
                selectHTML += `<option value="${name}" ${selected}>${name}</option>`;
            });
            selectHTML += `</select>`;
            // Gán vào ô td
            td.innerHTML = selectHTML;
            const selectEl = td.querySelector('#list_subject');
            for (const option of selectEl.options) {
                if (selectedSubject.includes(option.value)) {
                    option.selected = true; // hoặc option.setAttribute("selected", "selected");
                }
            }
            // Khởi tạo plugin multiSelect
            $(function () {
                $('#list_subject').multiSelect();
            });
        } 
        else if (index === 6 || index === 7) {
            // Chỉ cho phép chỉnh sửa các cột có thể chọn Có/Không
            const currentValue = td.textContent.trim();
            td.innerHTML = `<select class="form-control form-control-sm">
                <option value="true" ${currentValue === "Có" ? "selected" : ""}>Có</option>
                <option value="false" ${currentValue === "Không" ? "selected" : ""}>Không</option>
            </select>`;
        } else if (index === 8) {
            // Chỉ cho phép chỉnh sửa ngày không dạy được
            const currentValue = td.textContent.trim();
            const selectedDay = currentValue
                .split(",")
                .map(name => name.trim());
            console.log("selectedDay:", selectedDay);

            // Tạo một select với nhiều lựa chọn
            td.innerHTML = `
                <select id="unavailable_day" name="people" multiple>
                    <option value="Thứ 2">Thứ 2</option>
                    <option value="Thứ 3">Thứ 3</option>
                    <option value="Thứ 4">Thứ 4</option>
                    <option value="Thứ 5">Thứ 5</option>
                    <option value="Thứ 6">Thứ 6</option>
                    <option value="Thứ 7">Thứ 7</option>
                </select>`;
            // Gán selected cho từng option trước khi khởi tạo plugin
            const selectEl = td.querySelector('#unavailable_day');
            for (const option of selectEl.options) {
                if (selectedDay.includes(option.value)) {
                    option.selected = true; // hoặc option.setAttribute("selected", "selected");
                }
            }
            // Khởi tạo plugin multiSelect
            $(function () {
                $('#unavailable_day').multiSelect();
            });

        } else if (index === 9) {
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

async function saveEdit(el, teacherCode) {
    const row = el.closest("tr");
    const inputs = row.querySelectorAll("td input");
    const selects = row.querySelectorAll("td select");
    const new_code = inputs[1].value; // Mã giáo viên
    const name = inputs[2].value;
    const subjects = Array.from(selects[0].selectedOptions)
        .map(option => option.value);
    const maxWeeklyLessons = inputs[3].value;
    const availableMorning = selects[1].value === "true" ? true : false; // Chuyển đổi từ "Có" hoặc "Không" thành boolean
    const availableAfternoon = selects[2].value === "true" ? true : false; // Chuyển đổi từ "Có" hoặc "Không" thành boolean
    const unavailableDays = Array.from(selects[3].selectedOptions)
        .map(option => option.value);
    const status = selects[4].value;
    const updatedValues = {
        code: new_code, // Mã giáo viên
        name: name,
        subjects: subjects,
        status: status,
        max_weekly_lessons: parseInt(maxWeeklyLessons) || 18, // Mặc định là 18 nếu không nhập
        available_morning: availableMorning, // Chuyển đổi từ "Có" hoặc "Không" thành boolean
        available_afternoon: availableAfternoon, // Chuyển đổi từ "Có" hoặc "Không" thành boolean
        unavailable_slots: unavailableDays   // Mảng ngày không dạy được
    };
    console.log("Updated values:", updatedValues);
    if (!validateTeacherData(new_code, name, subjects)) return;

    const res = await fetch(`http://localhost:8000/teachers/${teacherCode}`, {
        method: "PUT",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedValues)
    });
    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Lỗi khi cập nhật thông tin giáo viên.");
    }
    const result = await res.json();
    showToast(result.message || "Đã cập nhật thông tin giáo viên");

    // Set lại từng cell bằng đúng giá trị bạn vừa dùng
    // Quay lại hiển thị bình thường
    row.querySelectorAll("td:not(:first-child):not(:last-child)").forEach((td, idx) => {
        let baseIdx = 1
        if (idx === baseIdx) td.innerHTML = updatedValues.code;
        if (idx === baseIdx + 1) td.innerHTML = updatedValues.name;
        if (idx === baseIdx + 2) td.innerHTML = updatedValues.subjects.join(", ");
        if (idx === baseIdx + 3) td.innerHTML = updatedValues.max_weekly_lessons;
        if (idx === baseIdx + 4) td.innerHTML = updatedValues.available_morning == "true" ? "Có" : "Không";
        if (idx === baseIdx + 5) td.innerHTML = updatedValues.available_afternoon == "true" ? "Có" : "Không";
        if (idx === baseIdx + 6) td.innerHTML = updatedValues.unavailable_slots.join(", "); // Hiển thị mảng ngày không dạy được
        if (idx === baseIdx + 7) td.innerHTML = updatedValues.status === "active" ? "Đang dạy" : "Tạm dừng";
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
    const teacherCode = document.getElementById("teacherCode").value.trim();
    const name = document.getElementById("teacherName").value.trim();
    const subjects = Array.from(document.getElementById("teacherSubject").selectedOptions)
        .map(option => option.value);
    const phone = document.getElementById("teacherPhone").value.trim();
    const email = document.getElementById("teacherEmail").value.trim();
    const dob = document.getElementById("teacherDoB").value.trim();
    // Chuyển đổi định dạng ngày sinh từ "dd/mm/yyyy" sang "yyyy-mm-dd"
    const [y, m, d] = dob.split('-');
    dob_formatted = `${m}/${d}/${y}`; // → "23/04/2000"
    const address = document.getElementById("teacherAddress").value.trim();
    const maxWeeklyLessons = document.getElementById("teacherMaxLesson").value.trim();
    const availableMorning = document.getElementById("teacherAvailableMorning").value.trim() === "true" ? true : false; // Chuyển đổi từ "Có" hoặc "Không" thành boolean
    const availableAfternoon = document.getElementById("teacherAvailableAfternoon").value.trim() === "true" ? true : false; // Chuyển đổi từ "Có" hoặc "Không" thành boolean
    const unavailableDays = Array.from(document.getElementById("teacherUnavailabeDay").selectedOptions)
        .map(option => option.value);
    const status = document.getElementById("teacherStatus").value.trim();

    const addValues = {
        code: teacherCode, // Mã giáo viên
        name: name,
        subject: subjects,
        phone: phone,
        email: email,
        dob: dob_formatted,
        address: address,
        status: status,
        max_weekly_lessons: parseInt(maxWeeklyLessons) || 18, // Mặc định là 18 nếu không nhập
        available_morning: availableMorning, // Chuyển đổi từ "Có" hoặc "Không" thành boolean
        available_afternoon: availableAfternoon, // Chuyển đổi từ "Có" hoặc "Không" thành boolean
        unavailable_slots: unavailableDays   // Mảng ngày không dạy được
    };

    // const addValues = {
    //     "code": "abcd1234",
    //     "name": "Nguyễn Việt Dũng",
    //     "subject": [
    //         "Toán 11"
    //     ],
    //     "phone": "1234567890",
    //     "email": "tiensunguyen2103@gmail.com",
    //     "dob": "07/03/2025",
    //     "address": "Hà Nội",
    //     "status": "active",
    //     "max_weekly_lessons": 12,
    //     "available_morning": true,
    //     "available_afternoon": true,
    //     "unavailable_slots": [
    //         "Thứ 2",
    //         "Thứ 3"
    //     ]
    // };
    console.log('addTeacher: ', addValues);
    if (!validateTeacherData(teacherCode, name, subjects, phone, email, dob, address)) return;

    try {
        const response = await fetch("http://localhost:8000/teachers", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(addValues)
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

function validateTeacherData(code, name, subjects) {
    const errors = [];

    // 1. Mã giáo viên (code): không rỗng, không chứa ký tự đặc biệt, độ dài 3–10 ký tự
    if (!code || typeof code !== 'string' || !/^[A-Za-z0-9]{3,10}$/.test(code)) {
        errors.push("Mã giáo viên không hợp lệ (chỉ gồm chữ/số, 3–10 ký tự).");
    }

    // 2. Tên: không rỗng, là chuỗi
    if (!name || typeof name !== 'string' || name.trim().length < 2) {
        errors.push("Tên giáo viên không hợp lệ (tối thiểu 2 ký tự).");
    }

    // 3. Môn dạy (subjects): phải là mảng, có ít nhất 1 môn
    if (!Array.isArray(subjects) || subjects.length === 0) {
        errors.push("Giáo viên phải dạy ít nhất một môn.");
    }

    return {
        valid: errors.length === 0,
        errors
    };
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
    }, type === "danger" || "warning" ? 10000 : 3000); // Thông báo lỗi hiển thị lâu hơn
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

// Tải danh sách môn học khi trang được tải để hiển thị trong select box
$(document).ready(function () {
    fetch("http://localhost:8000/subjects/names")
        .then(response => response.json())
        .then(data => {
            const subjectNames = data.subject_names; // backend trả về: { subject_names: [...] }
            console.log("Danh sách môn học:", subjectNames);
            const selectElement = document.getElementById("teacherSubject");

            // Xóa các option cũ (nếu cần), nhưng giữ lại option mặc định
            // selectElement.innerHTML = `<option disabled selected>-- Chọn môn học --</option>`;

            subjectNames.forEach(name => {
                const option = document.createElement("option");
                option.value = name;
                option.textContent = name;
                selectElement.appendChild(option);
            });
            // Khởi tạo plugin multiSelect
            $(function () {
                $('#teacherSubject').multiSelect();
            });
        })
        .catch(error => {
            console.error("Lỗi khi tải danh sách môn học:", error);
        });
});

$(document).ready(function () {
    // Khởi tạo plugin multiSelect cho select box môn học
    $(function () {
        $('#teacherUnavailabeDay').multiSelect();
    });
});

$(document).ready(fetchTeachers(1)); // Load trang đầu tiên khi DOM sẵn sàng

// Logout functionality
$(document).ready(function () {
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
