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
