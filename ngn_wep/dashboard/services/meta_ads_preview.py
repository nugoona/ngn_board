import os
import requests
from google.cloud import bigquery
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# ✅ 환경변수에서 장기 토큰 불러오기
META_ACCESS_TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")

def get_meta_ads_preview_list(account_id):
    """
    주어진 account_id에 대해 오늘 활성화된 '단일', '영상' 광고를 조회하고,
    광고 썸네일, 문구, 링크 정보를 반환합니다. (최적화된 버전)
    """
    start_time = time.time()
    print(f"[OPTIMIZED] LIVE 광고 미리보기 요청 시작: account_id={account_id}")
    
    client = bigquery.Client()

    # ✅ 먼저 해당 account_id의 company_name이 demo인지 확인 (계정 매칭 검증 강화)
    company_check_query = f"""
        SELECT company_name, meta_acc_id
        FROM `winged-precept-443218-v8.ngn_dataset.metaAds_acc`
        WHERE meta_acc_id = '{account_id}'
        LIMIT 1
    """
    company_result = client.query(company_check_query).result()
    company_data = next(iter(company_result), {})
    company_name = company_data.get("company_name", None)
    verified_account_id = company_data.get("meta_acc_id", None)
    
    # ✅ 계정 매칭 검증
    if not verified_account_id or verified_account_id != account_id:
        print(f"[ERROR] 계정 매칭 실패: 요청된 account_id={account_id}, 검증된 account_id={verified_account_id}")
        return []
    
    print(f"[VERIFIED] 계정 검증 완료: {account_id} -> {company_name}")

    # ✅ 데모 계정이면 고정 광고 8개 반환
    if company_name == "demo":
        print("[DEMO] 데모 계정 - 고정 광고 반환")
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

    # ✅ 일반 계정일 경우 실제 광고 가져오기 (최적화된 쿼리)
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
            AND A.account_id = '{account_id}'
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
        LIMIT 10
    """

    print("[BIGQUERY] 광고 목록 조회 시작")
    query_start = time.time()
    ads = client.query(query).result()
    ad_list = [dict(row) for row in ads]
    query_time = time.time() - query_start
    print(f"[BIGQUERY] 광고 목록 조회 완료: {len(ad_list)}개, {query_time:.2f}초")

    if not ad_list:
        print("[RESULT] 활성 광고 없음")
        return []

    # ✅ 병렬 처리로 Meta API 호출 최적화
    print("[META_API] 병렬 처리로 광고 상세 정보 수집 시작")
    api_start = time.time()
    results = get_ads_details_parallel(ad_list)
    api_time = time.time() - api_start
    print(f"[META_API] 광고 상세 정보 수집 완료: {len(results)}개, {api_time:.2f}초")
    
    total_time = time.time() - start_time
    print(f"[OPTIMIZED] 전체 처리 완료: {total_time:.2f}초 (이전 대비 {query_time + api_time:.2f}초)")
    
    return results


def get_ads_details_parallel(ad_list):
    """
    병렬 처리로 광고 상세 정보를 수집합니다.
    """
    results = []
    
    # ThreadPoolExecutor를 사용한 병렬 처리
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 각 광고에 대해 병렬로 상세 정보 수집
        future_to_ad = {
            executor.submit(get_single_ad_details, ad): ad 
            for ad in ad_list
        }
        
        # 완료된 작업들을 순서대로 처리
        for future in as_completed(future_to_ad):
            ad = future_to_ad[future]
            try:
                result = future.result()
                if result:  # 유효한 결과만 추가
                    results.append(result)
            except Exception as e:
                print(f"[WARNING] 광고 상세 정보 수집 실패 (ad_id={ad.get('ad_id', 'unknown')}): {e}")
                continue
    
    return results


def get_single_ad_details(ad):
    """
    단일 광고의 상세 정보를 수집합니다.
    """
    ad_id = ad["ad_id"]
    instagram_acc_name = ad.get("instagram_acc_name", "")
    
    try:
        # 1차 요청: 크리에이티브 ID (타임아웃 단축)
        creative_url = f"https://graph.facebook.com/v24.0/{ad_id}?fields=adcreatives&access_token={META_ACCESS_TOKEN}"
        creative_res = requests.get(creative_url, timeout=3)
        creative_data = creative_res.json()
        creative_id = creative_data.get("adcreatives", {}).get("data", [{}])[0].get("id")
        if not creative_id:
            return None

        # 2차 요청: 상세 정보 (타임아웃 단축) - asset_feed_spec 포함하여 자동 형식 광고 지원
        detail_url = (
            f"https://graph.facebook.com/v24.0/{creative_id}"
            f"?fields=body,object_story_spec,image_url,video_id,asset_feed_spec"
            f"&access_token={META_ACCESS_TOKEN}"
        )
        detail_res = requests.get(detail_url, timeout=3)
        detail_data = detail_res.json()

        # API 에러 확인
        if "error" in detail_data:
            print(f"[ERROR] Meta API 에러 (ad_id={ad_id}): {detail_data.get('error', {})}")
            return None

        message = detail_data.get("body") or \
                  detail_data.get("object_story_spec", {}).get("message") or \
                  detail_data.get("object_story_spec", {}).get("video_data", {}).get("message") or \
                  "(문구 없음)"

        link = detail_data.get("object_story_spec", {}).get("video_data", {}).get("call_to_action", {}).get("value", {}).get("link") or \
               detail_data.get("object_story_spec", {}).get("link_data", {}).get("link") or \
               "#"

        # video_id 추출 (여러 경로 지원)
        extracted_video_id = None
        
        # 1) root video_id
        if detail_data.get("video_id"):
            extracted_video_id = detail_data["video_id"]
        
        # 2) asset_feed_spec 기반 (NGN 자동 형식 광고)
        asset_feed = detail_data.get("asset_feed_spec", {})
        videos = asset_feed.get("videos", [])
        if not extracted_video_id and isinstance(videos, list) and len(videos) > 0:
            extracted_video_id = videos[0].get("video_id")
        
        # 3) object_story_spec.video_data.video_id
        oss = detail_data.get("object_story_spec", {})
        if not extracted_video_id:
            extracted_video_id = oss.get("video_data", {}).get("video_id")
        
        # 비디오 URL 추출 및 고화질 썸네일 폴백 처리
        video_url = None
        high_quality_thumbnail = None  # 고화질 썸네일 (비디오 source 실패 시 사용)
        
        if extracted_video_id:
            # 1단계: 비디오 source URL 조회 시도
            try:
                video_api = (
                    f"https://graph.facebook.com/v24.0/{extracted_video_id}"
                    f"?fields=source&access_token={META_ACCESS_TOKEN}"
                )
                video_res = requests.get(video_api, timeout=3).json()
                
                if "error" not in video_res:
                    video_url = video_res.get("source")
                else:
                    # 권한 에러 또는 기타 에러 발생 시 썸네일로 폴백
                    error_code = video_res.get("error", {}).get("code", 0)
                    print(f"[WARNING] 비디오 source 조회 실패 (ad_id={ad_id}, error_code={error_code}), 썸네일로 폴백")
            except Exception as video_error:
                print(f"[WARNING] 비디오 URL 가져오기 실패 (ad_id={ad_id}): {video_error}, 썸네일로 폴백")
            
            # 2단계: 비디오 source가 없거나 실패한 경우, 고화질 썸네일 조회
            if not video_url:
                try:
                    thumb_url = f"https://graph.facebook.com/v24.0/{extracted_video_id}?fields=thumbnails&access_token={META_ACCESS_TOKEN}"
                    thumb_res = requests.get(thumb_url, timeout=2)
                    thumb_data = thumb_res.json()
                    
                    if "error" not in thumb_data:
                        thumbnails = thumb_data.get("thumbnails", {}).get("data", [])
                        if thumbnails:
                            # 해상도(width * height)가 가장 높은 썸네일 선택 (고화질)
                            high_quality_thumbnail = max(
                                thumbnails, 
                                key=lambda x: x.get("width", 0) * x.get("height", 0)
                            ).get("uri", "")
                            print(f"[INFO] 고화질 썸네일 추출 성공 (ad_id={ad_id})")
                    else:
                        print(f"[WARNING] 비디오 썸네일 API 에러 (ad_id={ad_id}): {thumb_data.get('error', {})}")
                except Exception as thumb_error:
                    print(f"[WARNING] 비디오 썸네일 가져오기 실패 (ad_id={ad_id}): {thumb_error}")
        
        # 이미지 URL 추출 (썸네일용 또는 이미지 광고용)
        # 고화질 썸네일이 있으면 최우선으로 사용, 없으면 기존 로직 사용
        image_url = (
            high_quality_thumbnail or  # 고화질 썸네일 (최우선)
            detail_data.get("image_url") or  # 직접 이미지 URL
            detail_data.get("object_story_spec", {}).get("link_data", {}).get("picture") or  # 링크 광고 이미지
            detail_data.get("object_story_spec", {}).get("link_data", {}).get("image_url") or
            detail_data.get("object_story_spec", {}).get("video_data", {}).get("image_url") or  # 비디오 광고 이미지
            detail_data.get("object_story_spec", {}).get("video_data", {}).get("picture") or
            ""
        )

        # ✅ 이미지 URL 또는 비디오 URL 중 하나는 있어야 함
        if (not image_url or image_url.strip() == "") and (not video_url or video_url.strip() == ""):
            print(f"[FILTERED] 이미지/비디오 URL이 없어서 광고 제외 (ad_id={ad_id}, ad_name={ad['ad_name']})")
            return None
        
        return {
            "ad_id": ad_id,
            "ad_name": ad["ad_name"],
            "instagram_acc_name": instagram_acc_name,
            "message": message,
            "link": link,
            "image_url": image_url,  # 썸네일 또는 이미지 광고용
            "video_url": video_url,  # 비디오 광고 원본 URL (있을 경우)
            "is_video": bool(extracted_video_id)
        }

    except Exception as e:
        print(f"[WARNING] 광고 미리보기 정보 가져오기 실패 (ad_id={ad_id}): {e}")
        return None
