# **Đặc tả dự án DS-Reading-Platform**

## **1. Mô tả chung**

**DS-Reading-Platform** là một nền tảng web giúp người dùng đăng bài, chia sẻ bài viết với nội dung phong phú từ nhiều nguồn. Người dùng có thể:

* Đính kèm **link bài viết** hoặc **nội dung text** vào khung bên trái.
* Soạn bài post của riêng mình ở khung bên phải, có thể viết nhận xét, phân tích hoặc chia sẻ quan điểm.
* Chia sẻ bài đăng của họ với cộng đồng.

Hệ thống có cơ chế **quản trị viên (admin)** để giám sát nội dung và quản lý người dùng.

## **2. Công nghệ sử dụng**

* **Backend** : Flask
* **Frontend** : Flask, Tailwindcss và React.js cho giao diện
* **Cơ sở dữ liệu** : SQLite
* **Môi trường ảo hóa** : Máy ảo (VM) để đảm bảo tính độc lập và hiệu suất cao (python -m venv venv)

---

## **3. Chức năng chính**

### **3.1. Chức năng dành cho user**

✅ **Đăng ký, đăng nhập, đăng xuất**

✅ **Đăng bài** :

* Nhập **link hoặc nội dung bài viết gốc** vào khung bên trái.
* Soạn bài viết của riêng mình ở khung bên phải.
* Có thể thêm tiêu đề, tag, định dạng markdown cơ bản.

✅ **Tương tác với bài viết** :

* Like, bình luận, lưu bài viết.
* Chia sẻ bài viết của người khác.

✅ **Quản lý bài viết cá nhân** :

* Xem danh sách bài đã đăng.
* Chỉnh sửa hoặc xóa bài viết của mình.

✅ **Tìm kiếm bài viết** :

* Lọc bài theo tag hoặc từ khóa.

---

### **3.2. Chức năng dành cho admin**

✅ **Quản lý user**

* Xem danh sách user.
* Chặn/tắt tài khoản vi phạm.

✅ **Duyệt bài viết**

* Kiểm duyệt nội dung bài viết nếu cần.
* Ẩn hoặc xóa bài nếu vi phạm.

✅ **Phân quyền admin**

* **Admin initial** :
  * Là admin đầu tiên được tạo khi khởi tạo database.
  * Không hiển thị trong danh sách user, không user nào có quyền thấy nó.
  * Có quyền quản lý user khác, đóng/ngắt hoạt động, vô hiệu hóa và kích hoạt user khác.
  * Ban đầu, chỉ có duy nhất admin initial, không có admin cấp dưới.

---

## **4. Cấu trúc database (SQLite)**

### **4.1. Bảng `users` (quản lý người dùng)**

| user_id  | username | email | password_hash | role              | created_at |
| -------- | -------- | ----- | ------------- | ----------------- | ---------- |
| INT (PK) | TEXT     | TEXT  | TEXT          | TEXT (user/admin) | TIMESTAMP  |

### **4.2. Bảng `posts` (quản lý bài viết)**

| post_id  | user_id (FK) | title | content | source_link | tags | created_at |
| -------- | ------------ | ----- | ------- | ----------- | ---- | ---------- |
| INT (PK) | INT          | TEXT  | TEXT    | TEXT        | TEXT | TIMESTAMP  |

### **4.3. Bảng `comments` (bình luận bài viết)**

| comment_id | post_id (FK) | user_id (FK) | content | created_at |
| ---------- | ------------ | ------------ | ------- | ---------- |
| INT (PK)   | INT          | INT          | TEXT    | TIMESTAMP  |

### **4.4. Bảng `likes` (lượt thích)**

| like_id  | post_id (FK) | user_id (FK) | created_at |
| -------- | ------------ | ------------ | ---------- |
| INT (PK) | INT          | INT          | TIMESTAMP  |

---

## **5. Quy trình hoạt động**

### **5.1. Khởi tạo hệ thống**

1️⃣ Tạo cơ sở dữ liệu SQLite.

2️⃣ Thêm **admin initial** vào database.

3️⃣ Admin initial có toàn quyền quản lý user và bài viết, không xuất hiện trong danh sách user thông thường.

### **5.2. Quy trình đăng bài**

1️⃣ User nhập link bài viết gốc hoặc nội dung gốc vào khung bên trái.

2️⃣ User viết bài post của mình bên phải.

3️⃣ User nhấn  **Đăng bài** , bài viết sẽ được lưu vào database.

### **5.3. Quy trình phân quyền admin**

* Ban đầu chỉ có admin initial.
* Admin initial có thể cấp quyền admin cho user khác nếu cần.
* Admin cấp dưới không thể xóa hoặc thay đổi admin initial.

---

## **6. Hạ tầng triển khai**

* **Máy ảo (VM)** : Tạo môi trường độc lập, tránh xung đột với hệ thống khác.

## **7. Cây thư mục:**

ds-reading-platform/
├── .env                    # Chứa biến môi trường
├── .gitignore             # Cấu hình git ignore
├── requirements.txt       # Danh sách package cần thiết
├── run.py                # File chạy ứng dụng
├── config.py             # Cấu hình ứng dụng
│
├── app/
│   ├── __init__.py       # Khởi tạo ứng dụng Flask
│   │
│   ├── models/           # Các model database
│   │   ├── __init__.py
│   │   ├── user.py      # Model User
│   │   ├── post.py      # Model Post
│   │   ├── comment.py   # Model Comment
│   │   └── like.py      # Model Like
│   │
│   ├── routes/          # Các route của ứng dụng
│   │   ├── __init__.py
│   │   ├── auth.py      # Route xác thực
│   │   ├── main.py      # Route chính
│   │   └── admin.py     # Route admin
│   │
│   ├── templates/       # Templates HTML
│   │   ├── base.html    # Template cơ sở
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   ├── main/
│   │   │   ├── index.html
│   │   │   ├── create_post.html
│   │   │   └── view_post.html
│   │   └── admin/
│   │       ├── dashboard.html
│   │       ├── users.html
│   │       └── posts.html
│   │
│   ├── static/         # File tĩnh
│   │   ├── css/
│   │   │   └── main.css
│   │   ├── js/
│   │   │   └── main.js
│   │   └── img/
│   │
│   └── utils/         # Các hàm tiện ích
│       ├── __init__.py
│       └── decorators.py
│
├── tests/            # Unit tests
│   ├── __init__.py
│   ├── test_auth.py
│   └── test_posts.py
│
└── venv/            # Môi trường ảo Python (sẽ được tạo sau)
