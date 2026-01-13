import os
import requests
from google.cloud import bigquery

# ✅ 환경변수에서 장기 토큰 불러오기
META_ACCESS_TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")

def get_meta_ads_preview_list(account_id):
    """
    주어진 account_id에 대해 오늘 활성화된 '단일', '영상' 광고를 조회하고,
    광고 썸네일, 문구, 링크 정보를 반환합니다.
    """
    client = bigquery.Client()

    # ✅ 먼저 해당 account_id의 company_name이 demo인지 확인
    company_check_query = f"""
        SELECT company_name
        FROM `winged-precept-443218-v8.ngn_dataset.metaAds_acc`
        WHERE meta_acc_id = '{account_id}'
        LIMIT 1
    """
    company_result = client.query(company_check_query).result()
    company_name = next(iter(company_result), {}).get("company_name", None)

    # ✅ 데모 계정이면 고정 광고 8개 반환
    if company_name == "demo":
        ad_names = [f"[단일] NGN 인스타 광고 {chr(65+i)}" for i in range(8)]  # A ~ H
        image_urls = [f"/static/demo_ads/demo_{i+1}.jpg" for i in range(8)]
        message = "★인스타광고는 누구나컴퍼니★"
        link = "https://www.nugoona.co.kr/"

        dummy_ads = []
        for i in range(8):
            dummy_ads.append({
                "ad_id": f"demo_ad_{i+1}",
                "ad_name": ad_names[i],
                "instagram_acc_name": "NGN_COMPANY",
                "message": message,
                "link": link,
                "image_url": image_urls[i],
                "is_video": False
            })
        return dummy_ads

    # ✅ 일반 계정일 경우 실제 광고 가져오기
    query = f"""
        WITH today_ads AS (
          SELECT
            A.date,
            C.company_name,
            CI.instagram_acc_name,
            A.account_id,
            A.ad_name,
            A.ad_id,
            A.ad_status,
            A.spend
          FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_ad_level` A
          LEFT JOIN `winged-precept-443218-v8.ngn_dataset.metaAds_acc` C
            ON A.account_id = C.meta_acc_id
          LEFT JOIN `winged-precept-443218-v8.ngn_dataset.company_info` CI
            ON C.company_name = CI.company_name
          WHERE
            A.date = CURRENT_DATE('Asia/Seoul')
            AND A.ad_status = 'ACTIVE'
            AND A.spend > 0
            AND (LOWER(A.ad_name) LIKE '%단일%' OR LOWER(A.ad_name) LIKE '%영상%')
        )
        SELECT
          FORMAT_DATE('%Y-%m-%d', ANY_VALUE(date)) AS date,
          ANY_VALUE(company_name) AS company_name,
          ANY_VALUE(instagram_acc_name) AS instagram_acc_name,
          ANY_VALUE(account_id) AS account_id,
          ad_name,
          ANY_VALUE(ad_id) AS ad_id,
          ANY_VALUE(ad_status) AS ad_status,
          SUM(spend) AS total_spend
        FROM today_ads
        GROUP BY ad_name
        ORDER BY total_spend DESC
    """

    ads = client.query(query).result()
    ad_list = [dict(row) for row in ads if row.get("account_id") == account_id]

    if not ad_list:
        return []

    results = []
    for ad in ad_list:
        ad_id = ad["ad_id"]
        instagram_acc_name = ad.get("instagram_acc_name", "")

        try:
            # 1차 요청: 크리에이티브 ID
            creative_url = f"https://graph.facebook.com/v24.0/{ad_id}?fields=adcreatives&access_token={META_ACCESS_TOKEN}"
            creative_res = requests.get(creative_url)
            creative_data = creative_res.json()
            creative_id = creative_data.get("adcreatives", {}).get("data", [{}])[0].get("id")
            if not creative_id:
                continue

            # 2차 요청: 상세 정보
            detail_url = f"https://graph.facebook.com/v24.0/{creative_id}?fields=body,object_story_spec,image_url,video_id&access_token={META_ACCESS_TOKEN}"
            detail_res = requests.get(detail_url)
            detail_data = detail_res.json()

            message = detail_data.get("body") or \
                      detail_data.get("object_story_spec", {}).get("message") or \
                      detail_data.get("object_story_spec", {}).get("video_data", {}).get("message") or \
                      "(문구 없음)"

            link = detail_data.get("object_story_spec", {}).get("video_data", {}).get("call_to_action", {}).get("value", {}).get("link") or \
                   detail_data.get("object_story_spec", {}).get("link_data", {}).get("link") or \
                   "#"

            image_url = detail_data.get("object_story_spec", {}).get("video_data", {}).get("image_url") or \
                        detail_data.get("image_url") or \
                        detail_data.get("object_story_spec", {}).get("link_data", {}).get("picture") or ""

            if not image_url and detail_data.get("video_id"):
                thumb_url = f"https://graph.facebook.com/v24.0/{detail_data['video_id']}?fields=thumbnails&access_token={META_ACCESS_TOKEN}"
                thumb_res = requests.get(thumb_url)
                thumb_data = thumb_res.json()
                image_url = thumb_data.get("thumbnails", {}).get("data", [{}])[0].get("uri", "")

            # ✅ 이미지 URL이 유효하지 않으면 광고 제외
            if not image_url or image_url.strip() == "":
                print(f"[FILTERED] 이미지 URL이 없어서 광고 제외 (ad_id={ad_id}, ad_name={ad['ad_name']})")
                continue

            # ✅ 이미지 URL 유효성 검사 (선택적)
            try:
                img_check = requests.head(image_url, timeout=5)
                if img_check.status_code != 200:
                    print(f"[FILTERED] 이미지 URL 접근 불가로 광고 제외 (ad_id={ad_id}, status_code={img_check.status_code})")
                    continue
            except Exception as img_error:
                print(f"[FILTERED] 이미지 URL 검증 실패로 광고 제외 (ad_id={ad_id}, error={img_error})")
                continue

            results.append({
                "ad_id": ad_id,
                "ad_name": ad["ad_name"],
                "instagram_acc_name": instagram_acc_name,
                "message": message,
                "link": link,
                "image_url": image_url,
                "is_video": bool(detail_data.get("video_id"))
            })

        except Exception as e:
            print(f"[WARNING] 광고 미리보기 정보 가져오기 실패 (ad_id={ad_id}): {e}")
            continue

    return results
