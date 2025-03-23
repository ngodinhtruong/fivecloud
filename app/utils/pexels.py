import requests
from flask import current_app
import random

def get_random_avatar():
    """Lấy một ảnh avatar ngẫu nhiên từ Pexels"""
    api_key = current_app.config['PEXELS_API_KEY']
    if not api_key:
        print("Missing Pexels API key")
        return get_default_avatar()

    headers = {
        'Authorization': api_key
    }

    try:
        # Danh sách từ khóa tìm kiếm đa dạng
        keywords = [
            'portrait face', 'profile avatar', 
            'anime portrait', 'cartoon avatar',
            'character portrait'
        ]
        
        # Chọn ngẫu nhiên một từ khóa
        keyword = random.choice(keywords)
        
        # Gọi Pexels API
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers,
            params={
                'query': keyword,
                'per_page': 80,
                'size': 'small',
                'orientation': 'square'
            },
            timeout=5  # Timeout sau 5 giây
        )

        # In ra response để debug
        print(f"Pexels API Response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('photos'):
                # Lấy ngẫu nhiên một ảnh từ kết quả
                photo = random.choice(data['photos'])
                # Sử dụng ảnh nhỏ để làm avatar
                return photo['src']['small']
            else:
                print("No photos found in Pexels response")
        else:
            print(f"Pexels API error: {response.text}")

    except Exception as e:
        print(f"Error fetching Pexels image: {str(e)}")

    return get_default_avatar()

def get_default_avatar():
    """Trả về URL avatar mặc định"""
    default_avatars = [
        "https://raw.githubusercontent.com/Ashwinvalento/cartoon-avatar/master/lib/images/male/45.png",
        "https://raw.githubusercontent.com/Ashwinvalento/cartoon-avatar/master/lib/images/female/45.png",
        "https://raw.githubusercontent.com/Ashwinvalento/cartoon-avatar/master/lib/images/male/85.png",
        "https://raw.githubusercontent.com/Ashwinvalento/cartoon-avatar/master/lib/images/female/85.png"
    ]
    return random.choice(default_avatars) 