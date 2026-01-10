import requests
import tkinter as tk
from tkinter import filedialog
import os

# 1. 설정 정보
ACCESS_TOKEN = 'EAAPedvkO7m4BQF0hLQZAZBH4OX1LKhtSRLDJv2aXyrOnqsBZC0doGkrZAN4ZCiQ9TE3BeW1cP33lgf4Hbvw6bZCmUuWLUgh0nikz2EoatIEcKETPGr0pQIQLo5RxSOkjvBNGGI80Mb4v2wggzr39qqmRUsO0c9NZCxWi2AuSJpX0Af5foAcxjLad7YsY2lk'
AD_ACCOUNT_ID = 'act_1289149138367044'
API_VERSION = 'v24.0'

def test_image_upload():
    # 윈도우 파일 선택창 띄우기
    root = tk.Tk()
    root.withdraw() # 메인 창은 숨김
    file_path = filedialog.askopenfilename(title="업로드할 광고 이미지를 선택하세요")
    
    if not file_path:
        print("❌ 파일이 선택되지 않았습니다.")
        return

    print(f"📂 선택된 파일: {file_path}")

    url = f"https://graph.facebook.com/{API_VERSION}/{AD_ACCOUNT_ID}/adimages"
    
    try:
        # 파일을 바이너리 모드로 읽기
        with open(file_path, 'rb') as f:
            files = {'file': f}
            params = {'access_token': ACCESS_TOKEN}
            response = requests.post(url, params=params, files=files)
            
        data = response.json()
        
        if 'images' in data:
            image_name = list(data['images'].keys())[0]
            img_hash = data['images'][image_name]['hash']
            print(f"✅ 이미지 업로드 성공!")
            print(f"🔹 획득한 Hash 값: {img_hash}")
            print("\n💡 이 Hash 값을 복사해서 메모장에 저장해두세요!")
        else:
            print("❌ 업로드 실패:", data)
            
    except Exception as e:
        print(f"❗ 오류 발생: {e}")

if __name__ == "__main__":
    test_image_upload()