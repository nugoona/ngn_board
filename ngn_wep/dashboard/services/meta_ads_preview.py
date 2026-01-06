import os
import logging
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError as RequestsConnectionError
from google.cloud import bigquery
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from urllib.parse import quote
from collections import defaultdict
import threading

# ✅ 로깅 설정
logger = logging.getLogger(__name__)

# ✅ Cloud Run에서는 키 파일 대신 런타임 서비스계정(ADC)을 사용
# GOOGLE_APPLICATION_CREDENTIALS 환경변수가 설정되어 있으면 제거하여 ADC 사용
creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if creds_path and not os.path.exists(creds_path):
    os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

# ⚠️ 전역 캐싱 제거 - 호출 시점에 토큰을 읽도록 변경
# META_ACCESS_TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")  # DEPRECATED

# ✅ 토큰 로그 출력 여부 (1회만 출력)
_token_logged = False


def _get_meta_access_token():
    """
    Meta API 액세스 토큰을 환경변수에서 읽어 반환합니다.
    토큰이 없으면 RuntimeError를 발생시킵니다.
    """
    global _token_logged
    token = os.getenv("META_SYSTEM_USER_TOKEN")
    if not token:
        logger.error("[META_API] META_SYSTEM_USER_TOKEN 환경변수가 설정되지 않았습니다!")
        raise RuntimeError("META_SYSTEM_USER_TOKEN 환경변수가 설정되지 않았습니다. Cloud Run 환경변수를 확인하세요.")
    
    # ✅ 토큰 앞 8자만 1회 출력 (보안상 전체 출력 금지)
    if not _token_logged:
        token_head = token[:8] if len(token) >= 8 else token
        logger.warning(f"[META_API][TOKEN] 토큰 로드 완료: token_head={token_head}..., length={len(token)}")
        _token_logged = True
    
    return token


def _safe_meta_api_get(url, timeout=3, context=""):
    """
    Meta Graph API GET 요청을 수행하고, 에러 발생 시 상세 로그를 남깁니다.
    
    Returns:
        tuple: (data, error_reason) - 성공 시 (dict, None), 실패 시 (None, "reason_string")
    """
    try:
        resp = requests.get(url, timeout=timeout)
        
        # ✅ HTTP 상태 코드 체크
        if resp.status_code != 200:
            reason = f"http_{resp.status_code}"
            logger.error(
                f"[META_API][HTTP_ERROR] ({context}): "
                f"status_code={resp.status_code}, url={url[:100]}..., "
                f"body={resp.text[:500]}"
            )
            return None, reason
        
        data = resp.json()
        
        # ✅ API 에러 체크
        if "error" in data:
            error_info = data.get("error", {})
            reason = f"api_error_{error_info.get('code', 'unknown')}"
            logger.error(
                f"[META_API][API_ERROR] ({context}): "
                f"code={error_info.get('code')}, type={error_info.get('type')}, "
                f"message={error_info.get('message')}, "
                f"error_subcode={error_info.get('error_subcode')}"
            )
            return None, reason
        
        return data, None
    
    except Timeout as e:
        logger.exception(f"[META_API][TIMEOUT] ({context}): url={url[:100]}...")
        return None, "timeout"
    except RequestsConnectionError as e:
        logger.exception(f"[META_API][CONN_ERROR] ({context}): url={url[:100]}...")
        return None, "connection_error"
    except RequestException as e:
        logger.exception(f"[META_API][REQ_ERROR] ({context}): url={url[:100]}...")
        return None, "request_exception"
    except ValueError as e:
        # JSON 파싱 에러
        logger.exception(f"[META_API][JSON_ERROR] ({context}): url={url[:100]}...")
        return None, "json_parse_error"
    except Exception as e:
        logger.exception(f"[META_API][EXCEPTION] ({context}): {type(e).__name__}")
        return None, f"exception_{type(e).__name__}"


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
    logger.warning(f"[META_API][START] LIVE 광고 미리보기 요청 시작: account_id={account_id}")
    
    client = bigquery.Client()

    # ✅ 먼저 해당 account_id의 company_name이 demo인지 확인 (계정 매칭 검증 강화)
    company_check_query = """
        SELECT company_name, meta_acc_id
        FROM `winged-precept-443218-v8.ngn_dataset.metaAds_acc`
        WHERE meta_acc_id = @account_id
        LIMIT 1
    """
    company_check_params = [
        bigquery.ScalarQueryParameter("account_id", "STRING", account_id)
    ]
    company_result = client.query(
        company_check_query,
        job_config=bigquery.QueryJobConfig(query_parameters=company_check_params)
    ).result()
    company_data = next(iter(company_result), {})
    company_name = company_data.get("company_name", None)
    verified_account_id = company_data.get("meta_acc_id", None)
    
    # ✅ 계정 매칭 검증
    if not verified_account_id or verified_account_id != account_id:
        logger.error(f"[META_API][ERROR] 계정 매칭 실패: 요청된 account_id={account_id}, 검증된 account_id={verified_account_id}")
        return []
    
    logger.warning(f"[META_API][VERIFIED] 계정 검증 완료: {account_id} -> {company_name}")

    # ✅ 데모 계정이면 고정 광고 8개 반환
    if company_name == "demo":
        logger.warning("[META_API][DEMO] 데모 계정 - 고정 광고 반환")
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
    query = """
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
            AND A.account_id = @account_id
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
    ads_query_params = [
        bigquery.ScalarQueryParameter("account_id", "STRING", account_id)
    ]

    logger.warning("[META_API][BIGQUERY] 광고 목록 조회 시작")
    query_start = time.time()
    ads = client.query(
        query,
        job_config=bigquery.QueryJobConfig(query_parameters=ads_query_params)
    ).result()
    
    # ✅ BigQuery 결과를 ad_list로 변환하면서 상세 로깅
    ad_list = []
    raw_row_count = 0
    filtered_count = 0
    
    for row in ads:
        raw_row_count += 1
        try:
            ad_dict = dict(row)
            ad_id = ad_dict.get("ad_id")
            
            # ad_id가 없으면 필터링 로그
            if not ad_id:
                filtered_count += 1
                logger.warning(
                    f"[META_API][FILTERED_BEFORE_PARALLEL] "
                    f"idx={raw_row_count-1}, reason=missing_ad_id, "
                    f"keys={list(ad_dict.keys())}, "
                    f"ad_name={ad_dict.get('ad_name', 'N/A')[:40]}"
                )
                continue  # ad_id 없으면 스킵
            
            ad_list.append(ad_dict)
            
        except Exception as e:
            filtered_count += 1
            logger.warning(
                f"[META_API][FILTERED_BEFORE_PARALLEL] "
                f"idx={raw_row_count-1}, reason=dict_conversion_error, "
                f"error={type(e).__name__}: {e}"
            )
            continue
    
    query_time = time.time() - query_start
    logger.warning(
        f"[META_API][BIGQUERY] 광고 목록 조회 완료: "
        f"raw_rows={raw_row_count}, valid_ads={len(ad_list)}, filtered={filtered_count}, "
        f"query_time={query_time:.2f}초"
    )
    
    # 디버깅: 조회된 광고 목록 출력
    if ad_list:
        logger.warning(f"[META_API][BIGQUERY] 조회된 광고 목록 (최대 5개):")
        for idx, ad in enumerate(ad_list[:5], 1):
            logger.warning(
                f"[META_API][BIGQUERY]   {idx}. "
                f"ad_id={ad.get('ad_id')}, "
                f"ad_name={ad.get('ad_name', '')[:50]}, "
                f"account_id={ad.get('account_id')}"
            )
    else:
        logger.warning(f"[META_API][BIGQUERY] ⚠️ 광고 목록이 비어있습니다. account_id={account_id}, raw_rows={raw_row_count}, 쿼리 조건 확인 필요")

    if not ad_list:
        logger.warning("[META_API][RESULT] 활성 광고 없음")
        return []

    # ✅ [PRE_FILTER] 병렬 처리 직전 ad_list 상태 강제 로깅
    logger.warning(f"[META_API][PRE_FILTER] ========== 병렬 처리 직전 ad_list 검사 시작 ==========")
    logger.warning(f"[META_API][PRE_FILTER] total_ads={len(ad_list)}, ad_list_type={type(ad_list).__name__}")
    
    for idx, ad in enumerate(ad_list[:3]):
        ad_id_val = ad.get("ad_id") if isinstance(ad, dict) else None
        ad_name_val = ad.get("ad_name", "N/A")[:40] if isinstance(ad, dict) else "N/A"
        account_id_val = ad.get("account_id") if isinstance(ad, dict) else None
        has_creative_id = "creative_id" in ad if isinstance(ad, dict) else False
        has_creative = "creative" in ad if isinstance(ad, dict) else False
        has_object_story_spec = "object_story_spec" in ad if isinstance(ad, dict) else False
        ad_keys = list(ad.keys()) if isinstance(ad, dict) else []
        
        logger.warning(
            f"[META_API][PRE_FILTER] idx={idx}, "
            f"ad_id={ad_id_val}, "
            f"account_id={account_id_val}, "
            f"ad_name={ad_name_val}, "
            f"has_creative_id={has_creative_id}, "
            f"has_creative={has_creative}, "
            f"has_object_story_spec={has_object_story_spec}, "
            f"ad_type={type(ad).__name__}, "
            f"keys={ad_keys}"
        )
    
    # ad_list 요소 중 ad_id가 없는 것이 있는지 사전 검사
    ads_without_id = [i for i, ad in enumerate(ad_list) if not (isinstance(ad, dict) and ad.get("ad_id"))]
    if ads_without_id:
        logger.warning(f"[META_API][PRE_FILTER] ⚠️ ad_id 누락된 인덱스: {ads_without_id[:10]}... (총 {len(ads_without_id)}개)")
    else:
        logger.warning(f"[META_API][PRE_FILTER] ✅ 모든 광고에 ad_id 존재함")
    
    logger.warning(f"[META_API][PRE_FILTER] ========== 병렬 처리 직전 ad_list 검사 완료 ==========")

    # ✅ 병렬 처리로 Meta API 호출 최적화
    logger.warning("[META_API][PARALLEL] 병렬 처리로 광고 상세 정보 수집 시작")
    api_start = time.time()
    results = get_ads_details_parallel(ad_list)
    api_time = time.time() - api_start
    logger.warning(f"[META_API][PARALLEL] 광고 상세 정보 수집 완료: {len(results)}개, {api_time:.2f}초")
    
    total_time = time.time() - start_time
    logger.warning(f"[META_API][DONE] 전체 처리 완료: {total_time:.2f}초")
    
    return results


def get_ads_details_parallel(ad_list):
    """
    병렬 처리로 광고 상세 정보를 수집합니다.
    """
    total_count = len(ad_list)
    start_time = time.time()
    logger.warning(f"[META_API][PARALLEL_START] get_ads_details_parallel 시작: {total_count}개 광고 처리")
    
    if not ad_list:
        logger.warning("[META_API][PARALLEL_EMPTY] ⚠️ ad_list가 비어있습니다!")
        return []
    
    # ✅ [INPUT] 첫 3개 광고 샘플 디버그 로그
    for idx, ad in enumerate(ad_list[:3]):
        ad_id_val = ad.get("ad_id") if isinstance(ad, dict) else None
        has_creative_id = "creative_id" in ad if isinstance(ad, dict) else False
        has_creative = "creative" in ad if isinstance(ad, dict) else False
        ad_keys = list(ad.keys()) if isinstance(ad, dict) else []
        logger.warning(
            f"[META_API][INPUT] idx={idx}, "
            f"ad_id={ad_id_val}, "
            f"has_creative_id={has_creative_id}, "
            f"has_creative={has_creative}, "
            f"ad_type={type(ad).__name__}, "
            f"keys={ad_keys}"
        )
    
    results = []
    success_count = 0
    fail_count = 0
    
    # ✅ 스킵 사유별 카운트 (thread-safe)
    skip_reasons = defaultdict(int)
    skip_reasons_lock = threading.Lock()
    
    # ThreadPoolExecutor를 사용한 병렬 처리
    logger.warning(f"[META_API][EXECUTOR] ThreadPoolExecutor 시작 (max_workers=5)")
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 각 광고에 대해 병렬로 상세 정보 수집
        future_to_ad = {
            executor.submit(get_single_ad_details, ad): ad 
            for ad in ad_list
        }
        logger.warning(f"[META_API][EXECUTOR] {len(future_to_ad)}개 future 생성 완료")
        
        # 완료된 작업들을 순서대로 처리
        processed_count = 0
        for future in as_completed(future_to_ad):
            ad = future_to_ad[future]
            ad_id_for_log = ad.get("ad_id", "UNKNOWN") if isinstance(ad, dict) else "INVALID"
            processed_count += 1
            
            try:
                result, skip_reason = future.result()
                if result:  # 유효한 결과만 추가
                    results.append(result)
                    success_count += 1
                    logger.warning(f"[META_API][SUCCESS] ad_id={ad_id_for_log} (processed={processed_count}/{total_count})")
                else:
                    fail_count += 1
                    # ✅ [NONE] result가 None인 경우 상세 로깅
                    logger.warning(
                        f"[META_API][NONE] ad_id={ad_id_for_log}, "
                        f"skip_reason={skip_reason}, "
                        f"processed={processed_count}/{total_count}"
                    )
                    # ✅ 스킵 사유 카운트
                    with skip_reasons_lock:
                        skip_reasons[skip_reason or "unknown"] += 1
            except RuntimeError as e:
                # 토큰 누락 시 즉시 에러 전파 (조용히 0개 반환 금지)
                logger.error(f"[META_API][RUNTIME_ERROR] 토큰 에러로 처리 중단: ad_id={ad_id_for_log}, error={e}")
                raise
            except Exception as e:
                fail_count += 1
                with skip_reasons_lock:
                    skip_reasons[f"exception_{type(e).__name__}"] += 1
                logger.exception(
                    f"[META_API][FUTURE_EXCEPTION] ad_id={ad_id_for_log}, "
                    f"exception={type(e).__name__}: {e}"
                )
                continue
    
    elapsed_time = time.time() - start_time
    
    # ✅ 최종 수집 결과 요약 로그 (1회)
    logger.warning(
        f"[META_API][SUMMARY] 📊 수집 결과 요약: "
        f"요청={total_count}개, 성공={success_count}개, 실패={fail_count}개, "
        f"경과시간={elapsed_time:.2f}초"
    )
    
    # ✅ 스킵 사유별 카운트 요약 로그 (1회)
    if skip_reasons:
        reasons_str = ", ".join([f"{k}={v}" for k, v in sorted(skip_reasons.items())])
        logger.warning(f"[META_API][SKIP_SUMMARY] 📋 스킵 사유별 카운트: {reasons_str}")
    else:
        logger.warning(f"[META_API][SKIP_SUMMARY] 스킵 사유 없음 (모두 성공 또는 예외)")
    
    return results


def get_single_ad_details(ad):
    """
    단일 광고의 상세 정보를 수집합니다.
    
    Returns:
        tuple: (result_dict, skip_reason) - 성공 시 (dict, None), 실패 시 (None, "reason_string")
    """
    # ✅ [ENTER] 무조건 찍히는 진입 로그 (맨 첫 줄)
    ad_id_raw = ad.get("ad_id") if isinstance(ad, dict) else None
    logger.warning(f"[META_API][ENTER] get_single_ad_details ad_id={ad_id_raw}, ad_type={type(ad).__name__}")
    
    # ✅ ad dict 검증 및 기본값 추출
    if not ad or not isinstance(ad, dict):
        logger.warning(f"[META_API][SKIP] reason=invalid_ad_dict, ad_type={type(ad).__name__}, ad_value={str(ad)[:100]}")
        return None, "invalid_ad_dict"
    
    ad_id = ad.get("ad_id")
    ad_name = ad.get("ad_name", "UNKNOWN")
    account_id = ad.get("account_id", "UNKNOWN")
    instagram_acc_name = ad.get("instagram_acc_name", "")
    ad_keys = list(ad.keys())
    
    # ✅ ad_id 필수 검증
    if not ad_id:
        logger.warning(
            f"[META_API][SKIP] reason=missing_ad_id, "
            f"account_id={account_id}, ad_name={ad_name[:50]}, "
            f"keys={ad_keys}"
        )
        return None, "missing_ad_id"
    
    logger.warning(f"[META_API][DETAIL_START] ad_id={ad_id}, ad_name={ad_name[:50]}, account_id={account_id}")
    
    # ✅ 호출 시점에 토큰 읽기 (토큰 없으면 RuntimeError 발생)
    try:
        access_token = _get_meta_access_token()
    except RuntimeError as e:
        logger.error(f"[META_API][SKIP] reason=token_missing, ad_id={ad_id}, error={e}")
        raise  # 토큰 에러는 전파
    
    try:
        # 1차 요청: 크리에이티브 ID (타임아웃 단축)
        creative_url = f"https://graph.facebook.com/v24.0/{ad_id}?fields=adcreatives&access_token={access_token}"
        logger.warning(f"[META_API][API_CALL_1] adcreatives 요청: ad_id={ad_id}")
        
        creative_data, api_error = _safe_meta_api_get(creative_url, timeout=3, context=f"adcreatives ad_id={ad_id}")
        if creative_data is None:
            skip_reason = f"adcreatives_api_{api_error}"
            logger.warning(
                f"[META_API][SKIP] reason={skip_reason}, "
                f"ad_id={ad_id}, account_id={account_id}, ad_name={ad_name[:50]}"
            )
            return None, skip_reason
        
        logger.warning(f"[META_API][API_RESP_1] adcreatives 응답 수신: ad_id={ad_id}, keys={list(creative_data.keys())}")
        
        # ✅ adcreatives 응답 구조 검증
        adcreatives = creative_data.get("adcreatives")
        if not adcreatives:
            logger.warning(
                f"[META_API][SKIP] reason=no_adcreatives_field, "
                f"ad_id={ad_id}, account_id={account_id}, "
                f"response_keys={list(creative_data.keys())}"
            )
            return None, "no_adcreatives_field"
        
        adcreatives_data = adcreatives.get("data", [])
        if not adcreatives_data or len(adcreatives_data) == 0:
            logger.warning(
                f"[META_API][SKIP] reason=empty_adcreatives_data, "
                f"ad_id={ad_id}, account_id={account_id}, "
                f"adcreatives={adcreatives}"
            )
            return None, "empty_adcreatives_data"
        
        creative_id = adcreatives_data[0].get("id")
        if not creative_id:
            logger.warning(
                f"[META_API][SKIP] reason=missing_creative_id, "
                f"ad_id={ad_id}, account_id={account_id}, "
                f"adcreatives_data[0]={adcreatives_data[0]}"
            )
            return None, "missing_creative_id"
        
        logger.warning(f"[META_API][CREATIVE_OK] ad_id={ad_id}, creative_id={creative_id}")

        # 2차 요청: 상세 정보 (타임아웃 단축) - asset_feed_spec 포함하여 자동 형식 광고 지원
        detail_url = (
            f"https://graph.facebook.com/v24.0/{creative_id}"
            f"?fields=body,object_story_spec,image_url,video_id,asset_feed_spec"
            f"&access_token={access_token}"
        )
        logger.warning(f"[META_API][API_CALL_2] creative_detail 요청: creative_id={creative_id}")
        
        detail_data, api_error = _safe_meta_api_get(detail_url, timeout=3, context=f"creative_detail creative_id={creative_id}")
        if detail_data is None:
            skip_reason = f"creative_detail_api_{api_error}"
            logger.warning(
                f"[META_API][SKIP] reason={skip_reason}, "
                f"ad_id={ad_id}, creative_id={creative_id}, account_id={account_id}"
            )
            return None, skip_reason
        
        logger.warning(f"[META_API][API_RESP_2] creative_detail 응답 수신: creative_id={creative_id}, keys={list(detail_data.keys())}")

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
            video_api = (
                f"https://graph.facebook.com/v24.0/{extracted_video_id}"
                f"?fields=source&access_token={access_token}"
            )
            video_data, video_error = _safe_meta_api_get(video_api, timeout=3, context=f"video_source video_id={extracted_video_id}")
            if video_data:
                video_url = video_data.get("source")
            else:
                logger.warning(f"[META_API][VIDEO_FALLBACK] 비디오 source 조회 실패 (ad_id={ad_id}, error={video_error}), 썸네일로 폴백")
            
            # 2단계: 비디오 source가 없거나 실패한 경우, 고화질 썸네일 조회
            if not video_url:
                thumb_url = f"https://graph.facebook.com/v24.0/{extracted_video_id}?fields=thumbnails&access_token={access_token}"
                thumb_data, thumb_error = _safe_meta_api_get(thumb_url, timeout=2, context=f"video_thumbnails video_id={extracted_video_id}")
                if thumb_data:
                    thumbnails = thumb_data.get("thumbnails", {}).get("data", [])
                    if thumbnails:
                        # 해상도(width * height)가 가장 높은 썸네일 선택 (고화질)
                        high_quality_thumbnail = max(
                            thumbnails, 
                            key=lambda x: x.get("width", 0) * x.get("height", 0)
                        ).get("uri", "")
                        logger.warning(f"[META_API][THUMB_OK] 고화질 썸네일 추출 성공 (ad_id={ad_id})")
        
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
            logger.warning(
                f"[META_API][SKIP] reason=no_image_or_video_url, "
                f"ad_id={ad_id}, account_id={account_id}, ad_name={ad_name[:50]}, "
                f"detail_keys={list(detail_data.keys())}"
            )
            return None, "no_image_or_video_url"
        
        # ✅ 이미지 URL을 프록시 URL로 변환 (배포 환경 대응)
        proxy_image_url = get_proxy_image_url(image_url) if image_url else ""
        
        logger.warning(f"[META_API][DETAIL_OK] ✅ 광고 상세 수집 성공: ad_id={ad_id}, has_image={bool(image_url)}, has_video={bool(video_url)}")
        
        return {
            "ad_id": ad_id,
            "ad_name": ad["ad_name"],
            "instagram_acc_name": instagram_acc_name,
            "message": message,
            "link": link,
            "image_url": proxy_image_url,  # 프록시 URL로 변환된 썸네일 또는 이미지 광고용
            "video_url": video_url,  # 비디오 광고 원본 URL (있을 경우)
            "is_video": bool(extracted_video_id)
        }, None  # 성공 시 skip_reason = None

    except Exception as e:
        skip_reason = f"exception_{type(e).__name__}"
        logger.exception(
            f"[META_API][SKIP] reason={skip_reason}, "
            f"ad_id={ad_id}, account_id={account_id}, ad_name={ad_name[:50]}"
        )
        return None, skip_reason
