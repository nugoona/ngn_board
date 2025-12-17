import os
import logging
import requests
from google.cloud import bigquery
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from urllib.parse import quote

# ✅ 로깅 설정
logger = logging.getLogger(__name__)

# ✅ Cloud Run에서는 키 파일 대신 런타임 서비스계정(ADC)을 사용
# GOOGLE_APPLICATION_CREDENTIALS 환경변수가 설정되어 있으면 제거하여 ADC 사용
creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if creds_path and not os.path.exists(creds_path):
    os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

# ⚠️ 전역 캐싱 제거 - 호출 시점에 토큰을 읽도록 변경
# META_ACCESS_TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")  # DEPRECATED


def _get_meta_access_token():
    """
    Meta API 액세스 토큰을 환경변수에서 읽어 반환합니다.
    토큰이 없으면 RuntimeError를 발생시킵니다.
    """
    token = os.getenv("META_SYSTEM_USER_TOKEN")
    if not token:
        logger.error("[META_API] META_SYSTEM_USER_TOKEN 환경변수가 설정되지 않았습니다!")
        raise RuntimeError("META_SYSTEM_USER_TOKEN 환경변수가 설정되지 않았습니다. Cloud Run 환경변수를 확인하세요.")
    return token


def get_proxy_image_url(image_url):
    """
    이미지 URL을 프록시 URL로 변환합니다.
    배포 환경에서 CORS 및 Mixed Content 문제를 해결하기 위해 사용합니다.
    """
    if not image_url or image_url.strip() == "":
        return ""
    
    # 로컬 파일 경로인 경우 그대로 반환
    if image_url.startswith("/static/"):
        return image_url
    
    # 외부 URL인 경우 프록시 URL로 변환
    # URL 인코딩하여 프록시 엔드포인트에 전달
    encoded_url = quote(image_url, safe='')
    return f"/dashboard/proxy_image?url={encoded_url}"


def get_meta_ads_preview_list(account_id):
    """
    주어진 account_id에 대해 오늘 활성화된 '단일', '영상' 광고를 조회하고,
    광고 썸네일, 문구, 링크 정보를 반환합니다. (최적화된 버전)
    """
    start_time = time.time()
    logger.info(f"[OPTIMIZED] LIVE 광고 미리보기 요청 시작: account_id={account_id}")
    
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
        logger.error(f"[ERROR] 계정 매칭 실패: 요청된 account_id={account_id}, 검증된 account_id={verified_account_id}")
        return []
    
    logger.info(f"[VERIFIED] 계정 검증 완료: {account_id} -> {company_name}")

    # ✅ 데모 계정이면 고정 광고 8개 반환
    if company_name == "demo":
        logger.info("[DEMO] 데모 계정 - 고정 광고 반환")
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

    logger.info("[BIGQUERY] 광고 목록 조회 시작")
    query_start = time.time()
    ads = client.query(query).result()
    ad_list = [dict(row) for row in ads]
    query_time = time.time() - query_start
    logger.info(f"[BIGQUERY] 광고 목록 조회 완료: {len(ad_list)}개, {query_time:.2f}초")
    
    # 디버깅: 조회된 광고 목록 출력
    if ad_list:
        logger.debug(f"[BIGQUERY] 조회된 광고 목록 (최대 5개):")
        for idx, ad in enumerate(ad_list[:5], 1):
            logger.debug(f"  {idx}. ad_id={ad.get('ad_id')}, ad_name={ad.get('ad_name', '')[:50]}")
    else:
        logger.warning(f"[BIGQUERY] ⚠️ 광고 목록이 비어있습니다. account_id={account_id}, 쿼리 조건 확인 필요")

    if not ad_list:
        logger.info("[RESULT] 활성 광고 없음")
        return []

    # ✅ 병렬 처리로 Meta API 호출 최적화
    logger.info("[META_API] 병렬 처리로 광고 상세 정보 수집 시작")
    api_start = time.time()
    results = get_ads_details_parallel(ad_list)
    api_time = time.time() - api_start
    logger.info(f"[META_API] 광고 상세 정보 수집 완료: {len(results)}개, {api_time:.2f}초")
    
    total_time = time.time() - start_time
    logger.info(f"[OPTIMIZED] 전체 처리 완료: {total_time:.2f}초 (이전 대비 {query_time + api_time:.2f}초)")
    
    return results


def get_ads_details_parallel(ad_list):
    """
    병렬 처리로 광고 상세 정보를 수집합니다.
    """
    total_count = len(ad_list)
    logger.info(f"[META_API] get_ads_details_parallel 시작: {total_count}개 광고 처리")
    
    if not ad_list:
        logger.warning("[META_API] ⚠️ ad_list가 비어있습니다!")
        return []
    
    results = []
    success_count = 0
    fail_count = 0
    
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
                    success_count += 1
                else:
                    fail_count += 1
                    logger.warning(f"[META_API] 광고 상세 정보 수집 결과 없음 (ad_id={ad.get('ad_id', 'unknown')}, ad_name={ad.get('ad_name', 'unknown')})")
            except RuntimeError as e:
                # 토큰 누락 시 즉시 에러 전파 (조용히 0개 반환 금지)
                logger.error(f"[META_API] 토큰 에러로 처리 중단: {e}")
                raise
            except Exception as e:
                fail_count += 1
                logger.error(f"[META_API] 광고 상세 정보 수집 실패 (ad_id={ad.get('ad_id', 'unknown')}, ad_name={ad.get('ad_name', 'unknown')}): {type(e).__name__}: {e}")
                continue
    
    # ✅ 최종 수집 결과 요약 로그 (1회)
    logger.info(f"[META_API] 📊 수집 결과 요약: 요청={total_count}개, 성공={success_count}개, 실패={fail_count}개")
    
    return results


def get_single_ad_details(ad):
    """
    단일 광고의 상세 정보를 수집합니다.
    """
    ad_id = ad.get("ad_id", "UNKNOWN")
    ad_name = ad.get("ad_name", "UNKNOWN")
    instagram_acc_name = ad.get("instagram_acc_name", "")
    
    logger.debug(f"[META_API] get_single_ad_details 시작: ad_id={ad_id}, ad_name={ad_name[:50]}")
    
    # ✅ 호출 시점에 토큰 읽기 (토큰 없으면 RuntimeError 발생)
    access_token = _get_meta_access_token()
    
    try:
        # 1차 요청: 크리에이티브 ID (타임아웃 단축)
        creative_url = f"https://graph.facebook.com/v24.0/{ad_id}?fields=adcreatives&access_token={access_token}"
        logger.debug(f"[META_API] Meta API 요청 시작: ad_id={ad_id}")
        creative_res = requests.get(creative_url, timeout=3)
        
        # ✅ HTTP 상태 코드 체크
        if creative_res.status_code != 200:
            logger.error(f"[META_API] HTTP 에러 (ad_id={ad_id}): status_code={creative_res.status_code}, body={creative_res.text[:200]}")
            return None
        
        creative_data = creative_res.json()
        
        # API 에러 확인
        if "error" in creative_data:
            error_info = creative_data.get("error", {})
            logger.error(f"[META_API] API 에러 (ad_id={ad_id}): code={error_info.get('code')}, type={error_info.get('type')}, message={error_info.get('message')}")
            return None
        
        creative_id = creative_data.get("adcreatives", {}).get("data", [{}])[0].get("id")
        if not creative_id:
            logger.warning(f"[META_API] creative_id 없음 (ad_id={ad_id}): adcreatives.data={creative_data.get('adcreatives', {}).get('data', [])}")
            return None
        
        logger.debug(f"[META_API] creative_id 조회 성공: ad_id={ad_id}, creative_id={creative_id}")

        # 2차 요청: 상세 정보 (타임아웃 단축) - asset_feed_spec 포함하여 자동 형식 광고 지원
        detail_url = (
            f"https://graph.facebook.com/v24.0/{creative_id}"
            f"?fields=body,object_story_spec,image_url,video_id,asset_feed_spec"
            f"&access_token={access_token}"
        )
        detail_res = requests.get(detail_url, timeout=3)
        
        # ✅ HTTP 상태 코드 체크
        if detail_res.status_code != 200:
            logger.error(f"[META_API] HTTP 에러 (creative_id={creative_id}): status_code={detail_res.status_code}, body={detail_res.text[:200]}")
            return None
        
        detail_data = detail_res.json()

        # API 에러 확인
        if "error" in detail_data:
            error_info = detail_data.get("error", {})
            logger.error(f"[META_API] API 에러 (creative_id={creative_id}): code={error_info.get('code')}, type={error_info.get('type')}, message={error_info.get('message')}")
            return None

        # asset_feed_spec 추출 (NGN 자동 형식 광고용)
        asset_feed = detail_data.get("asset_feed_spec", {})
        
        # message 추출 (여러 경로 지원)
        message = (
            detail_data.get("body") or  # 직접 body
            detail_data.get("object_story_spec", {}).get("message") or  # object_story_spec.message
            detail_data.get("object_story_spec", {}).get("video_data", {}).get("message") or  # object_story_spec.video_data.message
            (asset_feed.get("bodies", [{}])[0].get("text") if asset_feed.get("bodies") and len(asset_feed.get("bodies", [])) > 0 else None) or  # asset_feed_spec.bodies[0].text
            (asset_feed.get("descriptions", [{}])[0].get("text") if asset_feed.get("descriptions") and len(asset_feed.get("descriptions", [])) > 0 else None) or  # asset_feed_spec.descriptions[0].text
            "(문구 없음)"
        )

        # link 추출 (여러 경로 지원)
        # asset_feed_spec.link_urls[0].website_url (NGN 계정 실제 구조)
        asset_link_urls = asset_feed.get("link_urls", [])
        asset_link_value = None
        if asset_link_urls and len(asset_link_urls) > 0:
            asset_link_value = asset_link_urls[0].get("website_url")  # asset_feed_spec.link_urls[0].website_url
        
        # asset_feed_spec.links는 문자열 배열일 수도 있고 객체 배열일 수도 있음 (다른 구조 대비)
        asset_links = asset_feed.get("links", [])
        if not asset_link_value and asset_links and len(asset_links) > 0:
            if isinstance(asset_links[0], str):
                asset_link_value = asset_links[0]  # 문자열인 경우
            elif isinstance(asset_links[0], dict):
                asset_link_value = asset_links[0].get("link")  # 객체인 경우
        
        link = (
            detail_data.get("object_story_spec", {}).get("video_data", {}).get("call_to_action", {}).get("value", {}).get("link") or  # object_story_spec.video_data.call_to_action.value.link
            detail_data.get("object_story_spec", {}).get("link_data", {}).get("link") or  # object_story_spec.link_data.link
            asset_link_value or  # asset_feed_spec.link_urls[0].website_url (최우선)
            (asset_feed.get("call_to_action_links", [{}])[0].get("link") if asset_feed.get("call_to_action_links") and len(asset_feed.get("call_to_action_links", [])) > 0 else None) or  # asset_feed_spec.call_to_action_links[0].link
            "#"
        )
        
        # 디버깅: asset_feed_spec이 있는 경우 로그 출력
        if asset_feed:
            logger.debug(f"[META_API] asset_feed_spec 발견 (ad_id={ad_id}): message={message[:50] if message else 'None'}..., link={link[:50] if link and link != '#' else 'None'}...")

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
                    f"?fields=source&access_token={access_token}"
                )
                video_res = requests.get(video_api, timeout=3)
                
                if video_res.status_code == 200:
                    video_data = video_res.json()
                    if "error" not in video_data:
                        video_url = video_data.get("source")
                    else:
                        error_code = video_data.get("error", {}).get("code", 0)
                        logger.warning(f"[META_API] 비디오 source API 에러 (ad_id={ad_id}, error_code={error_code}), 썸네일로 폴백")
                else:
                    logger.warning(f"[META_API] 비디오 source HTTP 에러 (ad_id={ad_id}, status={video_res.status_code}), 썸네일로 폴백")
            except Exception as video_error:
                logger.warning(f"[META_API] 비디오 URL 가져오기 실패 (ad_id={ad_id}): {video_error}, 썸네일로 폴백")
            
            # 2단계: 비디오 source가 없거나 실패한 경우, 고화질 썸네일 조회
            if not video_url:
                try:
                    thumb_url = f"https://graph.facebook.com/v24.0/{extracted_video_id}?fields=thumbnails&access_token={access_token}"
                    thumb_res = requests.get(thumb_url, timeout=2)
                    
                    if thumb_res.status_code == 200:
                        thumb_data = thumb_res.json()
                        if "error" not in thumb_data:
                            thumbnails = thumb_data.get("thumbnails", {}).get("data", [])
                            if thumbnails:
                                # 해상도(width * height)가 가장 높은 썸네일 선택 (고화질)
                                high_quality_thumbnail = max(
                                    thumbnails, 
                                    key=lambda x: x.get("width", 0) * x.get("height", 0)
                                ).get("uri", "")
                                logger.debug(f"[META_API] 고화질 썸네일 추출 성공 (ad_id={ad_id})")
                        else:
                            logger.warning(f"[META_API] 비디오 썸네일 API 에러 (ad_id={ad_id}): {thumb_data.get('error', {})}")
                    else:
                        logger.warning(f"[META_API] 비디오 썸네일 HTTP 에러 (ad_id={ad_id}, status={thumb_res.status_code})")
                except Exception as thumb_error:
                    logger.warning(f"[META_API] 비디오 썸네일 가져오기 실패 (ad_id={ad_id}): {thumb_error}")
        
        # 이미지 URL 추출 (썸네일용 또는 이미지 광고용)
        # asset_feed_spec.videos[0].thumbnail_url 추출 (NGN 자동 형식 광고용)
        asset_video_thumbnail = None
        if asset_feed and asset_feed.get("videos") and len(asset_feed.get("videos", [])) > 0:
            asset_video_thumbnail = asset_feed.get("videos", [])[0].get("thumbnail_url")
        
        # 고화질 썸네일이 있으면 최우선으로 사용, 없으면 기존 로직 사용
        image_url = (
            high_quality_thumbnail or  # 고화질 썸네일 (최우선)
            asset_video_thumbnail or  # asset_feed_spec.videos[0].thumbnail_url
            detail_data.get("thumbnail_url") or  # 루트 thumbnail_url (NGN 계정)
            detail_data.get("image_url") or  # 직접 이미지 URL
            detail_data.get("object_story_spec", {}).get("link_data", {}).get("picture") or  # 링크 광고 이미지
            detail_data.get("object_story_spec", {}).get("link_data", {}).get("image_url") or
            detail_data.get("object_story_spec", {}).get("video_data", {}).get("image_url") or  # 비디오 광고 이미지
            detail_data.get("object_story_spec", {}).get("video_data", {}).get("picture") or
            ""
        )

        # ✅ 이미지 URL 또는 비디오 URL 중 하나는 있어야 함
        if (not image_url or image_url.strip() == "") and (not video_url or video_url.strip() == ""):
            logger.warning(f"[META_API] 이미지/비디오 URL이 없어서 광고 제외 (ad_id={ad_id}, ad_name={ad['ad_name']})")
            return None
        
        # ✅ 이미지 URL을 프록시 URL로 변환 (배포 환경 대응)
        proxy_image_url = get_proxy_image_url(image_url) if image_url else ""
        
        return {
            "ad_id": ad_id,
            "ad_name": ad["ad_name"],
            "instagram_acc_name": instagram_acc_name,
            "message": message,
            "link": link,
            "image_url": proxy_image_url,  # 프록시 URL로 변환된 썸네일 또는 이미지 광고용
            "video_url": video_url,  # 비디오 광고 원본 URL (있을 경우)
            "is_video": bool(extracted_video_id)
        }

    except Exception as e:
        logger.error(f"[META_API] 광고 미리보기 정보 가져오기 실패 (ad_id={ad_id}): {type(e).__name__}: {e}")
        return None
