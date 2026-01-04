"""
29CM 트렌드 분석 AI 리포트 생성 모듈
- Google Gemini API를 사용하여 29CM 트렌드 스냅샷 데이터를 분석
- 소싱/마케팅/가격 전략에 즉시 적용 가능한 액션 아이템 도출
"""

import os
import sys
import json
import re
import traceback
from typing import Dict, Optional, Any
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
    
    # 2. 스크립트 위치 기준으로 프로젝트 루트 찾기 (ngn_board)
    if not env_loaded:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # tools/ai_report_test/ -> tools/ -> 프로젝트 루트 (ngn_board)
        project_root = os.path.dirname(os.path.dirname(script_dir))
        env_path = os.path.join(project_root, ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
            env_loaded = True
            print(f"✅ [INFO] .env 파일 로드됨: {env_path}", file=sys.stderr)
        else:
            print(f"⚠️ [DEBUG] .env 파일을 찾을 수 없습니다: {env_path}", file=sys.stderr)
    
    # 3. 기본 load_dotenv() 시도 (현재 디렉토리 및 상위 디렉토리 자동 탐색)
    if not env_loaded:
        load_dotenv(override=True)  # .env 파일이 없어도 에러 없이 진행
        
except ImportError:
    print("⚠️ [WARN] python-dotenv 패키지가 설치되지 않았습니다.", file=sys.stderr)
    print("   설치: pip install python-dotenv", file=sys.stderr)

# Google Gen AI SDK
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    types = None

# 환경 변수
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# 핵심 카테고리 정의
CORE_CATEGORIES = ["상의", "바지", "스커트", "원피스", "니트웨어", "셋업"]


def build_trend_analysis_prompt(snapshot_data: Dict) -> str:
    """
    29CM 트렌드 분석 프롬프트 생성
    지침서 기반 프롬프트 구성
    """
    tabs_data = snapshot_data.get("tabs_data", {})
    current_week = snapshot_data.get("current_week", "")
    
    # 전체 데이터 준비 (모든 탭의 데이터 통합)
    all_categories_data = {}
    
    for tab_name, tab_data in tabs_data.items():
        all_categories_data[tab_name] = {
            "rising_star": tab_data.get("rising_star", []),
            "new_entry": tab_data.get("new_entry", []),
            "rank_drop": tab_data.get("rank_drop", [])
        }
    
    # 데이터 요약 통계
    total_rising = sum(len(data.get("rising_star", [])) for data in all_categories_data.values())
    total_new_entry = sum(len(data.get("new_entry", [])) for data in all_categories_data.values())
    total_rank_drop = sum(len(data.get("rank_drop", [])) for data in all_categories_data.values())
    
    prompt = f"""당신은 여성 의류 쇼핑몰 MD 또는 마케팅 대행사의 수석 데이터 분석가입니다.

## 📋 [지침서] 29CM 트렌드 분석 AI 리포트 생성 규칙

### 1. 역할 및 목표 (Role & Goal)
- **Role**: 여성 의류 쇼핑몰 MD 또는 마케팅 대행사의 수석 데이터 분석가
- **Target Audience**: 여성 패션 의류를 판매하는 쇼핑몰 대표 및 MD
- **Goal**: 단순한 순위 나열이 아닌, **소싱(Sourcing), 마케팅(Marketing), 가격 전략(Pricing)**에 즉시 적용 가능한 '액션 아이템' 도출
- **핵심 원칙**: "왜 떴는가?", "무엇이 지고 있는가?", "그래서 무엇을 팔아야 하는가?"에 대한 답을 제시

### 2. 분석 범위 및 제약사항
- **대상 데이터**: 제공된 29CM 랭킹 JSON 데이터 (순위, 변동폭, 브랜드, 상품명, 가격, 이미지 등)
- **카테고리 집중**:
  - 전체 시장 흐름: 모든 카테고리(홈웨어, 언더웨어 포함)를 포괄하여 거시적 트렌드 파악
  - 상세 분석: 핵심 6대 카테고리({', '.join(CORE_CATEGORIES)})에 집중
- **금지 사항**:
  - 사용자의 자사몰 데이터에 대한 추측성 발언 금지
  - 근거 없는 뇌피셜 금지 (반드시 데이터에 기반한 팩트만 서술)

### 3. 리포트 구조 (3단 구성)
반드시 다음 3가지 섹션으로 구성하고, 순서대로 출력하세요.

#### Section 1. Market Overview (시장 핵심 키워드 3가지)
전체 시장을 관통하는 3가지 키워드 요약:
- **Material (소재)**: 유행하는 텍스처나 원단 (예: 플리스, 코듀로이, 헤어리 니트)
- **Occasion (TPO)**: 소비 목적 (예: 연초 모임룩 vs 집콕 홈웨어)
- **Price (가격)**: 소비 패턴 (예: 가성비와 고가 아우터의 양극화)

#### Section 2. Segment Deep Dive (세그먼트별 심층 분석)
3가지 세그먼트의 '속도와 방향성' 분석:
- **🔥 급상승 (Rising Star)**: 무엇이 트렌드를 주도하며 치고 올라오는가? (예: 보온 소재로의 이동)
- **🚀 신규 진입 (New Entry)**: 새로운 루키 브랜드나 고단가 아이템의 등장
- **📉 순위 하락 (Rank Drop)**: 무엇이 시즌 아웃되거나 대체되었는가? (예: 얇은 소재, 애매한 컬러)

#### Section 3. Category Deep Dive (6대 핵심 카테고리 상세)
각 카테고리별 구체적인 스타일/핏/디자인 분석:
{', '.join(CORE_CATEGORIES)} (각 1~2줄 요약 + Key Item 언급)

### 4. 분석 방법론 - "근거 필수"
AI는 문장을 작성할 때 반드시 아래 **[데이터 근거]**를 포함해야 합니다:
- **구체적 수치**: "급상승했다" (X) -> "74계단 상승하여 1위를 탈환했다" (O)
- **브랜드/상품명 명시**: "특정 브랜드가 인기다" (X) -> "**'플로움'**이 원피스 상위권을 독점했다" (O)
- **인과 관계 설명**: "스커트 순위가 떨어졌다" (X) -> "한파로 인해 '미니 기장' 스커트가 **'기모 바지'**로 대체되며 순위가 하락했다" (O)

### 5. 디자인 및 톤앤매너
- **톤앤매너**: 전문적이고 분석적인 어조 (해요체 사용 가능하나, 내용은 드라이하게)
- **UI 요소**:
  - 중요 키워드는 굵게(Bold) 처리
  - 가독성을 위해 글머리 기호(Bullet points) 적극 활용
  - 문단 사이 여백을 주어 시각적 피로도 감소
- **⚠️ 중요**: 아이콘 이모지는 절대 사용하지 마세요. 순수 텍스트만 사용하세요.

### 6. 출력 형식
- **마크다운 형식**으로 작성하세요
- **토큰 제한**: 충분한 길이로 작성하세요 (최대 8192 토큰 지원, 한글 기준 약 12,000자 이상)
- **섹션 구분**: 각 섹션은 명확히 구분하고, 제목은 `##` 또는 `###` 마크다운 헤더로 표시하세요

---

## 📊 분석 대상 데이터

**현재 주차**: {current_week}

**데이터 요약**:
- 급상승 상품: {total_rising}개
- 신규 진입 상품: {total_new_entry}개
- 순위 하락 상품: {total_rank_drop}개

**전체 카테고리 데이터**:
{json.dumps(all_categories_data, ensure_ascii=False, indent=2)}

---

위 지침을 정확히 따르며, 제공된 데이터를 기반으로 분석 리포트를 작성해주세요.
특히 **구체적인 수치, 브랜드명, 상품명**을 반드시 포함하여 근거 기반 분석을 해주세요.
"""

    return prompt


def generate_trend_analysis(
    snapshot_data: Dict,
    api_key: Optional[str] = None,
    max_tokens: int = 8192
) -> Optional[str]:
    """
    29CM 트렌드 스냅샷 데이터를 AI로 분석하여 리포트 생성
    
    Args:
        snapshot_data: 트렌드 스냅샷 데이터 (tabs_data, current_week 포함)
        api_key: Gemini API 키 (None이면 환경변수에서 로드)
        max_tokens: 최대 토큰 수 (기본값 8192, 월간 리포트와 동일, 한글 기준 약 12,000자 이상 지원)
    
    Returns:
        AI 분석 리포트 텍스트 (마크다운 형식)
    """
    # google-genai 패키지 확인
    if not GENAI_AVAILABLE or genai is None or types is None:
        raise ImportError("google-genai 패키지가 설치되지 않았습니다. 'pip install google-genai'로 설치해주세요.")
    
    # API 키 확인
    api_key = api_key or GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았거나 api_key 파라미터가 필요합니다.")
    
    # Google Gen AI SDK Client 초기화
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        raise ImportError(f"google-genai 초기화 실패: {e}")
    
    try:
        print(f"🤖 [INFO] 29CM 트렌드 분석 AI 리포트 생성 시작...", file=sys.stderr)
        
        # 프롬프트 생성
        prompt = build_trend_analysis_prompt(snapshot_data)
        
        # AI 모델 호출
        print(f"📤 [INFO] Gemini API 호출 중...", file=sys.stderr)
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=max_tokens,  # 월간 리포트와 동일하게 8192 사용
                top_p=0.95,
            )
        )
        
        # 응답 파싱
        if hasattr(response, 'text'):
            analysis_text = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            analysis_text = response.candidates[0].content.parts[0].text
        else:
            analysis_text = str(response)
        
        # 아이콘/이모지 제거 (안전장치)
        analysis_text = remove_icons_and_emojis(analysis_text)
        
        # 토큰 수 체크 (경고만)
        char_count = len(analysis_text)
        if char_count > max_tokens * 2:  # 한글 기준으로 대략 계산
            print(f"⚠️ [WARN] 분석 리포트가 길 수 있습니다 ({char_count}자). 토큰 제한: 약 {max_tokens}", file=sys.stderr)
        else:
            print(f"✅ [INFO] 분석 리포트 생성 완료 ({char_count}자)", file=sys.stderr)
        
        return analysis_text.strip()
        
    except Exception as e:
        print(f"❌ [ERROR] AI 분석 생성 실패: {e}", file=sys.stderr)
        traceback.print_exc()
        return None


def remove_icons_and_emojis(text: str) -> str:
    """
    텍스트에서 아이콘 이모지 제거 (안전장치)
    마크다운 형식이나 특수 문자는 유지
    """
    # 이모지 제거 (유니코드 이모지 범위)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    
    text = emoji_pattern.sub('', text)
    
    # 불필요한 이모지 문자 제거 (단, 마크다운 문법은 유지)
    # 화살표, 불릿 포인트 등은 유지
    text = re.sub(r'[🔥🚀📉📊💡📋✅❌⚠️]', '', text)
    
    return text.strip()


def generate_trend_analysis_from_snapshot(
    snapshot_data: Dict,
    api_key: Optional[str] = None
) -> Dict:
    """
    스냅샷 데이터에 AI 분석 리포트를 추가하여 반환
    
    Args:
        snapshot_data: 트렌드 스냅샷 데이터
        api_key: Gemini API 키
    
    Returns:
        AI 분석 리포트가 추가된 snapshot_data
    """
    try:
        # AI 분석 생성
        analysis_text = generate_trend_analysis(snapshot_data, api_key=api_key)
        
        if analysis_text:
            # snapshot_data에 분석 리포트 추가
            if "insights" not in snapshot_data:
                snapshot_data["insights"] = {}
            
            snapshot_data["insights"]["analysis_report"] = analysis_text
            snapshot_data["insights"]["generated_at"] = datetime.utcnow().isoformat() + "Z"
            
            print(f"✅ [SUCCESS] AI 분석 리포트가 스냅샷에 추가되었습니다.", file=sys.stderr)
        else:
            print(f"⚠️ [WARN] AI 분석 리포트 생성 실패, 스냅샷은 그대로 유지됩니다.", file=sys.stderr)
        
        return snapshot_data
        
    except Exception as e:
        print(f"❌ [ERROR] AI 분석 리포트 추가 실패: {e}", file=sys.stderr)
        traceback.print_exc()
        # 에러가 나도 스냅샷 데이터는 그대로 반환
        return snapshot_data


def generate_ai_analysis_from_file(
    snapshot_file: str,
    output_file: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict:
    """
    스냅샷 파일(GCS 또는 로컬)에서 읽어서 AI 분석 후 저장
    월간 리포트와 동일한 방식
    
    Args:
        snapshot_file: 입력 스냅샷 파일 경로 (로컬 파일 또는 gs:// 경로)
        output_file: 출력 파일 경로 (None이면 입력 파일에 덮어쓰기, 로컬 파일 또는 gs:// 경로)
        api_key: Gemini API 키
    
    Returns:
        AI 분석 리포트가 추가된 snapshot_data
    """
    try:
        from google.cloud import storage
        import gzip
        import io
    except ImportError:
        print("❌ [ERROR] google-cloud-storage 패키지가 필요합니다.", file=sys.stderr)
        raise
    
    # 입력 파일 읽기 (GCS 또는 로컬)
    if snapshot_file.startswith("gs://"):
        print(f"📥 [INFO] GCS에서 파일 로드 중: {snapshot_file}", file=sys.stderr)
        # GCS에서 다운로드
        parts = snapshot_file.replace("gs://", "").split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"GCS 경로 파싱 실패: {snapshot_file}")
        
        bucket_name = parts[0]
        blob_path = parts[1]
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        if not blob.exists():
            raise FileNotFoundError(f"GCS 파일이 존재하지 않습니다: {snapshot_file}")
        
        # Gzip 압축 해제
        snapshot_bytes = blob.download_as_bytes()
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(snapshot_bytes)) as gz_file:
                snapshot_json_str = gz_file.read().decode('utf-8')
        except (gzip.BadGzipFile, OSError):
            snapshot_json_str = snapshot_bytes.decode('utf-8')
        
        snapshot_data = json.loads(snapshot_json_str)
    else:
        print(f"📥 [INFO] 로컬 파일 로드 중: {snapshot_file}", file=sys.stderr)
        with open(snapshot_file, 'r', encoding='utf-8') as f:
            snapshot_data = json.load(f)
    
    # AI 분석 수행
    snapshot_data = generate_trend_analysis_from_snapshot(
        snapshot_data,
        api_key=api_key
    )
    
    # 결과 저장 (출력 경로 미지정 시 입력 파일 경로에 덮어쓰기)
    output_path = output_file or snapshot_file
    
    if output_path.startswith("gs://"):
        print(f"📤 [INFO] GCS에 파일 업로드 중: {output_path}", file=sys.stderr)
        # GCS에 업로드
        parts = output_path.replace("gs://", "").split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"GCS 경로 파싱 실패: {output_path}")
        
        bucket_name = parts[0]
        blob_path = parts[1]
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        # JSON 직렬화 및 Gzip 압축
        json_str = json.dumps(snapshot_data, ensure_ascii=False, indent=2)
        json_bytes = json_str.encode('utf-8')
        compressed_bytes = gzip.compress(json_bytes)
        
        blob.upload_from_string(compressed_bytes, content_type='application/gzip')
    else:
        print(f"📤 [INFO] 로컬 파일 저장 중: {output_path}", file=sys.stderr)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2, sort_keys=True)
    
    print(f"✅ [SUCCESS] AI 분석 결과 저장 완료: {output_path}", file=sys.stderr)
    
    return snapshot_data


if __name__ == "__main__":
    # CLI 사용 예시
    import argparse
    
    parser = argparse.ArgumentParser(description="29CM 트렌드 분석 AI 리포트 생성")
    parser.add_argument("snapshot_file", help="스냅샷 파일 경로 (로컬 또는 gs:// 경로)")
    parser.add_argument("--output", "-o", help="출력 파일 경로 (기본값: 입력 파일에 덮어쓰기)")
    parser.add_argument("--api-key", help="Gemini API 키 (기본값: 환경변수에서 로드)")
    
    args = parser.parse_args()
    
    # AI 분석 추가 (GCS 지원)
    generate_ai_analysis_from_file(
        snapshot_file=args.snapshot_file,
        output_file=args.output,
        api_key=args.api_key
    )

