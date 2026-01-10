import requests
import webbrowser
import os
import json

# ==========================================
# 1. 설정 정보 (v24.0 정책 고정)
# ==========================================
ACCESS_TOKEN = 'EAAPedvkO7m4BQF0hLQZAZBH4OX1LKhtSRLDJv2aXyrOnqsBZC0doGkrZAN4ZCiQ9TE3BeW1cP33lgf4Hbvw6bZCmUuWLUgh0nikz2EoatIEcKETPGr0pQIQLo5RxSOkjvBNGGI80Mb4v2wggzr39qqmRUsO0c9NZCxWi2AuSJpX0Af5foAcxjLad7YsY2lk'
AD_ACCOUNT_ID = 'act_1289149138367044' 
IMAGE_HASH = '9eaba2db9e82f2a8afb169407e793a61'
PAGE_ID = '100626312650716' 
API_VERSION = 'v24.0'

def test_generate_preview_v24_final():
    # v24.0 공식 엔드포인트 (언더바 없음)
    url = f"https://graph.facebook.com/{API_VERSION}/{AD_ACCOUNT_ID}/generatepreviews"
    
    # 크리에이티브 스펙
    creative_spec = {
        "object_story_spec": {
            "page_id": PAGE_ID,
            "link_data": {
                "image_hash": IMAGE_HASH,
                "link": "https://piscess.shop/",
                "message": "파이시스 리퍼브 상품 입고! ✨\n고퀄리티 제품을 합리적인 가격에 만나보세요.",
                "name": "파이시스 리퍼브 컬렉션",
                "call_to_action": {"type": "SHOP_NOW"}
            }
        }
    }

    # [수정 포인트] v24.0 허용 리스트에 있는 값인 'INSTAGRAM_STANDARD' 사용
    params = {
        'access_token': ACCESS_TOKEN,
        'creative': json.dumps(creative_spec),
        'ad_format': 'INSTAGRAM_STANDARD' 
    }
    
    try:
        print(f"--- [v24.0] 최종 규격 호출 중 ---")
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'data' in data and len(data['data']) > 0:
            preview_html = data['data'][0]['body']
            
            file_name = "v24_preview_final_fixed.html"
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(preview_html)
            
            print("✅ v24.0 실시간 미리보기 생성 성공!")
            full_path = os.path.abspath(file_name)
            webbrowser.open('file://' + full_path)
            
        else:
            print("❌ v24.0 미리보기 생성 실패 (응답 확인):")
            print(json.dumps(data, indent=4, ensure_ascii=False))
            
    except Exception as e:
        print(f"❗ 시스템 오류 발생: {e}")

if __name__ == "__main__":
    test_generate_preview_v24_final()