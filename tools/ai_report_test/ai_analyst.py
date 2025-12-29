"""
AI 분석 모듈
- Google Gemini API를 사용하여 월간 리포트 스냅샷 데이터를 분석
- 섹션별 분석 텍스트를 생성하여 signals 필드에 추가
"""

"""
AI 분석 모듈
- Google Gemini API를 사용하여 월간 리포트 스냅샷 데이터를 분석
- 섹션별 분석 텍스트를 생성하여 signals 필드에 추가

사용 예시:
    from tools.ai_report_test.ai_analyst import generate_ai_analysis
    
    # 스냅샷 데이터에 AI 분석 추가
    snapshot_with_analysis = generate_ai_analysis(
        snapshot_data,
        system_prompt_file="tools/ai_report_test/system_prompt_v44.txt"
    )
"""

import os
import sys
import json
import gzip
import traceback
from typing import Dict, Optional, List

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
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")  # 기본 모델 (가성비 및 안정성 최적화)

# System Prompt는 별도 파일에서 로드하거나 함수 파라미터로 받음
# 사용자가 나중에 붙여넣을 예정이므로, 기본 템플릿만 제공
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
        
        # 파일 다운로드 (임시 파일 사용하여 urllib3 버전 호환성 문제 회피)
        import tempfile
        with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
            blob.download_to_filename(tmp_file.name)
            # 파일을 바이너리 모드로 읽기
            with open(tmp_file.name, 'rb') as f:
                file_bytes = f.read()
        
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


def build_section_prompt(section_num: int, snapshot_data: Dict) -> str:
    """
    섹션별 프롬프트 생성
    
    Args:
        section_num: 섹션 번호 (1-9)
        snapshot_data: 스냅샷 JSON 데이터
    
    Returns:
        섹션별 프롬프트 문자열
    """
    facts = snapshot_data.get("facts", {})
    report_meta = snapshot_data.get("report_meta", {})
    company_name = report_meta.get("company_name", "업체")
    report_month = report_meta.get("report_month", "")
    
    section_prompts = {
        1: f"""
[섹션 1: 지난달 매출 분석]
{company_name}의 {report_month} 매출 데이터를 분석해주세요.

데이터:
- 이번 달 매출: {json.dumps(facts.get('mall_sales', {}).get('this', {}), ensure_ascii=False, indent=2)}
- 전월 매출: {json.dumps(facts.get('mall_sales', {}).get('prev', {}), ensure_ascii=False, indent=2)}
- 비교 데이터: {json.dumps(facts.get('comparisons', {}).get('mall_sales', {}), ensure_ascii=False, indent=2)}

분석 요청:
- 매출 증감 요인 분석
- 주요 성과 지표 해석
- 전월 대비 변화 인사이트
""",
        2: f"""
[섹션 2: 주요 유입 채널]
{company_name}의 {report_month} 유입 채널 데이터를 분석해주세요.

데이터:
- GA4 트래픽: {json.dumps(facts.get('ga4_traffic', {}).get('this', {}), ensure_ascii=False, indent=2)}
- 상위 유입 소스: {json.dumps(facts.get('ga4_traffic', {}).get('this', {}).get('top_sources', [])[:5], ensure_ascii=False, indent=2)}

분석 요청:
- 주요 유입 채널 성과 분석
- 채널별 이탈률 및 전환율 해석
- 채널 최적화 제안
""",
        3: f"""
[섹션 3: 고객 방문 및 구매 여정]
{company_name}의 {report_month} 고객 여정 데이터를 분석해주세요.

데이터:
- GA4 퍼널: {json.dumps(facts.get('ga4_traffic', {}).get('this', {}).get('totals', {}), ensure_ascii=False, indent=2)}
- 매출 데이터: {json.dumps(facts.get('mall_sales', {}).get('this', {}), ensure_ascii=False, indent=2)}

분석 요청:
- 유입 → 장바구니 → 구매 전환율 분석
- 여정별 이탈 지점 파악
- 전환율 개선 제안
""",
        4: f"""
[섹션 4: 자사몰 베스트 상품 성과]
{company_name}의 {report_month} 베스트 상품 데이터를 분석해주세요.

데이터:
- 베스트 상품 (매출 기준): {json.dumps(facts.get('products', {}).get('this', {}).get('rolling', {}).get('d30', {}).get('top_products_by_sales', [])[:5], ensure_ascii=False, indent=2)}
- 베스트 상품 (조회 기준): {json.dumps(facts.get('viewitem', {}).get('this', {}).get('top_items_by_view_item', [])[:5], ensure_ascii=False, indent=2)}

분석 요청:
- 베스트 상품 성과 분석
- 매출 vs 조회수 비교 인사이트
- 상품 포트폴리오 개선 제안
""",
        5: f"""
[섹션 5: 시장 트렌드 확인 (29CM)]
{company_name}의 {report_month} 시장 트렌드 데이터를 분석해주세요.

데이터:
- 29CM 베스트 상품: {json.dumps(facts.get('29cm_best', {}).get('items', [])[:10], ensure_ascii=False, indent=2)}

분석 요청:
- 시장 트렌드 분석
- 인기 상품 카테고리/가격대 파악
- 시장 기회 포착
""",
        6: f"""
[섹션 6: 매체 성과 및 효율 진단]
{company_name}의 {report_month} 광고 매체 데이터를 분석해주세요.

데이터:
- Meta Ads 성과: {json.dumps(facts.get('meta_ads_goals', {}).get('this', {}), ensure_ascii=False, indent=2)}
- 상위 광고: {json.dumps(facts.get('meta_ads_goals', {}).get('this', {}).get('top_ads', {}), ensure_ascii=False, indent=2)}

분석 요청:
- 광고 매체 효율 분석
- ROAS/CTR/CVR 해석
- 광고 최적화 제안
""",
        7: f"""
[섹션 7: 시장 트렌드와 자사몰 비교]
{company_name}의 {report_month} 시장 비교 데이터를 분석해주세요.

데이터:
- 29CM 베스트: {json.dumps(facts.get('29cm_best', {}).get('items', [])[:10], ensure_ascii=False, indent=2)}
- 자사몰 상품: {json.dumps(facts.get('products', {}).get('this', {}).get('rolling', {}).get('d30', {}).get('top_products_by_sales', [])[:10], ensure_ascii=False, indent=2)}

분석 요청:
- 시장 vs 자사몰 비교 분석
- 차별화 포인트 파악
- 경쟁력 강화 방안

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

데이터:
- 전망 데이터: {json.dumps(facts.get('forecast_next_month', {}), ensure_ascii=False, indent=2)}
- 작년 동월/익월 매출: {json.dumps(facts.get('forecast_next_month', {}).get('mall_sales', {}), ensure_ascii=False, indent=2)}

분석 요청:
- 다음 달 목표 설정 제안
- 작년 대비 전망 분석
- 시장 전망 및 리스크 요인
""",
        9: f"""
[섹션 9: 데이터 기반 전략 액션 플랜]
{company_name}의 {report_month} 전체 데이터를 종합하여 전략을 제안해주세요.

데이터 요약:
- 매출: {json.dumps(facts.get('mall_sales', {}).get('this', {}), ensure_ascii=False, indent=2)}
- 광고: {json.dumps(facts.get('meta_ads', {}).get('this', {}), ensure_ascii=False, indent=2)}
- 유입: {json.dumps(facts.get('ga4_traffic', {}).get('this', {}).get('totals', {}), ensure_ascii=False, indent=2)}
- 신호: {json.dumps(snapshot_data.get('signals', {}), ensure_ascii=False, indent=2)}

분석 요청:
- 종합 전략 액션 플랜
- 우선순위별 실행 방안
- KPI 및 목표 설정
"""
    }
    
    return section_prompts.get(section_num, "")


def extract_section_content(full_text: str, target_section: int) -> str:
    """
    AI 응답에서 특정 섹션의 내용만 추출 (다른 섹션 언급 제거)
    
    Args:
        full_text: AI가 반환한 전체 텍스트
        target_section: 추출할 섹션 번호 (1-9)
    
    Returns:
        해당 섹션의 내용만 포함한 텍스트
    """
    import re
    
    # 섹션 제목 패턴 정의 (한글/영문 모두 매칭)
    section_patterns = {
        1: [r'\[섹션\s*1\]', r'섹션\s*1', r'지난달\s*매출\s*분석', r'Revenue\s*Analysis'],
        2: [r'\[섹션\s*2\]', r'섹션\s*2', r'주요\s*유입\s*채널', r'Channel\s*Efficiency'],
        3: [r'\[섹션\s*3\]', r'섹션\s*3', r'고객\s*방문\s*및\s*구매\s*여정', r'Acquisition\s*&\s*Conversion'],
        4: [r'\[섹션\s*4\]', r'섹션\s*4', r'자사몰\s*베스트\s*상품\s*성과', r'Best\s*Sellers'],
        5: [r'\[섹션\s*5\]', r'섹션\s*5', r'시장\s*트렌드\s*확인', r'Market\s*Deep\s*Dive'],
        6: [r'\[섹션\s*6\]', r'섹션\s*6', r'매체\s*성과\s*및\s*효율\s*진단', r'Creative\s*Performance'],
        7: [r'\[섹션\s*7\]', r'섹션\s*7', r'시장\s*트렌드와\s*자사몰\s*비교', r'Gap\s*Analysis'],
        8: [r'\[섹션\s*8\]', r'섹션\s*8', r'익월\s*목표\s*설정\s*및\s*시장\s*전망', r'Target\s*&\s*Outlook'],
        9: [r'\[섹션\s*9\]', r'섹션\s*9', r'데이터\s*기반\s*전략\s*액션\s*플랜', r'Action\s*Plan', r'종합\s*전략']
    }
    
    # 타겟 섹션 패턴
    target_patterns = section_patterns.get(target_section, [])
    if not target_patterns:
        # 패턴이 없으면 전체 텍스트 반환
        return full_text
    
    # 타겟 섹션 시작 위치 찾기 (줄 시작 부분에서만 매칭)
    target_start_pos = -1
    for pattern in target_patterns:
        # 줄 시작 부분에서 매칭하도록 ^ 앵커 추가 (MULTILINE 모드)
        multiline_pattern = r'^\s*' + pattern
        match = re.search(multiline_pattern, full_text, re.MULTILINE | re.IGNORECASE)
        if match:
            target_start_pos = match.start()
            break
    
    # 타겟 섹션을 찾지 못하면 전체 텍스트 반환
    if target_start_pos == -1:
        print(f"⚠️ [WARN] 섹션 {target_section} 시작 패턴을 찾을 수 없습니다. 전체 텍스트를 반환합니다.", file=sys.stderr)
        return full_text
    
    # 다음 섹션 시작 위치 찾기 (타겟 섹션 이후)
    next_section_start = len(full_text)
    for section_num in range(1, 10):
        if section_num == target_section:
            continue
        if section_num <= target_section:
            continue  # 이미 지나간 섹션은 무시
        
        # 다음 섹션 패턴 찾기 (줄 시작 부분에서만 매칭)
        next_patterns = section_patterns.get(section_num, [])
        for pattern in next_patterns:
            # 타겟 섹션 시작 이후의 텍스트에서만 검색
            remaining_text = full_text[target_start_pos + 1:]
            multiline_pattern = r'^\s*' + pattern
            match = re.search(multiline_pattern, remaining_text, re.MULTILINE | re.IGNORECASE)
            if match:
                # 타겟 섹션 시작 위치 기준으로 상대 위치 계산
                relative_pos = match.start()
                next_section_start = target_start_pos + 1 + relative_pos
                break
        
        if next_section_start < len(full_text):
            break  # 가장 가까운 다음 섹션을 찾았으면 종료
    
    # 타겟 섹션 내용 추출
    extracted_text = full_text[target_start_pos:next_section_start].strip()
    
    # 중복 섹션 제목 제거: 같은 섹션 제목이 내용 중간에 다시 나오면 그 이후 내용 제거
    # 첫 번째 섹션 제목 이후의 모든 섹션 제목 패턴 찾기
    first_title_end = None
    for pattern in target_patterns:
        multiline_pattern = r'^\s*' + pattern
        match = re.search(multiline_pattern, extracted_text, re.MULTILINE | re.IGNORECASE)
        if match:
            # 섹션 제목 다음 줄바꿈이나 공백까지 찾기
            title_end = match.end()
            # 다음 줄바꿈까지 찾기
            next_newline = extracted_text.find('\n', title_end)
            if next_newline != -1:
                first_title_end = next_newline
            else:
                first_title_end = title_end
            break
    
    if first_title_end:
        # 첫 번째 섹션 제목 이후에 같은 섹션 제목이 또 나오는지 확인 (줄 시작 부분에서만)
        remaining_text = extracted_text[first_title_end:]
        for pattern in target_patterns:
            multiline_pattern = r'^\s*' + pattern
            match = re.search(multiline_pattern, remaining_text, re.MULTILINE | re.IGNORECASE)
            if match:
                # 중복 섹션 제목 발견 - 그 이전까지만 유지
                duplicate_pos = first_title_end + match.start()
                extracted_text = extracted_text[:duplicate_pos].strip()
                print(f"⚠️ [WARN] 섹션 {target_section} 중복 제목 발견 및 제거", file=sys.stderr)
                break
    
    # 섹션 제목 제거 (내용만 반환)
    # 첫 번째 줄이 섹션 제목인 경우 제거
    lines = extracted_text.split('\n')
    if lines:
        first_line = lines[0].strip()
        is_title = False
        for pattern in target_patterns:
            multiline_pattern = r'^\s*' + pattern
            if re.search(multiline_pattern, first_line, re.IGNORECASE):
                is_title = True
                break
        
        if is_title:
            # 섹션 제목과 구분선(---) 제거
            if len(lines) > 1 and lines[1].strip() == "---":
                extracted_text = "\n".join(lines[2:]).strip()
            else:
                extracted_text = "\n".join(lines[1:]).strip()
    
    return extracted_text


def generate_ai_analysis(
    snapshot_data: Dict,
    system_prompt: Optional[str] = None,
    system_prompt_file: Optional[str] = None,
    sections: Optional[List[int]] = None,
    api_key: Optional[str] = None
) -> Dict:
    """
    스냅샷 데이터를 AI에게 분석시키고 결과를 signals 필드에 추가
    
    Args:
        snapshot_data: 스냅샷 JSON 데이터 (report_meta, facts, signals 포함)
        system_prompt: System Prompt 문자열 (직접 제공)
        system_prompt_file: System Prompt 파일 경로
        sections: 분석할 섹션 번호 리스트 (None이면 1-9 모두)
        api_key: Gemini API 키 (None이면 환경변수에서 로드)
    
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
        system_prompt_text = load_system_prompt(system_prompt_file)
    
    # signals 초기화 (없으면 생성)
    if "signals" not in snapshot_data:
        snapshot_data["signals"] = {}
    
    signals = snapshot_data["signals"]
    
    # 분석할 섹션 리스트 (기본값: 1-9)
    if sections is None:
        sections = list(range(1, 10))
    
    # 각 섹션별 분석 수행
    for section_num in sections:
        section_key = f"section_{section_num}_analysis"
        
        try:
            print(f"🤖 [INFO] 섹션 {section_num} AI 분석 시작...", file=sys.stderr)
            
            # 섹션별 프롬프트 생성
            section_prompt = build_section_prompt(section_num, snapshot_data)
            
            # 전체 프롬프트 구성
            full_prompt = f"{system_prompt_text}\n\n{section_prompt}"
            
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
            analysis_text = extract_section_content(raw_analysis_text, section_num)
            
            # 원본과 추출된 텍스트 길이 비교 로그
            if len(analysis_text) < len(raw_analysis_text):
                reduction_pct = (1 - len(analysis_text) / len(raw_analysis_text)) * 100
                print(f"📝 [INFO] 섹션 {section_num} 내용 추출: {len(raw_analysis_text)}자 → {len(analysis_text)}자 ({reduction_pct:.1f}% 감소)", file=sys.stderr)
            
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

