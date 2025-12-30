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
    
    # 다음 달 계산 (예: "2025-12" -> "2026-01")
    try:
        from datetime import datetime
        if report_month and len(report_month) >= 7:  # "2025-12" 형식
            year, month = map(int, report_month.split("-"))
            if month == 12:
                next_month = f"{year + 1}-01"
            else:
                next_month = f"{year}-{month + 1:02d}"
        else:
            next_month = "다음 달"
    except:
        next_month = "다음 달"
    
    # 섹션별 데이터 준비
    # 1. 이벤트 데이터 구조 명확히 파싱 (중첩 구조 해제)
    raw_events = safe_get(facts, "events", default={})
    # 만약 {'events': [...]} 형태의 딕셔너리라면 내부 리스트만 추출
    if isinstance(raw_events, dict) and "events" in raw_events:
        marketing_calendar = safe_get_list(raw_events, "events", default=[])
    elif isinstance(raw_events, list):
        marketing_calendar = raw_events
    else:
        marketing_calendar = []
    
    section_data_map = {
        1: {
            "mall_sales_this": safe_get_dict(facts, "mall_sales", "this", default={}),
            "mall_sales_prev": safe_get_dict(facts, "mall_sales", "prev", default={}),
            "comparisons": safe_get_dict(facts, "comparisons", "mall_sales", default={}),
            "daily_this": safe_get_list(facts, "mall_sales", "daily_this", default=[]),
            "marketing_calendar": marketing_calendar,
        },
        2: {
            "ga4_traffic_this": safe_get_dict(facts, "ga4_traffic", "this", default={}),
            "top_sources": safe_get_list(facts, "ga4_traffic", "this", "top_sources", default=[]),
        },
        3: {
            "funnel_data": {
                "ga4_totals": safe_get_dict(facts, "ga4_traffic", "this", "totals", default={}),
                "mall_sales_this": safe_get_dict(facts, "mall_sales", "this", default={}),
            },
        },
        4: {
            "top_products": safe_get_list(facts, "products", "this", "rolling", "d30", "top_products_by_sales", default=[])[:5],
        },
        # 섹션 4 디버깅: 조회수 데이터 확인
        # _debug_section4: 섹션 4 데이터 로딩 시 조회수(product_views) 데이터 존재 여부 확인
        # 조회수 데이터는 GA4에서 가져와야 하며, bq_monthly_snapshot.py에서 병합되어야 함
        5: {
            "market_reviews": safe_get_list(facts, "29cm_best", "items", default=[])[:10],
        },
        6: {
            "meta_ads_goals_this": safe_get_dict(facts, "meta_ads_goals", "this", default={}),
            "top_ads": safe_get_dict(facts, "meta_ads_goals", "this", "top_ads", default={}),
        },
        7: {
            "section_5_analysis": safe_get(snapshot_data, "signals", "section_5_analysis", default=""),
            "top_products": safe_get_list(facts, "products", "this", "rolling", "d30", "top_products_by_sales", default=[])[:10],
        },
        8: {
            "mall_sales_this": safe_get_dict(facts, "mall_sales", "this", default={}),
            "forecast_next_month": safe_get_dict(facts, "forecast_next_month", default={}),
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

⚠️ **중요: 이 섹션 1만 분석하고 답변하세요.**

데이터:
- 이번 달 매출: {json.dumps(section_data.get('mall_sales_this', {}), ensure_ascii=False, indent=2)}
- 전월 매출: {json.dumps(section_data.get('mall_sales_prev', {}), ensure_ascii=False, indent=2)}
- 비교 데이터: {json.dumps(section_data.get('comparisons', {}), ensure_ascii=False, indent=2)}
- 일별 매출: {json.dumps(section_data.get('daily_this', [])[:10], ensure_ascii=False, indent=2)}
- 📅 마케팅_프로모션_일정: {json.dumps(section_data.get('marketing_calendar', []), ensure_ascii=False, indent=2)}

분석 요청:
데이터를 단순 나열하지 말고, **아래 4가지 항목으로 구분하여 인사이트를 포함한 문장**으로 작성하십시오.

⚠️ **출력 형식 (Markdown 필수)**:
* **매출 실적 (Growth):** [전월/전년 대비 증감 수치와 성장세 진단]
* **효율성 진단 (Efficiency):** [주문 건수와 객단가(AOV) 관계 분석]
* **고객 유입 (Acquisition):** [신규/재구매/취소 건수 기반 진단]
* **📊 이벤트 효과 (Event Impact):**
  - 위 '마케팅_프로모션_일정'을 참고하여 아래 기준으로 분석하십시오.
  1. **🚀 부스터(Booster) 평가:** `memo`가 **[자사몰]**인 행사 기간, 비행사 기간 대비 매출이 **유의미하게 상승**했는지 분석. (성공적인 기폭제였는지 평가)
  2. **🛡️ 방어(Defense) 평가:** `memo`가 **[29cm] 등 타 플랫폼**인 기간, 자사몰 매출이 **급감하지 않고 유지**되었는지 분석. (매출이 빠졌다면 '방어 실패/이탈', 유지했다면 '방어 성공'으로 평가)

- **금액(KRW)이나 건수**는 **굵게** 표시.
- 🎨 **퍼센트 표기법:** 숫자는 강조하되 **% 기호는 볼드 바깥**에 두십시오. (예: **92.5**% (O))
- 각 항목은 불렛 포인트(`*`)와 굵은 제목으로 시작.
""",
        2: f"""
[섹션 2: 주요 유입 채널]
{company_name}의 {report_month} 유입 채널 데이터를 분석해주세요.

⚠️ **중요: 이 섹션 2만 분석하고 답변하세요.**

데이터:
- GA4 트래픽: {json.dumps(section_data.get('ga4_traffic_this', {}), ensure_ascii=False, indent=2)}
- 상위 유입 소스: {json.dumps(section_data.get('top_sources', []), ensure_ascii=False, indent=2)}

분석 요청:
데이터를 단순 나열하지 말고, **아래 4가지 항목으로 구분하여 인사이트를 포함한 문장**으로 작성하십시오. 이모지(아이콘)는 사용하지 마십시오.

⚠️ **출력 형식 (Markdown 필수)**:
* **유입 성과 (Volume):** [최다 유입 채널 및 브랜드 직접 유입 비중 평가]
* **효율성 진단 (Efficiency):** [이탈률이 낮은 우수 채널 평가]
* **개선 필요 영역 (Weakness):** [유입은 많으나 이탈률이 높은 채널 진단]
* **전략 제안 (Action Plan):** [핵심 채널 개선을 위한 액션 플랜]

- 주요 수치는 **굵게** 표시 (예: **49.04**%)
- 퍼센트(%) 수치는 숫자만 굵게, %는 바깥에 둡니다 (예: **92.5**%)
- 각 항목은 불렛 포인트(`*`)와 굵은 제목으로 시작할 것.
""",
        3: f"""
[섹션 3: 고객 여정 (Funnel)]
{company_name}의 {report_month} 고객 행동 데이터를 분석해주세요.

⚠️ **중요: 이 섹션 3만 분석하고 답변하세요.**

데이터:
- 퍼널 데이터: {json.dumps(section_data.get('funnel_data', {}), ensure_ascii=False, indent=2)}

분석 요청:
**퍼널 단계별 전환율**을 중심으로 병목 구간을 찾고 개선책을 제안하십시오.

⚠️ **출력 형식 (Markdown 필수)**:
### 1. 퍼널 단계별 진단
* **유입 → 장바구니:** [전환율 수치와 분석]
* **장바구니 → 구매:** [전환율 수치와 분석]
* **전체 구매 전환율:** [수치와 평가]

### 2. 핵심 문제점 (Pain Point)
* [병목 구간 지적 및 원인 추론]

### 3. 개선 제안
* [구체적인 액션 아이템]

- 주요 수치는 **굵게** 표시 (예: **0.94**%)
- 퍼센트(%) 수치는 숫자만 굵게, %는 바깥에 둡니다 (예: **92.5**%)
- 소제목은 `###` 헤더 사용.
""",
        4: f"""
[섹션 4: 자사몰 베스트 상품 분석]
{company_name}의 {report_month} 상품 판매 데이터를 분석해주세요.

⚠️ **중요: 이 섹션 4만 분석하고 답변하세요.**

데이터:
- 베스트 상품: {json.dumps(section_data.get('top_products', []), ensure_ascii=False, indent=2)}

분석 요청:
데이터를 바탕으로 매출 리딩 상품과 판매량 리딩 상품을 구분하고, 객단가 상승을 위한 구체적인 번들링 전략을 제안하십시오.
(만약 `product_views` 데이터가 0이거나 없다면, '조회수' 언급을 생략하고 **'판매량'과 '매출액'** 기준으로만 분석하십시오.)

⚠️ **출력 형식 (Markdown 필수 - 줄글 금지)**:

### 🏆 매출 리딩 상품 (Revenue Leader)
* **[상품명]:** 압도적인 매출(**[금액]원**)을 기록하며 성장을 견인했습니다. (성과 요약)

### 📦 판매량 및 효율 진단 (Volume vs Efficiency)
* **[상품명]:** **[판매량]개**로 최다 판매를 기록했으나, 상대적으로 낮은 단가(**[객단가]원**)로 인해 매출 기여도는 제한적입니다.
* (조회수 데이터가 있다면 고효율/저효율 상품 추가 언급)

### 💡 포트폴리오 전략 (Action Plan)
* **번들링 제안:** 매출 1위인 **[상품 A]**와 판매량 1위인 **[상품 B]**를 연계하여 객단가(AOV) 상승을 유도하십시오.
* **수익성 점검:** 프로모션 실행 전, 대상 상품의 **재고 수량**과 **목표 이익률** 시뮬레이션을 반드시 선행하십시오.

- 상품명은 `[ ]` 없이 굵게 표시하지 말고 텍스트로만 표기.
- **금액**과 **수량** 수치는 **굵게** 표시.
- 🛑 **주의: 퍼센트(%) 기호는 볼드 바깥에 두십시오.**
""",
        5: f"""
[섹션 5: 시장 트렌드 (29CM)]
29CM 베스트 상품 리뷰 데이터를 바탕으로 시장 트렌드를 분석해주세요.

⚠️ **중요: 이 섹션 5만 분석하고 답변하세요.**

데이터:
- 29CM 리뷰 데이터: {json.dumps(section_data.get('market_reviews', []), ensure_ascii=False, indent=2)}

분석 요청:
경쟁사 상품의 **긍정적 리뷰**와 **부정적 리뷰**를 명확히 구분하여 분석하십시오.

⚠️ **출력 형식 (Markdown 필수)**:
### 시장 인기 트렌드
* **주요 아이템:** [카테고리 및 스타일 트렌드]
* **선호 키워드:** [소비자가 반응하는 핵심 키워드]

### 긍정적 리뷰 참고
* **[업체명 색상] 상품명:** [구체적 긍정 내용]
* **[업체명 색상] 상품명:** [구체적 긍정 내용]

### 부정적 리뷰 참고
* **[업체명 색상] 상품명:** [구체적 불만 내용]
* **[업체명 색상] 상품명:** [구체적 불만 내용]

### 기회 요인 (Opportunity)
* [경쟁사 약점을 공략할 틈새시장 제안]

- 브랜드/상품명은 **업체명에 색상을 포함**하여 표기 (예: **오떼뜨(브랜드명) 108파운드 Molly Reversible Shearling Coat_Dark brown**)
- 업체명과 상품명을 구분할 수 있도록 명확히 표기.
""",
        6: f"""
[섹션 6: 매체 성과 및 효율 진단]
{company_name}의 {report_month} 광고 매체 데이터를 분석해주세요.

⚠️ **중요: 이 섹션 6만 분석하고 답변하세요.**

데이터:
- Meta Ads 성과: {json.dumps(section_data.get('meta_ads_goals_this', {}), ensure_ascii=False, indent=2)}
- 상위 광고: {json.dumps(section_data.get('top_ads', {}), ensure_ascii=False, indent=2)}

분석 요청:
광고주가 흐름을 이해할 수 있도록, **수치 단순 나열을 넘어 '원인과 결과'를 해석**하여 서술하십시오. (Ad ID 표기 금지)

⚠️ **출력 형식 (Markdown 필수)**:
* **성과 및 역할 진단:** [전환 캠페인의 매출 기여도(ROAS) 평가] 및 [유입 캠페인의 모수 확보 효율성(CTR, CPC)에 대한 긍정적 평가와 역할 정의]
* **소재 형식별 승리 요인:** [구매 유도에 카탈로그가 유리했던 이유] vs [유입 유도에 영상이 효과적이었던 이유]를 비교 분석.
* **향후 운영 전략:** [소재별 예산 재배치 제안] 및 [유입된 트래픽을 전환으로 연결할 구체적 리타겟팅 시나리오]

- 주요 수치는 **굵게** 표시.
- 통화 단위는 'KRW' 대신 한글 **'원'**으로 표기하세요 (예: **1,000,000원**).
- 퍼센트(%) 수치는 숫자만 굵게, %는 바깥에 둡니다 (예: **92.5**%)
- 각 항목은 2~3문장의 깊이 있는 줄글로 작성.
- Ad ID (예: 12023...) 절대 표기 금지.
""",
        7: f"""
[섹션 7: 자사몰 vs 시장 비교]
자사몰 데이터와 29CM 시장 데이터를 비교 분석해주세요.

⚠️ **중요: 이 섹션 7만 분석하고 답변하세요.**

데이터:
- 시장 분석(섹션5 결과): {json.dumps(section_data.get('section_5_analysis', ''), ensure_ascii=False, indent=2)}
- 자사몰 상품(섹션4 결과): {json.dumps(section_data.get('top_products', []), ensure_ascii=False, indent=2)}

분석 요청:
시장과 자사를 비교 분석하되, **UI 테이블 렌더링을 위해 키(Key) 이름과 글자 수를 엄격하게 지키십시오.**

⚠️ **출력 형식 (반드시 JSON)**:
- `table_data`의 값은 **반드시 20자 이내의 단답형 키워드**로 압축하십시오. (서술형 문장 금지)
- `card_summary`는 구체적인 전략을 포함하여 서술형으로 작성하십시오.
- **키 이름(Key)에 언더바(_)를 쓰지 말고 공백을 사용하십시오.**

```json
{{
  "table_data": {{
    "가격대": {{ 
      "market": "중저가~고가 (넓은 범위)", 
      "company": "중가 (5~15만원대)" 
    }},
    "주력 아이템": {{ 
      "market": "퍼 코트, 플리스, 니트", 
      "company": "스커트 팬츠, 후드티" 
    }},
    "타겟 고객층": {{ 
      "market": "보온성/트렌드 중시", 
      "company": "실용성/데일리룩 중시" 
    }},
    "핵심 소재": {{ 
      "market": "페이크 퍼, 울, 텐셀", 
      "company": "코튼 혼방, 기능성 소재" 
    }}
  }},
  "card_summary": {{
    "market_analysis": "**시장 트렌드 요약:**\\n(겨울 아우터 위주의 시장 흐름과 '털 빠짐', '무거움' 등 소비자의 구체적인 불만 사항(Pain Point)을 요약)",
    "company_analysis": "**자사 포지셔닝:**\\n(자사몰은 시장의 '털 빠짐' 이슈를 해결하는 '관리 용이성'과 '합리적 가격'을 내세워 2030 실용주의 고객을 타겟팅합니다.)"
  }}
}}
```
""",
        8: f"""
[섹션 8: 다음 달 목표 제안]
과거 데이터를 바탕으로 다음 달({next_month}) 매출 목표를 제안해주세요.

⚠️ **중요: 이 섹션 8만 분석하고 답변하세요.**

데이터:
- 예측 데이터: {json.dumps(section_data.get('forecast_next_month', {}), ensure_ascii=False, indent=2)}

분석 요청:
기계적 예측치와 도전적 목표치를 제시하고, 그 근거를 설명하십시오.

⚠️ **출력 형식 (Markdown 필수)**:
### {next_month} 매출 목표 제안
* **보수적 목표 (기계적 예측):** **[금액]원** (전년 대비 [증감률]%)
* **도전적 목표 (Action Plan):** **[금액]원** (기계적 예측 대비 [배수]배)

### 목표 설정 근거
* [긍정적 요인]: [목표 상향의 근거]
* [부정적 요인]: [리스크 요인]
* [대응 전략]: [목표 달성을 위한 핵심 전략]

- 금액은 3자리 콤마(,) 포함하여 표기.
""",
        9: f"""
[섹션 9: 종합 제안 (Action Cards)]
앞선 모든 분석(섹션 1~8)을 종합하여, 다음 달 실행할 구체적인 전략 3가지를 제안해주세요.

⚠️ **중요: 이 섹션 9만 분석하고 답변하세요.**

데이터:
- 섹션 1~8의 주요 분석 내용 참고.

분석 요청:
마케팅, 상품 기획, 프로모션 관점에서 **구체적인 상품명과 데이터**에 기반한 전략을 제안하십시오.

⚠️ **출력 형식 (반드시 JSON)**:
- 결과는 반드시 **3개의 객체를 가진 JSON 배열(Array)**이어야 합니다.

**1. 제목(`title`) 규칙:**
- 🛑 **특수문자(?, ?, - 등) 절대 금지.**
- 오직 **"이모지 1개 + 공백 + 한글 제목"** 형태로만 작성하십시오.
  - (O) 💡 겨울 아우터 번들링 전략
  - (X) 💡 ? **겨울 아우터** ?

**2. 본문(`content`) 규칙:**
- **가독성:** 한 덩어리의 줄글 대신, **줄바꿈(`\\n`)과 불렛 포인트(`•`)**를 사용하여 핵심을 나누십시오.
- **용어 정제:** `is_declining`, `stock` 같은 영어 변수명을 절대 쓰지 말고 **'매출 감소 추세', '재고'** 등 한국어로 자연스럽게 표현하십시오.
- **마크다운:** 단어를 강조할 때 **작은따옴표(')를 쓰지 마십시오.** 그냥 글자만 굵게 처리하십시오.
  - (O) **스커트 팬츠**와 **후드티**를...
  - (X) **'스커트 팬츠'**와... (따옴표 금지)

🛑 **주의: 아래는 형식을 보여주기 위한 '예시'입니다. 내용은 반드시 실제 데이터를 분석하여 새로 작성하십시오.**

```json
[
  {{
    "title": "💡 윈터 스타일링 세트 제안",
    "content": "섹션 4 데이터를 분석한 결과, 매출 1위인 **스커트 팬츠**와 조회수가 높은 **캐시미어 니트**의 시너지가 기대됩니다.\\n\\n• **전략:** 두 상품을 묶은 'Winter Style Setup' 세트 구성\\n• **기대 효과:** 객단가(**AOV**) 상승 및 코트 상품의 구매 전환 유도"
  }},
  {{
    "title": "🎯 품질 불만 해소 캠페인",
    "content": "경쟁사 리뷰에서 **털 빠짐**과 **무거운 착용감**에 대한 불만이 다수 확인되었습니다.\\n\\n• **전략:** 자사 제품의 '가벼움'과 '털 날림 없음'을 강조하는 콘텐츠 배포\\n• **타겟:** 품질에 민감한 2030 스마트 컨슈머 집중 공략"
  }},
  {{
    "title": "📦 시즌 오프 재고 소진",
    "content": "매출 감소 추세(**Declining**)를 보이는 겨울 니트류의 재고 소진이 시급합니다.\\n\\n• **전략:** 설 연휴 배송 마감 이슈를 활용한 'Last Chance' 타임 세일\\n• **체크:** 실행 전 대상 상품의 **재고 수량**과 **목표 이익률** 시뮬레이션 필수"
  }}
]
```
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


def split_section_7_analysis(text: str) -> List[str]:
    """
    섹션 7 분석 텍스트를 두 부분으로 분리 (29CM 시장 분석 / 자사몰 분석)
    
    Args:
        text: 섹션 7 분석 텍스트
    
    Returns:
        [29CM 시장 분석, 자사몰 분석] 리스트
    """
    if not text or not text.strip():
        return ["", ""]
    
    # JSON 블록 제거 (분리 전에 제거)
    text_without_json = re.sub(r'```json\s*[\s\S]*?\s*```', '', text, flags=re.DOTALL)
    text_without_json = text_without_json.strip()
    
    # 분리 키워드 패턴 (여러 패턴 시도)
    split_patterns = [
        r'\n\n반면,\s*자사몰은',
        r'\n\n자사몰은',
        r'\n반면,\s*자사몰은',
        r'\n자사몰은',
        r'반면,\s*자사몰은',
        r'자사몰은',
    ]
    
    for pattern in split_patterns:
        match = re.search(pattern, text_without_json, re.IGNORECASE)
        if match:
            split_pos = match.start()
            part1 = text_without_json[:split_pos].strip()
            part2 = text_without_json[split_pos:].strip()
            
            # "반면, 자사몰은" 같은 키워드 제거
            part2 = re.sub(r'^(반면,\s*)?자사몰은\s*', '', part2, flags=re.IGNORECASE).strip()
            
            if part1 and part2:
                return [part1, part2]
    
    # 분리 실패 시 중간 지점에서 분리 시도
    lines = text_without_json.split('\n')
    if len(lines) > 3:
        mid_point = len(lines) // 2
        part1 = '\n'.join(lines[:mid_point]).strip()
        part2 = '\n'.join(lines[mid_point:]).strip()
        
        # "반면" 또는 "자사몰" 키워드가 있는 줄 찾기
        for i, line in enumerate(lines):
            if re.search(r'반면|자사몰', line, re.IGNORECASE):
                if i > 0:
                    part1 = '\n'.join(lines[:i]).strip()
                    part2 = '\n'.join(lines[i:]).strip()
                    # 키워드 제거
                    part2 = re.sub(r'^(반면,\s*)?자사몰은\s*', '', part2, flags=re.IGNORECASE).strip()
                    if part1 and part2:
                        return [part1, part2]
        
        if part1 and part2:
            return [part1, part2]
    
    # 모든 분리 시도 실패 시 전체를 첫 번째로 반환
    return [text_without_json, ""]


def extract_json_from_section(text: str):
    """텍스트에서 ```json ... ``` 블록을 찾아 파싱하여 반환 (섹션 7, 9용) - Dict 또는 List 반환"""
    try:
        # 방법 1: 정규식으로 JSON 블록 찾기 (개선된 버전)
        # 중괄호 매칭을 더 정확하게 처리하기 위해 여러 시도
        patterns = [
            r'```json\s*(\{[\s\S]*?\})\s*```',  # 객체 패턴
            r'```json\s*(\[[\s\S]*?\])\s*```',  # 배열 패턴
            r'```json\s*(\{.*?\})\s*```',       # 간단한 객체 패턴 (fallback)
            r'```json\s*(\[.*?\])\s*```',      # 간단한 배열 패턴 (fallback)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # JSON 파싱 실패 시 다음 패턴 시도
                    continue
        
        # 방법 2: 정규식으로 찾지 못한 경우, ```json과 ``` 사이의 모든 내용 추출
        json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', text, re.DOTALL)
        if json_block_match:
            json_str = json_block_match.group(1).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
                
    except Exception as e:
        print(f"⚠️ [WARN] JSON 추출 실패: {e}", file=sys.stderr)
    
    return None


def parse_section_9_cards(text: str) -> List[Dict]:
    """섹션 9 텍스트를 JSON 배열 또는 ### 기준으로 분리하여 카드 리스트로 변환"""
    cards = []
    
    if not text or not text.strip():
        return cards
    
    # 먼저 JSON 배열 형식인지 확인
    try:
        json_data = extract_json_from_section(text)
        if json_data and isinstance(json_data, list):
            # JSON 배열인 경우
            for item in json_data:
                if isinstance(item, dict) and "title" in item and "content" in item:
                    cards.append({
                        "title": item["title"],
                        "content": item["content"]
                    })
            if cards:
                print(f"✅ [INFO] 섹션 9 JSON 배열 파싱 완료: {len(cards)}개 카드", file=sys.stderr)
                return cards
    except Exception as e:
        print(f"⚠️ [WARN] 섹션 9 JSON 파싱 실패, ### 방식으로 시도: {e}", file=sys.stderr)
    
    # JSON이 아니면 ### 기준으로 분리 (기존 방식)
    # 정규식: ### 로 시작하는 줄을 찾아서 분리
    parts = re.split(r'\n###\s+', text)
    
    for i, part in enumerate(parts):
        part = part.strip()
        
        # 첫 번째 부분이 ###로 시작하지 않는 경우 (헤더가 없는 경우)
        if i == 0 and not part.startswith('###'):
            # 첫 번째 부분이 헤더가 아니면 건너뛰기
            if not part or len(part) < 10:
                continue
            # 첫 번째 부분이 헤더가 아니지만 내용이 있으면, 제목 없이 내용만 저장
            cards.append({"title": "전략", "content": part})
            continue
        
        # ### 헤더가 있는 경우
        if not part or len(part) < 5:  # 너무 짧거나 빈 구간 제외
            continue
        
        # 첫 줄을 제목, 나머지를 내용으로 분리
        lines = part.split('\n', 1)
        title = lines[0].strip()
        
        # 제목에서 ### 제거 (이미 split으로 분리했지만 혹시 모를 경우 대비)
        title = re.sub(r'^#+\s*', '', title).strip()
        
        # 제목에서 [전략 N] 패턴 제거 (예: "[전략 1]" → "")
        title = re.sub(r'^\[전략\s*\d+\]\s*', '', title).strip()
        
        content = lines[1].strip() if len(lines) > 1 else ""
        
        # 제목과 내용이 모두 있는 경우만 추가
        if title:
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
                top_products = safe_get_list(facts, "products", "this", "rolling", "d30", "top_products_by_sales", default=[])
                has_data = bool(top_products)
                print(f"   - products.this.rolling.d30.top_products_by_sales: {'✅ 있음' if has_data else '❌ 없음'}", file=sys.stderr)
                # 조회수 데이터 확인
                if top_products:
                    products_with_views = [p for p in top_products if isinstance(p, dict) and p.get("product_views", 0) > 0]
                    print(f"   - product_views 데이터가 있는 상품 수: {len(products_with_views)}/{len(top_products)}", file=sys.stderr)
                    if len(products_with_views) == 0:
                        print(f"   ⚠️ [WARN] 조회수(product_views) 데이터가 없습니다. GA4 데이터 병합 로직을 확인하세요.", file=sys.stderr)
                    else:
                        sample_product = top_products[0]
                        print(f"   - 샘플 상품 조회수: {sample_product.get('product_views', 'N/A')}", file=sys.stderr)
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
            
            # 섹션 7: JSON 추출 및 분석 텍스트 분리
            if section_num == 7:
                json_data = extract_json_from_section(analysis_text)
                if json_data and isinstance(json_data, dict):
                    signals["section_7_data"] = json_data
                    print(f"✅ [INFO] 섹션 7 JSON 비교표 추출 완료", file=sys.stderr)
                    
                    # JSON에서 card_summary의 market_analysis와 company_analysis 추출
                    card_summary = json_data.get("card_summary", {})
                    if "market_analysis" in card_summary:
                        signals["section_7_analysis_1"] = card_summary["market_analysis"]
                        print(f"✅ [INFO] 섹션 7 시장 분석 추출 완료", file=sys.stderr)
                    elif "market_analysis" in json_data:  # 하위 호환성
                        signals["section_7_analysis_1"] = json_data["market_analysis"]
                        print(f"✅ [INFO] 섹션 7 시장 분석 추출 완료 (하위 호환)", file=sys.stderr)
                    
                    if "company_analysis" in card_summary:
                        signals["section_7_analysis_2"] = card_summary["company_analysis"]
                        print(f"✅ [INFO] 섹션 7 자사몰 분석 추출 완료", file=sys.stderr)
                    elif "company_analysis" in json_data:  # 하위 호환성
                        signals["section_7_analysis_2"] = json_data["company_analysis"]
                        print(f"✅ [INFO] 섹션 7 자사몰 분석 추출 완료 (하위 호환)", file=sys.stderr)
                else:
                    # JSON 추출 실패 시 기존 방식으로 분리 시도
                    analysis_parts = split_section_7_analysis(analysis_text)
                    if len(analysis_parts) >= 2:
                        signals["section_7_analysis_1"] = analysis_parts[0]  # 29CM 시장 분석
                        signals["section_7_analysis_2"] = analysis_parts[1]  # 자사몰 분석
                        print(f"✅ [INFO] 섹션 7 분석 텍스트 분리 완료 (1: {len(analysis_parts[0])}자, 2: {len(analysis_parts[1])}자)", file=sys.stderr)
                    else:
                        # 분리 실패 시 전체를 첫 번째로 저장
                        signals["section_7_analysis_1"] = analysis_text
                        signals["section_7_analysis_2"] = ""
                        print(f"⚠️ [WARN] 섹션 7 분석 텍스트 분리 실패, 전체를 첫 번째로 저장", file=sys.stderr)
                
                # 기존 section_7_analysis는 제거하지 않고 유지 (하위 호환성)
                signals[section_key] = analysis_text
            
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
