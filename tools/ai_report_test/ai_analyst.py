"""
AI 분석 모듈
- Google Gemini API를 사용하여 월간 리포트 스냅샷 데이터를 분석
- 섹션별 분석 텍스트를 생성하여 signals 필드에 추가
- 섹션별 개별 API 호출 방식으로 정확도 향상
"""

import os
import sys
import json
import gzip
import re
import traceback
from typing import Dict, Optional, List, Any
from datetime import datetime

# .env 파일에서 환경 변수 로드
try:
    from dotenv import load_dotenv
    # 여러 경로에서 .env 파일 찾기 시도
    env_loaded = False
    
    # 1. 현재 작업 디렉토리에서 찾기
    cwd_env = os.path.join(os.getcwd(), ".env")
    if os.path.exists(cwd_env):
        load_dotenv(cwd_env, override=True)
        env_loaded = True
        print(f"✅ [INFO] .env 파일 로드됨: {cwd_env}", file=sys.stderr)
    
    # 2. 스크립트 위치 기준으로 프로젝트 루트 찾기
    if not env_loaded:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))  # tools/ai_report_test/ -> 프로젝트 루트
        env_path = os.path.join(project_root, ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
            env_loaded = True
            print(f"✅ [INFO] .env 파일 로드됨: {env_path}", file=sys.stderr)
    
    # 3. 기본 load_dotenv() 시도 (현재 디렉토리 및 상위 디렉토리 자동 탐색)
    if not env_loaded:
        load_dotenv(override=True)  # .env 파일이 없어도 에러 없이 진행
        
except ImportError:
    print("⚠️ [WARN] python-dotenv 패키지가 설치되지 않았습니다.", file=sys.stderr)
    print("   설치: pip install python-dotenv", file=sys.stderr)

# Google Gen AI SDK (v1.0+) 최신 버전 사용
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    types = None
    print("⚠️ [WARN] google-genai 패키지가 설치되지 않았습니다.", file=sys.stderr)
    print("   설치: pip install google-genai", file=sys.stderr)

try:
    from google.cloud import storage
except ImportError:
    print("⚠️ [WARN] google-cloud-storage 패키지가 설치되지 않았습니다.", file=sys.stderr)
    print("   설치: pip install google-cloud-storage", file=sys.stderr)
    storage = None

# 환경 변수
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# System Prompt는 별도 파일에서 로드하거나 함수 파라미터로 받음
DEFAULT_SYSTEM_PROMPT_TEMPLATE = """
당신은 전자상거래 데이터 분석 전문가입니다.
제공된 월간 리포트 데이터를 분석하여 각 섹션별로 인사이트를 제공해주세요.

[분석 요구사항]
1. 데이터 기반의 객관적 분석
2. 구체적인 수치 인용
3. 실용적인 인사이트 제공
4. 한국어로 작성

[출력 형식]
각 섹션별로 분석 텍스트를 제공하되, 섹션 7의 경우 마지막에 JSON 비교표를 포함해주세요.
"""


# ============================================
# 유틸리티 함수
# ============================================

def safe_get(data: Dict, *keys, default: Any = None) -> Any:
    """
    안전한 딕셔너리 접근 함수 (중첩된 키 경로 지원)
    
    Args:
        data: 딕셔너리 데이터
        *keys: 키 경로 (예: 'facts', 'ga4_traffic', 'this')
        default: 기본값 (키가 없을 때 반환)
    
    Returns:
        찾은 값 또는 default
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current if current is not None else default


def safe_get_list(data: Dict, *keys, default: List = None) -> List:
    """리스트를 반환하는 safe_get (기본값은 빈 리스트)"""
    result = safe_get(data, *keys, default=default)
    if result is None:
        return []
    if isinstance(result, list):
        return result
    return []


def safe_get_dict(data: Dict, *keys, default: Dict = None) -> Dict:
    """딕셔너리를 반환하는 safe_get (기본값은 빈 딕셔너리)"""
    result = safe_get(data, *keys, default=default)
    if result is None:
        return {}
    if isinstance(result, dict):
        return result
    return {}


def log_prompt_to_file(section_num: int, prompt: str, log_file: str = "debug_prompts.log"):
    """
    프롬프트를 로그 파일에 저장
    
    Args:
        section_num: 섹션 번호
        prompt: 프롬프트 내용
        log_file: 로그 파일 경로
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"""
{'='*80}
[섹션 {section_num}] 프롬프트 로그 - {timestamp}
{'='*80}
{prompt}
{'='*80}

"""
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        print(f"📝 [INFO] 섹션 {section_num} 프롬프트가 {log_file}에 저장되었습니다.", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ [WARN] 프롬프트 로그 저장 실패: {e}", file=sys.stderr)


def parse_gcs_path(gcs_path: str) -> tuple:
    """
    GCS 경로를 파싱하여 버킷명과 blob 경로를 반환
    
    Args:
        gcs_path: gs://bucket-name/path/to/file.json.gz 형태의 경로
    
    Returns:
        (bucket_name, blob_path) 튜플
    """
    if not gcs_path.startswith("gs://"):
        raise ValueError(f"GCS 경로는 'gs://'로 시작해야 합니다: {gcs_path}")
    
    # gs:// 제거 후 파싱
    path_without_scheme = gcs_path[5:]  # "gs://" 제거
    parts = path_without_scheme.split("/", 1)
    
    if len(parts) < 2:
        raise ValueError(f"GCS 경로 형식이 올바르지 않습니다: {gcs_path}")
    
    bucket_name = parts[0]
    blob_path = parts[1]
    
    return bucket_name, blob_path


def load_from_gcs(gcs_path: str) -> Dict:
    """
    GCS에서 JSON 파일을 다운로드하여 로드 (gzip 압축 자동 처리)
    
    Args:
        gcs_path: gs://bucket-name/path/to/file.json.gz 형태의 GCS 경로
    
    Returns:
        JSON 데이터 (Dict)
    """
    if storage is None:
        raise ImportError("google-cloud-storage 패키지가 설치되지 않았습니다. 'pip install google-cloud-storage'로 설치해주세요.")
    
    try:
        # GCS 경로 파싱
        bucket_name, blob_path = parse_gcs_path(gcs_path)
        
        # GCS 클라이언트 생성
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        # 파일이 존재하는지 확인
        if not blob.exists():
            raise FileNotFoundError(f"GCS 파일을 찾을 수 없습니다: {gcs_path}")
        
        # Signed URL은 private key(서명)가 필요해서 Cloud Run/ADC 토큰 환경에서 실패할 수 있음.
        # GCS SDK로 원본 바이트를 직접 다운로드하면 서명 없이 동작하며,
        # raw_download=True로 자동 디코딩/압축 해제를 막고 우리가 직접 gzip 처리 가능.
        file_bytes = blob.download_as_bytes(raw_download=True)
        
        # Hybrid Reader: gzip 압축 해제 시도, 실패 시 일반 텍스트로 처리
        json_str = None
        is_gzipped = blob_path.endswith(".gz") or blob.content_encoding == "gzip"
        
        if is_gzipped:
            try:
                # gzip 압축 해제 시도
                decompressed_bytes = gzip.decompress(file_bytes)
                json_str = decompressed_bytes.decode('utf-8')
                print(f"📦 [INFO] Gzip 압축 해제 성공", file=sys.stderr)
            except (gzip.BadGzipFile, OSError) as e:
                # gzip이 아니면 일반 텍스트로 처리
                print(f"⚠️ [WARN] Gzip 압축 해제 실패, 일반 텍스트로 처리: {e}", file=sys.stderr)
                json_str = file_bytes.decode('utf-8')
        else:
            # 일반 텍스트로 디코딩
            json_str = file_bytes.decode('utf-8')
        
        # JSON 파싱
        data = json.loads(json_str)
        
        print(f"✅ [SUCCESS] GCS에서 파일 로드 완료: {gcs_path}", file=sys.stderr)
        return data
        
    except Exception as e:
        error_msg = f"GCS 파일 로드 실패: {str(e)}"
        print(f"❌ [ERROR] {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise


def upload_to_gcs(data: Dict, gcs_path: str) -> None:
    """
    JSON 데이터를 GCS에 업로드 (gzip 압축 자동 처리)
    
    Args:
        data: 업로드할 JSON 데이터 (Dict)
        gcs_path: gs://bucket-name/path/to/file.json.gz 형태의 GCS 경로
    """
    if storage is None:
        raise ImportError("google-cloud-storage 패키지가 설치되지 않았습니다. 'pip install google-cloud-storage'로 설치해주세요.")
    
    try:
        # GCS 경로 파싱
        bucket_name, blob_path = parse_gcs_path(gcs_path)
        
        # JSON 문자열로 변환
        json_str = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        json_bytes = json_str.encode('utf-8')
        
        # gzip 압축 여부 확인
        is_gzipped = blob_path.endswith(".gz")
        
        if is_gzipped:
            # gzip 압축
            compressed_bytes = gzip.compress(json_bytes)
            upload_bytes = compressed_bytes
            content_encoding = "gzip"
        else:
            upload_bytes = json_bytes
            content_encoding = None
        
        # GCS 클라이언트 생성
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        # 메타데이터 설정
        blob.content_type = "application/json"
        if content_encoding:
            blob.content_encoding = content_encoding
        
        # 업로드
        blob.upload_from_string(upload_bytes, content_type="application/json")
        
        print(f"✅ [SUCCESS] GCS에 파일 업로드 완료: {gcs_path}", file=sys.stderr)
        
    except Exception as e:
        error_msg = f"GCS 파일 업로드 실패: {str(e)}"
        print(f"❌ [ERROR] {error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise


def load_system_prompt(prompt_file: Optional[str] = None) -> str:
    """
    System Prompt를 파일에서 로드하거나 기본 템플릿 반환
    
    Args:
        prompt_file: System Prompt 파일 경로 (선택사항)
    
    Returns:
        System Prompt 문자열
    """
    if prompt_file and os.path.exists(prompt_file):
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"⚠️ [WARN] System Prompt 파일 로드 실패: {e}", file=sys.stderr)
            print(f"   기본 템플릿 사용", file=sys.stderr)
            return DEFAULT_SYSTEM_PROMPT_TEMPLATE
    else:
        return DEFAULT_SYSTEM_PROMPT_TEMPLATE


# ============================================
# 섹션별 프롬프트 생성 함수
# ============================================

def build_section_prompt(section_num: int, snapshot_data: Dict) -> str:
    """
    섹션별 프롬프트 생성 (안전한 데이터 접근 및 명확한 지시)
    
    Args:
        section_num: 섹션 번호 (1-9)
        snapshot_data: 스냅샷 JSON 데이터
    
    Returns:
        섹션별 프롬프트 문자열
    """
    facts = safe_get_dict(snapshot_data, "facts", default={})
    report_meta = safe_get_dict(snapshot_data, "report_meta", default={})
    company_name = safe_get(report_meta, "company_name", default="업체")
    report_month = safe_get(report_meta, "report_month", default="")
    
    # 섹션별 데이터 준비
    section_data_map = {
        1: {
            "mall_sales_this": safe_get_dict(facts, "mall_sales", "this", default={}),
            "mall_sales_prev": safe_get_dict(facts, "mall_sales", "prev", default={}),
            "comparisons": safe_get_dict(facts, "comparisons", "mall_sales", default={}),
            "daily_this": safe_get_list(facts, "mall_sales", "daily_this", default=[]),
            "events": safe_get_list(facts, "events", default=[]),
        },
        2: {
            "ga4_traffic_this": safe_get_dict(facts, "ga4_traffic", "this", default={}),
            "top_sources": safe_get_list(facts, "ga4_traffic", "this", "top_sources", default=[]),
        },
        3: {
            "ga4_totals": safe_get_dict(facts, "ga4_traffic", "this", "totals", default={}),
            "mall_sales_this": safe_get_dict(facts, "mall_sales", "this", default={}),
        },
        4: {
            "top_products_sales": safe_get_list(facts, "products", "this", "rolling", "d30", "top_products_by_sales", default=[])[:5],
            "top_items_view": safe_get_list(facts, "viewitem", "this", "top_items_by_view_item", default=[])[:5],
        },
        5: {
            "29cm_items": safe_get_list(facts, "29cm_best", "items", default=[])[:10],
        },
        6: {
            "meta_ads_goals_this": safe_get_dict(facts, "meta_ads_goals", "this", default={}),
            "top_ads": safe_get_dict(facts, "meta_ads_goals", "this", "top_ads", default={}),
        },
        7: {
            "29cm_items": safe_get_list(facts, "29cm_best", "items", default=[])[:10],
            "top_products_sales": safe_get_list(facts, "products", "this", "rolling", "d30", "top_products_by_sales", default=[])[:10],
        },
        8: {
            "mall_sales_this": safe_get_dict(facts, "mall_sales", "this", default={}),
            "forecast": safe_get_dict(facts, "forecast_next_month", default={}),
            "mall_sales_forecast": safe_get_dict(facts, "forecast_next_month", "mall_sales", default={}),
        },
        9: {
            "mall_sales_this": safe_get_dict(facts, "mall_sales", "this", default={}),
            "meta_ads_this": safe_get_dict(facts, "meta_ads", "this", default={}),
            "ga4_totals": safe_get_dict(facts, "ga4_traffic", "this", "totals", default={}),
            "signals": safe_get_dict(snapshot_data, "signals", default={}),
        },
    }
    
    section_data = section_data_map.get(section_num, {})
    
    # 섹션별 프롬프트 템플릿
    section_prompts = {
        1: f"""
[섹션 1: 지난달 매출 분석]
{company_name}의 {report_month} 매출 데이터를 분석해주세요.

⚠️ **중요: 이 섹션 1만 분석하고 답변하세요. 다른 섹션은 언급하지 마세요.**

데이터:
- 이번 달 매출: {json.dumps(section_data.get('mall_sales_this', {}), ensure_ascii=False, indent=2)}
- 전월 매출: {json.dumps(section_data.get('mall_sales_prev', {}), ensure_ascii=False, indent=2)}
- 비교 데이터: {json.dumps(section_data.get('comparisons', {}), ensure_ascii=False, indent=2)}
- 일별 매출 (이번 달): {json.dumps(section_data.get('daily_this', [])[:10], ensure_ascii=False, indent=2)}
- 이벤트: {json.dumps(section_data.get('events', [])[:5], ensure_ascii=False, indent=2)}

분석 요청:
- 매출 증감 요인 분석
- 주요 성과 지표 해석
- 전월 대비 변화 인사이트
- 이벤트와 매출의 인과관계

🛑 **절대적 제한: 반드시 1000자 이내로 작성하고 마무리하세요. 1000자를 초과하면 응답이 거부됩니다. 핵심 내용만 간결하게 요약하세요.**
""",
        2: f"""
[섹션 2: 주요 유입 채널]
{company_name}의 {report_month} 유입 채널 데이터를 분석해주세요.

⚠️ **중요: 이 섹션 2만 분석하고 답변하세요. 다른 섹션은 언급하지 마세요.**

데이터:
- GA4 트래픽: {json.dumps(section_data.get('ga4_traffic_this', {}), ensure_ascii=False, indent=2)}
- 상위 유입 소스: {json.dumps(section_data.get('top_sources', []), ensure_ascii=False, indent=2)}

분석 요청:
- 주요 유입 채널 성과 분석
- 채널별 이탈률 및 전환율 해석
- 채널 최적화 제안

🛑 **절대적 제한: 반드시 1000자 이내로 작성하고 마무리하세요. 1000자를 초과하면 응답이 거부됩니다. 핵심 내용만 간결하게 요약하세요.**
""",
        3: f"""
[섹션 3: 고객 방문 및 구매 여정]
{company_name}의 {report_month} 고객 여정 데이터를 분석해주세요.

⚠️ **중요: 이 섹션 3만 분석하고 답변하세요. 다른 섹션은 언급하지 마세요.**

데이터:
- GA4 퍼널: {json.dumps(section_data.get('ga4_totals', {}), ensure_ascii=False, indent=2)}
- 매출 데이터: {json.dumps(section_data.get('mall_sales_this', {}), ensure_ascii=False, indent=2)}

분석 요청:
- 유입 → 장바구니 → 구매 전환율 분석
- 여정별 이탈 지점 파악
- 전환율 개선 제안

🛑 **절대적 제한: 반드시 1000자 이내로 작성하고 마무리하세요. 1000자를 초과하면 응답이 거부됩니다. 핵심 내용만 간결하게 요약하세요.**
""",
        4: f"""
[섹션 4: 자사몰 베스트 상품 성과]
{company_name}의 {report_month} 베스트 상품 데이터를 분석해주세요.

⚠️ **중요: 이 섹션 4만 분석하고 답변하세요. 다른 섹션은 언급하지 마세요.**

데이터:
- 베스트 상품 (매출 기준): {json.dumps(section_data.get('top_products_sales', []), ensure_ascii=False, indent=2)}
- 베스트 상품 (조회 기준): {json.dumps(section_data.get('top_items_view', []), ensure_ascii=False, indent=2)}

분석 요청:
1. **[필수 제약]**: '제품번호(ID)'는 내부 관리용이므로 **절대 출력하지 마십시오.** 상품명만 언급하세요.
2. **[필수 제약]**: 통화 단위는 'KRW' 대신 **한글 '원'**으로 표기하세요. (예: 1,308,000원)
3. 단순 나열보다 '저조회 고효율(알짜상품)'과 '고조회 저효율(아쉬운 상품)'을 대비하여 인사이트를 제공하세요.
4. 베스트 상품 성과 분석
5. 매출 vs 조회수 비교 인사이트
6. 상품 포트폴리오 개선 제안

🛑 **절대적 제한: 반드시 1000자 이내로 작성하고 마무리하세요. 1000자를 초과하면 응답이 거부됩니다. 핵심 내용만 간결하게 요약하세요.**
""",
        5: f"""
[섹션 5: 시장 트렌드 확인 (29CM)]
{company_name}의 {report_month} 시장 트렌드 데이터를 분석해주세요.

⚠️ **중요: 이 섹션 5만 분석하고 답변하세요. 다른 섹션은 언급하지 마세요.**

데이터:
- 29CM 베스트 상품: {json.dumps(section_data.get('29cm_items', []), ensure_ascii=False, indent=2)}

분석 요청:
- 시장 트렌드 분석
- 인기 상품 카테고리/가격대 파악
- 시장 기회 포착

🛑 **절대적 제한: 반드시 1000자 이내로 작성하고 마무리하세요. 1000자를 초과하면 응답이 거부됩니다. 핵심 내용만 간결하게 요약하세요.**
""",
        6: f"""
[섹션 6: 매체 성과 및 효율 진단]
{company_name}의 {report_month} 광고 매체 데이터를 분석해주세요.

⚠️ **중요: 이 섹션 6만 분석하고 답변하세요. 다른 섹션은 언급하지 마세요.**

데이터:
- Meta Ads 성과: {json.dumps(section_data.get('meta_ads_goals_this', {}), ensure_ascii=False, indent=2)}
- 상위 광고: {json.dumps(section_data.get('top_ads', {}), ensure_ascii=False, indent=2)}

분석 요청:
1. **No Data Repetition (숫자 나열 금지)**:
   - 좌측 데이터 패널에 있는 지출액, 노출수, 클릭수, 구체적인 ROAS(소수점 단위)를 본문에 단순 나열하지 마십시오.
   - **Ad ID (예: 12023...)는 절대로 표기하지 마십시오.** (가독성 저하 주원인)
   
2. **Format Comparison (소재 형식 비교)**:
   - 개별 광고보다는 **'형식(Format)'** 위주로 분석하십시오. (예: "카탈로그 슬라이드가 영상 소재보다 구매 전환율이 월등히 높습니다.")
   - 영상 소재와 이미지 소재의 성과 차이를 비교하십시오.

3. **Strategic Insight (전략적 제안)**:
   - "숫자 읽어주기"가 아니라 "왜 이 소재가 잘 되었는지"를 추론하십시오.
   - 유입 캠페인(Traffic)과 전환 캠페인(Conversion)의 역할 분담이 잘 되고 있는지 진단하십시오.
   - 예산 재배치(Budget Reallocation)에 대한 구체적인 조언을 제공하십시오.

🛑 **절대적 제한: Ad ID 출력 금지. 수치는 '약 400% 대', '10% 가량' 등으로 둥글게 표현하여 흐름을 끊지 말 것. 반드시 1000자 이내로 작성하고 마무리하세요.**
""",
        7: f"""
[섹션 7: 시장 트렌드와 자사몰 비교]
{company_name}의 {report_month} 시장 비교 데이터를 분석해주세요.

⚠️ **중요: 이 섹션 7만 분석하고 답변하세요. 다른 섹션은 언급하지 마세요.**

데이터:
- 29CM 베스트: {json.dumps(section_data.get('29cm_items', []), ensure_ascii=False, indent=2)}
- 자사몰 상품: {json.dumps(section_data.get('top_products_sales', []), ensure_ascii=False, indent=2)}

분석 요청:
- **경향성 중심 분석**: 모든 상품을 개별적으로 나열하지 말고, 전체적인 시장 경향성과 트렌드만 요약하세요.
- **핵심 차별점 강조**: 자사몰과 시장 간의 핵심 차별점(가격대, 카테고리, 타겟 고객층)만 명확히 비교하세요.
- 구체적인 브랜드명이나 상품명은 필요시 2-3개만 대표적으로 언급하고, 나머지는 경향성으로 요약하세요.

🛑 **절대적 제한: 반드시 1000자 이내로 작성하고 마무리하세요. 1000자를 초과하면 응답이 거부됩니다. 핵심 내용만 간결하게 요약하세요.**

[중요] 분석 텍스트 마지막에 다음 형식의 JSON 비교표를 포함해주세요:
```json
{{
  "주력_아이템": {{
    "market": "29CM 시장의 주력 아이템",
    "company": "자사몰의 주력 아이템"
  }},
  "평균_가격": {{
    "market": "29CM 평균 가격",
    "company": "자사몰 평균 가격"
  }},
  "핵심_소재": {{
    "market": "29CM 인기 소재",
    "company": "자사몰 주요 소재"
  }},
  "타겟_고객층": {{
    "market": "29CM 타겟 고객",
    "company": "자사몰 타겟 고객"
  }},
  "가격대": {{
    "market": "29CM 가격대",
    "company": "자사몰 가격대"
  }}
}}
```
""",
        8: f"""
[섹션 8: 익월 목표 설정 및 시장 전망]
{company_name}의 {report_month} 전망 데이터를 분석해주세요.

⚠️ **중요: 이 섹션 8만 분석하고 답변하세요. 다른 섹션은 언급하지 마세요.**

데이터:
- 이번 달 실적: {json.dumps(section_data.get('mall_sales_this', {}), ensure_ascii=False, indent=2)}
- 기계적 예측치: {json.dumps(section_data.get('forecast', {}), ensure_ascii=False, indent=2)}

분석 요청:
1. **[중요] 기계적 예측의 한계 돌파**: 제공된 '기계적 예측치'는 작년 하락폭을 그대로 반영한 보수적 수치입니다. 이를 그대로 목표로 삼지 마십시오.
2. **[도전적 목표 설정]**: 최근 베스트 상품의 호조와 광고 성과를 근거로, 기계적 예측치보다 **상향 조정된 '희망적이고 도전적인 목표 매출'**을 제안하세요.
   - 예: "단순 예측은 250만원이나, 최근 세트 상품의 호조를 감안하여 500만원을 목표로 도전해볼 만합니다."
3. 시장의 비수기 요인(연휴 등)을 언급하되, 이를 극복할 방어 논리를 함께 제시하세요.

🛑 **절대적 제한: 반드시 1000자 이내로 작성하고 마무리하세요. 1000자를 초과하면 응답이 거부됩니다. 핵심 내용만 간결하게 요약하세요.**
""",
        9: f"""
[섹션 9: 데이터 기반 전략 액션 플랜]
{company_name}의 {report_month} 전체 데이터를 종합하여 전략을 제안해주세요.

⚠️ **중요: 이 섹션 9만 분석하고 답변하세요. 다른 섹션은 언급하지 마세요.**

데이터 요약:
- 매출: {json.dumps(section_data.get('mall_sales_this', {}), ensure_ascii=False, indent=2)}
- 광고: {json.dumps(section_data.get('meta_ads_this', {}), ensure_ascii=False, indent=2)}
- 유입: {json.dumps(section_data.get('ga4_totals', {}), ensure_ascii=False, indent=2)}
- 신호: {json.dumps(section_data.get('signals', {}), ensure_ascii=False, indent=2)}

분석 요청:
- 종합 전략 액션 플랜
- 우선순위별 실행 방안
- KPI 및 목표 설정

🛑 **절대적 제한: 반드시 1000자 이내로 작성하고 마무리하세요. 1000자를 초과하면 응답이 거부됩니다. 핵심 내용만 간결하게 요약하세요.**

[중요] 각 전략은 반드시 **`###` (헤더3)**로 구분하여 작성하십시오:
  ### 💡 [전략 1] (제목)
  (내용...)
  
  ### 🎯 [전략 2] (제목)
  (내용...)
  
  ### 📦 [전략 3] (제목)
  (내용...)
"""
    }
    
    return section_prompts.get(section_num, "")


# ============================================
# 응답 파싱 함수
# ============================================

def extract_section_content(full_text: str, target_section: int) -> str:
    """
    AI 응답에서 특정 섹션의 내용만 추출 (제목 제거 및 본문 확보)
    """
    # 섹션 제목 패턴 정의 (더 유연하게 확장)
    section_patterns = {
        1: [r'섹션\s*1', r'매출\s*분석', r'Revenue'],
        2: [r'섹션\s*2', r'유입\s*채널', r'Channel'],
        3: [r'섹션\s*3', r'고객\s*여정', r'Acquisition'],
        4: [r'섹션\s*4', r'베스트\s*상품', r'Best\s*Sellers'],
        5: [r'섹션\s*5', r'시장\s*트렌드', r'Market'],
        6: [r'섹션\s*6', r'매체\s*성과', r'Creative'],
        7: [r'섹션\s*7', r'시장\s*비교', r'Gap\s*Analysis'],
        8: [r'섹션\s*8', r'목표\s*설정', r'Outlook'],
        9: [r'섹션\s*9', r'액션\s*플랜', r'Action\s*Plan']
    }

    # 1. 텍스트가 비어있는지 확인
    if not full_text:
        return ""

    # 2. 타겟 섹션 패턴 가져오기
    patterns = section_patterns.get(target_section, [])
    
    # 3. 제목이 있는지 검사하고 제거 (첫 줄 위주로 확인)
    lines = full_text.split('\n')
    if not lines: return full_text.strip()

    first_line = lines[0].strip()
    
    # 일반적인 마크다운 헤더 제거 (#, ##, ###)
    clean_first_line = re.sub(r'^#+\s*', '', first_line)
    
    is_header = False
    
    # "섹션 N" 또는 "숫자." 패턴 확인
    # 예: "[섹션 1]", "1. 매출 분석", "**섹션 1**"
    common_header_regex = [
        rf'\[?섹션\s*{target_section}\]?',  # [섹션 1], 섹션 1
        rf'^{target_section}\.\s+',        # 1. (내용)
        rf'^{target_section}\)\s+',        # 1) (내용)
    ]
    
    # 커스텀 패턴 확인
    for pat in patterns:
        common_header_regex.append(pat)

    # 첫 줄이 헤더인지 정규식으로 확인
    for regex in common_header_regex:
        if re.search(regex, clean_first_line, re.IGNORECASE):
            is_header = True
            break
            
    # 헤더가 발견되면 첫 줄 제거, 아니면 전체 반환
    if is_header:
        # 두 번째 줄이 구분선(---)이면 그것도 제거
        if len(lines) > 1 and re.match(r'^[\s\-=_]+$', lines[1]):
            return "\n".join(lines[2:]).strip()
        return "\n".join(lines[1:]).strip()
    else:
        # 제목 패턴을 못 찾았으면, AI가 바로 본문을 쓴 것으로 간주하고 전체 반환
        # (이건 에러가 아님)
        print(f"ℹ️ [INFO] 섹션 {target_section} 제목 패턴을 찾지 못했습니다. 제목 없이 본문 바로 사용합니다.", file=sys.stderr)
        return full_text.strip()


def extract_json_from_section(text: str) -> Optional[Dict]:
    """텍스트에서 ```json ... ``` 블록을 찾아 파싱하여 반환 (섹션 7용)"""
    try:
        match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except Exception:
        pass
    return None


def parse_section_9_cards(text: str) -> List[Dict]:
    """섹션 9 텍스트를 ### 기준으로 분리하여 카드 리스트로 변환"""
    cards = []
    # ### 로 시작하는 구간들 분리
    parts = re.split(r'(^|\n)###\s+', text)
    for part in parts:
        part = part.strip()
        if not part or len(part) < 10: continue # 너무 짧거나 빈 구간 제외
        
        # 첫 줄을 제목, 나머지를 내용으로 분리
        lines = part.split('\n', 1)
        title = lines[0].strip()
        content = lines[1].strip() if len(lines) > 1 else ""
        
        cards.append({"title": title, "content": content})
    return cards


# ============================================
# 메인 AI 분석 함수
# ============================================

def generate_ai_analysis(
    snapshot_data: Dict,
    system_prompt: Optional[str] = None,
    system_prompt_file: Optional[str] = None,
    sections: Optional[List[int]] = None,
    api_key: Optional[str] = None,
    enable_prompt_logging: bool = True
) -> Dict:
    """
    스냅샷 데이터를 AI에게 분석시키고 결과를 signals 필드에 추가
    섹션별 개별 API 호출 방식으로 정확도 향상
    
    Args:
        snapshot_data: 스냅샷 JSON 데이터 (report_meta, facts, signals 포함)
        system_prompt: System Prompt 문자열 (직접 제공)
        system_prompt_file: System Prompt 파일 경로
        sections: 분석할 섹션 번호 리스트 (None이면 1-9 모두)
        api_key: Gemini API 키 (None이면 환경변수에서 로드)
        enable_prompt_logging: 프롬프트 로깅 활성화 여부
    
    Returns:
        signals 필드에 AI 분석 텍스트가 추가된 snapshot_data
    """
    # google-genai 패키지 확인
    if genai is None or types is None:
        raise ImportError("google-genai 패키지가 설치되지 않았습니다. 'pip install google-genai'로 설치해주세요.")
    
    # API 키 확인
    api_key = api_key or GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았거나 api_key 파라미터가 필요합니다.")
    
    # Google Gen AI SDK (v1.0+) Client 초기화
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        raise ImportError(f"google-genai 초기화 실패: {e}")
    
    # System Prompt 로드
    if system_prompt:
        system_prompt_text = system_prompt
    else:
        system_prompt_file = system_prompt_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "system_prompt_v44.txt"
        )
        system_prompt_text = load_system_prompt(system_prompt_file)
    
    # signals 초기화 (없으면 생성)
    if "signals" not in snapshot_data:
        snapshot_data["signals"] = {}
    
    signals = snapshot_data["signals"]
    
    # 분석할 섹션 리스트 (기본값: 1-9)
    if sections is None:
        sections = list(range(1, 10))
    
    # 각 섹션별 개별 API 호출로 분석 수행
    for section_num in sections:
        section_key = f"section_{section_num}_analysis"
        
        try:
            print(f"🤖 [INFO] 섹션 {section_num} AI 분석 시작...", file=sys.stderr)
            
            # 섹션별 프롬프트 생성
            section_prompt = build_section_prompt(section_num, snapshot_data)
            
            # 데이터 존재 여부 확인 및 로깅
            facts = safe_get_dict(snapshot_data, "facts", default={})
            print(f"📊 [INFO] 섹션 {section_num} 데이터 확인:", file=sys.stderr)
            if section_num == 1:
                has_data = bool(safe_get_dict(facts, "mall_sales", "this", default={}))
                print(f"   - mall_sales.this: {'✅ 있음' if has_data else '❌ 없음'}", file=sys.stderr)
            elif section_num == 2:
                has_data = bool(safe_get_dict(facts, "ga4_traffic", "this", default={}))
                print(f"   - ga4_traffic.this: {'✅ 있음' if has_data else '❌ 없음'}", file=sys.stderr)
            elif section_num == 3:
                has_data = bool(safe_get_dict(facts, "ga4_traffic", "this", "totals", default={}))
                print(f"   - ga4_traffic.this.totals: {'✅ 있음' if has_data else '❌ 없음'}", file=sys.stderr)
            elif section_num == 4:
                has_data = bool(safe_get_list(facts, "products", "this", "rolling", "d30", "top_products_by_sales", default=[]))
                print(f"   - products.this.rolling.d30.top_products_by_sales: {'✅ 있음' if has_data else '❌ 없음'}", file=sys.stderr)
            elif section_num == 5:
                has_data = bool(safe_get_list(facts, "29cm_best", "items", default=[]))
                print(f"   - 29cm_best.items: {'✅ 있음' if has_data else '❌ 없음'}", file=sys.stderr)
            elif section_num == 6:
                has_data = bool(safe_get_dict(facts, "meta_ads_goals", "this", default={}))
                print(f"   - meta_ads_goals.this: {'✅ 있음' if has_data else '❌ 없음'}", file=sys.stderr)
            elif section_num == 7:
                has_data = bool(safe_get_list(facts, "29cm_best", "items", default=[]))
                print(f"   - 29cm_best.items: {'✅ 있음' if has_data else '❌ 없음'}", file=sys.stderr)
            elif section_num == 8:
                has_data = bool(safe_get_dict(facts, "forecast_next_month", default={}))
                print(f"   - forecast_next_month: {'✅ 있음' if has_data else '❌ 없음'}", file=sys.stderr)
            elif section_num == 9:
                has_data = True  # 섹션 9는 종합 데이터이므로 항상 있음
                print(f"   - 종합 데이터: ✅ 있음", file=sys.stderr)
            
            # 전체 프롬프트 구성
            full_prompt = f"{system_prompt_text}\n\n{section_prompt}"
            
            # 프롬프트 로깅
            if enable_prompt_logging:
                log_prompt_to_file(section_num, full_prompt)
            
            # Google Gen AI SDK (v1.0+) API 호출
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=8192  # 답변이 중간에 잘리지 않도록 토큰 한도 증량
                )
            )
            
            # 응답 텍스트 추출
            raw_analysis_text = response.text.strip()
            
            # 해당 섹션의 내용만 추출 (다른 섹션 언급 제거)
            extracted_text = extract_section_content(raw_analysis_text, section_num)
            
            # 구분선 제거 (---, === 등)
            extracted_text = re.sub(r'^---+$', '', extracted_text, flags=re.MULTILINE)
            extracted_text = re.sub(r'^===+$', '', extracted_text, flags=re.MULTILINE)
            extracted_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', extracted_text)  # 연속된 빈 줄 정리
            extracted_text = extracted_text.strip()
            
            # 1000자 초과 시 WARN 로그만 남기고 그대로 사용
            if len(extracted_text) > 1000:
                print(f"⚠️ [WARN] 섹션 {section_num} 응답이 1000자 초과 ({len(extracted_text)}자). 그대로 사용합니다.", file=sys.stderr)
            
            analysis_text = extracted_text
            
            # 원본과 추출된 텍스트 길이 비교 로그
            if len(analysis_text) < len(raw_analysis_text):
                reduction_pct = (1 - len(analysis_text) / len(raw_analysis_text)) * 100
                print(f"📝 [INFO] 섹션 {section_num} 내용 추출: {len(raw_analysis_text)}자 → {len(analysis_text)}자 ({reduction_pct:.1f}% 감소)", file=sys.stderr)
            
            # 섹션 7: JSON 추출 및 별도 저장
            if section_num == 7:
                json_data = extract_json_from_section(analysis_text)
                if json_data:
                    signals["section_7_data"] = json_data
                    print(f"✅ [INFO] 섹션 7 JSON 비교표 추출 완료", file=sys.stderr)
            
            # 섹션 9: 카드 파싱 및 별도 저장
            if section_num == 9:
                cards = parse_section_9_cards(analysis_text)
                if cards:
                    signals["section_9_cards"] = cards
                    print(f"✅ [INFO] 섹션 9 카드 파싱 완료: {len(cards)}개 카드", file=sys.stderr)
            
            # signals에 저장
            signals[section_key] = analysis_text
            
            print(f"✅ [SUCCESS] 섹션 {section_num} AI 분석 완료 ({len(analysis_text)}자)", file=sys.stderr)
            
        except Exception as e:
            error_msg = f"섹션 {section_num} AI 분석 실패: {str(e)}"
            print(f"❌ [ERROR] {error_msg}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            
            # 에러 발생 시 빈 문자열 또는 에러 메시지 저장
            signals[section_key] = f"[AI 분석 오류: {error_msg}]"
    
    # signals 업데이트
    snapshot_data["signals"] = signals
    
    return snapshot_data


def generate_ai_analysis_from_file(
    snapshot_file: str,
    output_file: Optional[str] = None,
    system_prompt_file: Optional[str] = None,
    sections: Optional[List[int]] = None
) -> Dict:
    """
    스냅샷 JSON 파일에서 읽어서 AI 분석 후 저장 (GCS 지원)
    
    Args:
        snapshot_file: 입력 스냅샷 JSON 파일 경로 (로컬 파일 또는 gs:// 경로)
        output_file: 출력 파일 경로 (None이면 입력 파일에 덮어쓰기, 로컬 파일 또는 gs:// 경로)
        system_prompt_file: System Prompt 파일 경로
        sections: 분석할 섹션 번호 리스트
    
    Returns:
        AI 분석이 추가된 snapshot_data
    """
    # 입력 파일 읽기 (GCS 또는 로컬)
    if snapshot_file.startswith("gs://"):
        print(f"📥 [INFO] GCS에서 파일 로드 중: {snapshot_file}", file=sys.stderr)
        snapshot_data = load_from_gcs(snapshot_file)
    else:
        print(f"📥 [INFO] 로컬 파일 로드 중: {snapshot_file}", file=sys.stderr)
        with open(snapshot_file, 'r', encoding='utf-8') as f:
            snapshot_data = json.load(f)
    
    # AI 분석 수행
    snapshot_data = generate_ai_analysis(
        snapshot_data,
        system_prompt_file=system_prompt_file,
        sections=sections
    )
    
    # 결과 저장 (출력 경로 미지정 시 입력 파일 경로에 덮어쓰기)
    output_path = output_file or snapshot_file
    
    if output_path.startswith("gs://"):
        print(f"📤 [INFO] GCS에 파일 업로드 중: {output_path}", file=sys.stderr)
        upload_to_gcs(snapshot_data, output_path)
    else:
        print(f"📤 [INFO] 로컬 파일 저장 중: {output_path}", file=sys.stderr)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2, sort_keys=True)
    
    print(f"✅ [SUCCESS] AI 분석 결과 저장 완료: {output_path}", file=sys.stderr)
    
    return snapshot_data


if __name__ == "__main__":
    # CLI 사용 예시
    if len(sys.argv) < 2:
        print("Usage: python3 ai_analyst.py <snapshot_file> [output_file] [system_prompt_file]")
        print("  snapshot_file: 입력 스냅샷 JSON 파일 (로컬 파일 또는 gs:// 경로)")
        print("  output_file: 출력 파일 (선택사항, 기본값: 입력 파일에 덮어쓰기, 로컬 파일 또는 gs:// 경로)")
        print("  system_prompt_file: System Prompt 파일 (선택사항, 미지정 시 자동으로 system_prompt_v44.txt 검색)")
        print("")
        print("예시:")
        print("  python3 ai_analyst.py snapshot.json")
        print("  python3 ai_analyst.py gs://bucket/path/snapshot.json.gz")
        print("  python3 ai_analyst.py gs://bucket/path/snapshot.json.gz gs://bucket/path/output.json.gz")
        sys.exit(1)
    
    snapshot_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    system_prompt_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    # System Prompt 파일이 지정되지 않았을 때 자동으로 찾기
    if system_prompt_file is None:
        # 스크립트와 같은 폴더에 있는 system_prompt_v44.txt 확인
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_prompt_file = os.path.join(script_dir, "system_prompt_v44.txt")
        
        if os.path.exists(default_prompt_file):
            system_prompt_file = default_prompt_file
            print(f"📄 [INFO] System Prompt 자동 로드: {system_prompt_file}", file=sys.stderr)
        else:
            print(f"⚠️ [WARN] System Prompt 파일을 찾을 수 없습니다: {default_prompt_file}", file=sys.stderr)
            print(f"   기본 템플릿을 사용합니다.", file=sys.stderr)
    
    generate_ai_analysis_from_file(
        snapshot_file,
        output_file=output_file,
        system_prompt_file=system_prompt_file
    )
