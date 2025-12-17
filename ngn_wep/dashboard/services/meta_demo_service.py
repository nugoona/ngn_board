import os
import json
import requests

def load_access_token():
    # 환경변수에서 직접 토큰 가져오기 (Cloud Run 환경변수 사용)
    token = os.getenv("META_LONG_TOKEN")
    if token:
        return token
    # 로컬 개발용 fallback (선택사항)
    return None

def get_ad_accounts():
    token = load_access_token()
    if not token:
        return {"error": "Access token not found"}
    url = "https://graph.facebook.com/v24.0/me/adaccounts"
    params = {"access_token": token, "fields": "name,account_id"}
    return requests.get(url, params=params).json()

def get_businesses():
    token = load_access_token()
    if not token:
        return {"error": "Access token not found"}
    url = "https://graph.facebook.com/v24.0/me/businesses"
    params = {"access_token": token, "fields": "name,id"}
    return requests.get(url, params=params).json()

def get_pages():
    token = load_access_token()
    if not token:
        return {"error": "Access token not found"}
    url = "https://graph.facebook.com/v24.0/me/accounts"
    params = {"access_token": token, "fields": "name,id"}
    return requests.get(url, params=params).json()

def get_campaigns(ad_account_id):
    token = load_access_token()
    if not token:
        return {"error": "Access token not found"}
    url = f"https://graph.facebook.com/v24.0/act_{ad_account_id}/campaigns"
    params = {"access_token": token, "fields": "name,id"}
    return requests.get(url, params=params).json()

def get_posts(page_id):
    token = load_access_token()
    if not token:
        return {"error": "Access token not found"}
    url = f"https://graph.facebook.com/v24.0/{page_id}/posts"
    params = {"access_token": token, "fields": "message,created_time,id"}
    return requests.get(url, params=params).json()

def get_engagement(page_id):
    token = load_access_token()
    if not token:
        return {"error": "Access token not found"}
    url = f"https://graph.facebook.com/v24.0/{page_id}/insights/page_impressions,page_engaged_users"
    params = {"access_token": token}
    return requests.get(url, params=params).json()
