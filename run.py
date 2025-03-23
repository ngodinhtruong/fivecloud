from app import create_app
import os

# Đảm bảo thư mục instance tồn tại trước khi tạo app
os.makedirs('instance', exist_ok=True)

app = create_app()

if __name__ == '__main__':
    app.run(debug=True) 