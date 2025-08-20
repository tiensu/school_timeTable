# 🏫 School Timetable Management WebApp

Một ứng dụng web giúp Ban giám hiệu và nhà trường cấp 3 dễ dàng tạo, quản lý và tối ưu thời khóa biểu cho giáo viên, lớp học và môn học — với giao diện đơn giản, dễ sử dụng và có thể mở rộng bằng AI.

---

## 🧩 1. Tổng quan dự án

Ứng dụng hỗ trợ quản lý thời khóa biểu với các tính năng:
- CRUD dữ liệu lớp học, giáo viên, môn học, phòng học
- Gán môn học vào lớp – giáo viên – phòng theo từng tiết học
- Quản lý ràng buộc khi sinh thời khóa biểu (giáo viên bận, lớp chỉ học môn vào một số ngày...)
- Giao diện thân thiện, sử dụng Bootstrap
- Tích hợp chatbot hỗ trợ hỏi–đáp thông minh (sắp triển khai)
- Dễ dàng mở rộng: hỗ trợ AI để sinh thời khóa biểu tự động trong tương lai

---

## ✅ 2. Danh sách chức năng (tiếp tục cập nhật)

| Nhóm chức năng           | Mô tả ngắn                                                                 |
|--------------------------|---------------------------------------------------------------------------|
| 🎛 Dashboard              | Giao diện tổng hợp các liên kết quản lý                                   |
| 🏫 Quản lý lớp học         | Thêm / sửa / xóa lớp học, phân trang, tìm kiếm, chọn nhiều dòng để xóa   |
| 👩‍🏫 Quản lý giáo viên      | Thêm / sửa / xóa thông tin giáo viên                                     |
| 📚 Quản lý môn học         | Tên môn, khối lớp dạy, số tiết/tuần                                       |
| 🏠 Quản lý phòng học       | Phân loại phòng, sức chứa                                                 |
| 📅 Gán thời khóa biểu     | Gán môn – lớp – giáo viên – phòng theo từng tiết                         |
| ⚠️ Ràng buộc thời khóa biểu | Thiết lập hạn chế theo giáo viên, lớp, môn, thời gian                    |
| 💬 Chatbot (AI – sắp có)  | Hỏi đáp bằng ngôn ngữ tự nhiên về lịch học, phòng trống,...              |

---

## 🛠️ 3. Hướng dẫn build & chạy

### 🌐 Công nghệ sử dụng
- **Frontend**: HTML + JavaScript + Bootstrap 5
- **Backend**: Python + FastAPI
- **Database**: PostgreSQL
- **Docker**: dùng Docker Compose để build toàn bộ hệ thống

### 📦 Yêu cầu hệ thống
- Docker + Docker Compose cài sẵn

### ▶️ Cách chạy project:

```bash
# Clone repo
git https://github.com/tiensu/time_table.git
cd time_table

# Chạy project
docker-compose up --build
```

- Truy cập:
  - Frontend: http://localhost:3000
  - Backend API: http://localhost:8002/docs (Swagger UI)

---

## 📌 Ghi chú
- Source code được chia theo module: `frontend/`, `backend/app/`, `models/`, `schemas/`,...
- Toàn bộ dữ liệu mẫu sẽ được thêm sau bản MVP.
- Mọi đóng góp đều được hoan nghênh 🙌

---

## 📜 License

MIT License. Bạn có thể sử dụng, sửa đổi và phân phối lại dự án này với ghi chú bản quyền.
