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
    
    # 데이터 요약 및 필수 필드만 추출 (프롬프트 크기 최소화)
    def extract_essential_fields(items: list, max_items: int = 20) -> list:
        """필수 필드만 추출하여 AI 프롬프트 크기 최적화"""
        essential = []
        for item in items[:max_items]:  # 상위 N개만 사용
            essential.append({
                "Brand": item.get("Brand_Name"),  # 필수: 브랜드명
                "Product": item.get("Product_Name"),  # 필수: 상품명
                "Rank_Change": item.get("Rank_Change"),  # 필수: 순위 변화
                "Price": item.get("price")  # 필수: 가격
                # Ranking, This_Week_Rank, Last_Week_Rank, item_url, thumbnail_url 제외
            })
        return essential
    
    # 핵심 6대 카테고리만 선택 (전체 제외)
    core_tabs = []
    for core_cat in CORE_CATEGORIES:
        if core_cat in tabs_data:
            core_tabs.append(core_cat)
    
    # 핵심 카테고리가 없으면 전체 데이터 사용
    if not core_tabs:
        core_tabs = ["전체"] if "전체" in tabs_data else []
    
    # 데이터 준비 (핵심 6대 카테고리만, 각 세그먼트당 상위 10개)
    all_categories_data = {}
    
    for tab_name in core_tabs:
        if tab_name not in tabs_data:
            continue
        tab_data = tabs_data[tab_name]
        all_categories_data[tab_name] = {
            "rising_star": extract_essential_fields(tab_data.get("rising_star", []), max_items=20),
            "new_entry": extract_essential_fields(tab_data.get("new_entry", []), max_items=20),
            "rank_drop": extract_essential_fields(tab_data.get("rank_drop", []), max_items=20)
        }
    
    # 데이터 요약 통계 (전체 탭 기준)
    total_rising = sum(len(tab_data.get("rising_star", [])) for tab_data in tabs_data.values())
    total_new_entry = sum(len(tab_data.get("new_entry", [])) for tab_data in tabs_data.values())
    total_rank_drop = sum(len(tab_data.get("rank_drop", [])) for tab_data in tabs_data.values())
    
    # 전체 카테고리 목록 (참고용)
    all_tab_names = list(tabs_data.keys())
    
    # JSON 데이터 준비
    data_json = json.dumps(all_categories_data, ensure_ascii=False, indent=2)
    
    prompt = f"""당신은 패션 매거진의 에디터이자 데이터 분석가입니다.
독자가 편하게 읽을 수 있도록, 딱딱한 보고서 말투가 아닌 **'매끄러운 줄글'**로 리포트를 작성하세요.

[절대 규칙]
1. 빈칸 채우기나 개조식(~함, ~임)을 절대 금지합니다.
2. 반드시 **"~했습니다.", "~입니다."** 체를 사용하여, 옆에서 말해주듯이 자연스럽게 문장을 이으세요.
3. 데이터(순위, 브랜드명)는 문장 속에 자연스럽게 녹여내세요. (예: "'비터셀즈'가 1위를 차지했습니다.")
4. JSON 데이터의 브랜드명과 상품명은 그대로 사용하세요. 한글일 수도 있고 영어일 수도 있습니다. 절대 생략하거나 빈칸(** **)으로 두지 마세요.

[작성 순서]
1. Market Overview (소재, TPO, 가격 흐름을 문단으로 서술)
2. Segment Deep Dive (급상승, 신규진입, 순위하락 이슈를 문단으로 서술)
3. Category Deep Dive (각 카테고리별 트렌드를 문단으로 서술)
   - 대상 카테고리: {', '.join(CORE_CATEGORIES)}

[데이터]
현재 주차: {current_week}

데이터 요약:
- 급상승 상품: {total_rising}개
- 신규 진입 상품: {total_new_entry}개
- 순위 하락 상품: {total_rank_drop}개

핵심 6대 카테고리 데이터 (각 세그먼트당 상위 20개):
{data_json}

위 데이터를 바탕으로 자연스럽고 읽기 좋은 리포트를 작성해주세요.
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
        
        # 데이터 확인 (디버깅)
        tabs_data = snapshot_data.get("tabs_data", {})
        if tabs_data:
            first_tab = list(tabs_data.keys())[0]
            first_tab_data = tabs_data[first_tab]
            if first_tab_data.get("rising_star"):
                first_item = first_tab_data["rising_star"][0]
                brand_name = first_item.get("Brand_Name", "")
                product_name = first_item.get("Product_Name", "")
                print(f"🔍 [DEBUG] 샘플 데이터 확인:", file=sys.stderr)
                print(f"   - 브랜드명 (첫 번째 상품): '{brand_name}' ({len(brand_name)}자)", file=sys.stderr)
                print(f"   - 상품명 (첫 번째 상품): '{product_name[:50]}...' ({len(product_name)}자)", file=sys.stderr)
        
        # 프롬프트 생성
        prompt = build_trend_analysis_prompt(snapshot_data)
        
        # 프롬프트 크기 확인
        prompt_length = len(prompt)
        print(f"📊 [INFO] 프롬프트 크기: {prompt_length:,}자", file=sys.stderr)
        if prompt_length > 100000:  # 10만자 이상이면 경고
            print(f"⚠️ [WARN] 프롬프트가 매우 큽니다 ({prompt_length:,}자). 데이터 요약이 필요할 수 있습니다.", file=sys.stderr)
        
        # 프롬프트에 한글 포함 여부 확인 (디버깅)
        if "어반드레스" in prompt or "비터셀즈" in prompt:
            print(f"✅ [DEBUG] 프롬프트에 한글 브랜드명이 포함되어 있습니다.", file=sys.stderr)
        else:
            print(f"⚠️ [DEBUG] 프롬프트에 한글 브랜드명이 보이지 않습니다. JSON 데이터를 확인하세요.", file=sys.stderr)
        
        # AI 모델 호출
        print(f"📤 [INFO] Gemini API 호출 중...", file=sys.stderr)
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.8,  # 수다쟁이 모드: 말을 많이 하게 유도 (0.7에서 0.8로 상향)
                top_p=0.9,
                top_k=40,
                max_output_tokens=max_tokens,  # 8192 유지
                # response_mime_type 제거: 절대 JSON 모드로 두지 않음
            )
        )
        
        # 응답 파싱
        analysis_text = None
        if hasattr(response, 'text'):
            analysis_text = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            if hasattr(response.candidates[0].content, 'parts') and response.candidates[0].content.parts:
                analysis_text = response.candidates[0].content.parts[0].text
            elif hasattr(response.candidates[0], 'content'):
                analysis_text = str(response.candidates[0].content)
            else:
                analysis_text = str(response.candidates[0])
        
        if not analysis_text:
            analysis_text = str(response)
        
        if not analysis_text or len(analysis_text.strip()) < 100:
            print(f"⚠️ [WARN] AI 응답이 너무 짧습니다 ({len(analysis_text) if analysis_text else 0}자).", file=sys.stderr)
            print(f"[DEBUG] 원본 응답 타입: {type(response)}", file=sys.stderr)
            if hasattr(response, '__dict__'):
                print(f"[DEBUG] 응답 속성: {list(response.__dict__.keys())[:10]}", file=sys.stderr)
        
        # 아이콘/이모지 제거 (안전장치)
        analysis_text = remove_icons_and_emojis(analysis_text)
        
        # 토큰 수 체크 (경고만)
        char_count = len(analysis_text)
        if char_count < 500:
            print(f"⚠️ [WARN] 분석 리포트가 너무 짧습니다 ({char_count}자). 데이터가 제대로 전달되었는지 확인하세요.", file=sys.stderr)
        elif char_count > max_tokens * 2:  # 한글 기준으로 대략 계산
            print(f"⚠️ [WARN] 분석 리포트가 길 수 있습니다 ({char_count}자). 토큰 제한: 약 {max_tokens}", file=sys.stderr)
        else:
            print(f"✅ [INFO] 분석 리포트 생성 완료 ({char_count}자)", file=sys.stderr)
        
        return analysis_text.strip() if analysis_text else None
        
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
        
        # Gzip 압축 해제 (월간 리포트와 동일한 방식)
        snapshot_bytes = blob.download_as_bytes(raw_download=True)
        try:
            # 월간 리포트와 동일한 방식: gzip.decompress() 사용
            snapshot_json_str = gzip.decompress(snapshot_bytes).decode('utf-8')
            print(f"✅ [DEBUG] Gzip 압축 해제 성공", file=sys.stderr)
        except (gzip.BadGzipFile, OSError) as e:
            # Gzip 압축 해제 실패 → 압축되지 않은 JSON 파일로 처리
            snapshot_json_str = snapshot_bytes.decode('utf-8')
            print(f"⚠️ [WARN] Gzip 압축 해제 실패, 일반 텍스트로 처리: {e}", file=sys.stderr)
        
        snapshot_data = json.loads(snapshot_json_str)
        
        # 데이터 확인 (디버깅)
        print(f"✅ [DEBUG] 스냅샷 데이터 로드 완료", file=sys.stderr)
        if "tabs_data" in snapshot_data:
            tabs_count = len(snapshot_data["tabs_data"])
            print(f"   - 탭 개수: {tabs_count}", file=sys.stderr)
            # 첫 번째 탭의 첫 번째 상품 확인
            first_tab = list(snapshot_data["tabs_data"].keys())[0] if snapshot_data["tabs_data"] else None
            if first_tab:
                first_tab_data = snapshot_data["tabs_data"][first_tab]
                if first_tab_data.get("rising_star"):
                    first_item = first_tab_data["rising_star"][0]
                    brand_name = first_item.get("Brand_Name", "")
                    product_name = first_item.get("Product_Name", "")
                    print(f"   - 샘플 데이터 확인:", file=sys.stderr)
                    print(f"     * 탭: {first_tab}", file=sys.stderr)
                    print(f"     * 브랜드명: '{brand_name}' ({len(brand_name)}자)", file=sys.stderr)
                    print(f"     * 상품명: '{product_name[:50]}...' ({len(product_name)}자)", file=sys.stderr)
    else:
        print(f"📥 [INFO] 로컬 파일 로드 중: {snapshot_file}", file=sys.stderr)
        with open(snapshot_file, 'r', encoding='utf-8') as f:
            snapshot_data = json.load(f)
    
    # AI 분석 수행
    snapshot_data = generate_trend_analysis_from_snapshot(
        snapshot_data,
        api_key=api_key
    )
    
    # AI 분석 결과 확인 (디버깅)
    if "insights" in snapshot_data and snapshot_data["insights"].get("analysis_report"):
        analysis_report_len = len(snapshot_data["insights"]["analysis_report"])
        print(f"✅ [DEBUG] AI 분석 리포트가 스냅샷 데이터에 포함되어 있습니다 ({analysis_report_len}자).", file=sys.stderr)
    else:
        print(f"⚠️ [DEBUG] AI 분석 리포트가 스냅샷 데이터에 포함되지 않았습니다.", file=sys.stderr)
        print(f"   - insights 필드 존재: {'insights' in snapshot_data}", file=sys.stderr)
        if "insights" in snapshot_data:
            print(f"   - analysis_report 존재: {'analysis_report' in snapshot_data['insights']}", file=sys.stderr)
    
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
        
        # 저장 전 insights 필드 확인 (디버깅)
        if "insights" in snapshot_data and snapshot_data["insights"].get("analysis_report"):
            print(f"✅ [DEBUG] GCS 업로드 전 insights 필드 확인 완료.", file=sys.stderr)
        else:
            print(f"⚠️ [DEBUG] GCS 업로드 전 insights 필드가 없습니다.", file=sys.stderr)
        
        blob.upload_from_string(compressed_bytes, content_type='application/gzip')
        
        # 저장 후 확인 (디버깅)
        print(f"✅ [DEBUG] GCS 업로드 완료. 파일 크기: {len(compressed_bytes):,} bytes", file=sys.stderr)
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

