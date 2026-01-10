import requests

ACCESS_TOKEN = 'EAAPedvkO7m4BQF0hLQZAZBH4OX1LKhtSRLDJv2aXyrOnqsBZC0doGkrZAN4ZCiQ9TE3BeW1cP33lgf4Hbvw6bZCmUuWLUgh0nikz2EoatIEcKETPGr0pQIQLo5RxSOkjvBNGGI80Mb4v2wggzr39qqmRUsO0c9NZCxWi2AuSJpX0Af5foAcxjLad7YsY2lk'
API_VERSION = 'v24.0'

def get_page_ids():
    url = f"https://graph.facebook.com/{API_VERSION}/me/accounts"
    params = {'access_token': ACCESS_TOKEN}
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'data' in data:
            print("✅ 접근 가능한 페이지 목록:")
            for page in data['data']:
                print(f"- 페이지 이름: {page['name']} | ID: {page['id']}")
        else:
            print("❌ 페이지를 찾을 수 없습니다. 권한(pages_show_list 등)을 확인하세요.")
    except Exception as e:
        print(f"❗ 오류 발생: {e}")

if __name__ == "__main__":
    get_page_ids()