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
    # google-genai v1.0+에서 Safety Settings는 types 모듈에 포함됨
    try:
        from google.genai.types import HarmCategory, HarmBlockThreshold
        SAFETY_SETTINGS_AVAILABLE = True
    except ImportError:
        # fallback: google.generativeai에서 시도 (구버전 호환)
        try:
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            SAFETY_SETTINGS_AVAILABLE = True
        except ImportError:
            SAFETY_SETTINGS_AVAILABLE = False
            HarmCategory = None
            HarmBlockThreshold = None
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    SAFETY_SETTINGS_AVAILABLE = False
    genai = None
    types = None
    HarmCategory = None
    HarmBlockThreshold = None

# 환경 변수
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# 핵심 카테고리 정의
CORE_CATEGORIES = ["상의", "바지", "스커트", "원피스", "니트웨어", "셋업"]

# System Instruction (거대 데이터로 인한 지시사항 손실 방지)
SYSTEM_INSTRUCTION = """
당신은 29CM 패션 트렌드 분석가입니다.
사용자가 제공하는 JSON 데이터를 기반으로, 한국어(Korean)로 된 서술형 트렌드 리포트를 작성하십시오.

[절대 규칙]
1. 모든 답변은 반드시 '완벽한 한국어'로 작성해야 합니다.
2. JSON 문법이나 특수문자 기호(*, :)를 남발하지 말고, 자연스러운 줄글(Paragraph) 형태로 쓰세요.
3. 데이터(브랜드명, 상품명)를 문장 속에 자연스럽게 포함시키세요.
4. 중간에 끊기거나 영문만 출력되지 않도록 주의하세요.
5. 섹션 제목도 반드시 한글로 작성하세요 (예: "## 시장 개요", "## 세그먼트별 심층 분석").
6. 빈칸 채우기나 개조식(~함, ~임)을 절대 금지합니다.
7. 반드시 "~했습니다.", "~입니다." 체를 사용하여, 옆에서 말해주듯이 자연스럽게 문장을 이으세요.
"""


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
    
    # JSON 데이터 준비 (한글 유니코드 변환 방지 필수)
    data_json = json.dumps(all_categories_data, ensure_ascii=False, indent=2)
    
    # 디버깅: 데이터 JSON에 한글이 제대로 포함되었는지 확인
    print(f"🔍 [DEBUG] 데이터 JSON 길이: {len(data_json):,} 자", file=sys.stderr)
    print(f"🔍 [DEBUG] 프롬프트 데이터 일부 (처음 200자): {data_json[:200]}", file=sys.stderr)
    
    # 한글 포함 여부 확인
    has_korean = any('\uac00' <= char <= '\ud7a3' for char in data_json)
    has_unicode_escape = '\\u' in data_json
    print(f"🔍 [DEBUG] 데이터 JSON 한글 포함 여부: {has_korean}", file=sys.stderr)
    print(f"🔍 [DEBUG] 데이터 JSON 유니코드 이스케이프 포함 여부: {has_unicode_escape}", file=sys.stderr)
    if has_unicode_escape:
        print(f"⚠️ [WARN] ⚠️⚠️⚠️ 경고: 데이터에 유니코드 이스케이프(\\u...)가 포함되어 있습니다!", file=sys.stderr)
        print(f"   - 이는 ensure_ascii=False가 제대로 작동하지 않았음을 의미합니다.", file=sys.stderr)
    
    # 프롬프트 단순화 (데이터만 포함, 지시사항은 system_instruction에 위임)
    prompt = f"""
[분석할 데이터]
현재 주차: {current_week}

데이터 요약:
- 급상승 상품: {total_rising}개
- 신규 진입 상품: {total_new_entry}개
- 순위 하락 상품: {total_rank_drop}개

핵심 6대 카테고리 데이터 (각 세그먼트당 상위 20개):
{data_json}

위 데이터를 바탕으로 다음 3가지 섹션으로 구성된 트렌드 리포트를 작성해주세요:
1. 시장 개요: 소재, TPO, 가격 흐름을 문단으로 서술
2. 세그먼트별 심층 분석: 급상승, 신규진입, 순위하락 이슈를 문단으로 서술
3. 카테고리별 심층 분석: 각 카테고리별 트렌드를 문단으로 서술
"""

    return prompt


def generate_trend_analysis(
    snapshot_data: Dict,
    api_key: Optional[str] = None,
    max_tokens: int = 16384  # 월간 리포트 섹션 5와 동일 (긴 리포트를 위해 증가)
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
        
        # 프롬프트 생성 (데이터만 포함, 지시사항은 system_instruction에 위임)
        data_prompt = build_trend_analysis_prompt(snapshot_data)
        
        # System Instruction과 데이터 프롬프트 결합
        # (거대 데이터로 인한 지시사항 손실 방지를 위해 system_instruction을 프롬프트 앞부분에 명시적으로 포함)
        full_prompt = f"{SYSTEM_INSTRUCTION}\n\n{data_prompt}"
        
        # 프롬프트 데이터 검증 (정밀 디버깅)
        prompt_length = len(full_prompt)
        print(f"🔍 [DEBUG] 프롬프트 총 길이: {prompt_length:,} 자", file=sys.stderr)
        
        # 데이터 부분에 한글과 유니코드 이스케이프 확인
        has_korean_in_data = any('\uac00' <= char <= '\ud7a3' for char in data_prompt)
        has_unicode_in_data = '\\u' in data_prompt
        print(f"🔍 [DEBUG] 프롬프트 한글 포함 여부: {has_korean_in_data}", file=sys.stderr)
        print(f"🔍 [DEBUG] 프롬프트 유니코드 이스케이프 포함 여부: {has_unicode_in_data}", file=sys.stderr)
        if has_unicode_in_data:
            print(f"⚠️ [WARN] ⚠️⚠️⚠️ 프롬프트에 유니코드 이스케이프(\\u...)가 발견되었습니다!", file=sys.stderr)
        
        # 프롬프트 크기 확인
        print(f"📊 [INFO] 프롬프트 크기: {prompt_length:,}자", file=sys.stderr)
        if prompt_length > 100000:  # 10만자 이상이면 경고
            print(f"⚠️ [WARN] 프롬프트가 매우 큽니다 ({prompt_length:,}자).", file=sys.stderr)
        
        # 프롬프트에 한글 포함 여부 확인 (디버깅)
        if "어반드레스" in data_prompt or "비터셀즈" in data_prompt or "썸웨어버터" in data_prompt:
            print(f"✅ [DEBUG] 프롬프트에 한글 브랜드명이 포함되어 있습니다.", file=sys.stderr)
        
        # Safety Settings 설정 (한글 필터링 방지)
        safety_settings = None
        if SAFETY_SETTINGS_AVAILABLE and HarmCategory is not None and HarmBlockThreshold is not None:
            try:
                # google-genai v1.0+ 방식 시도
                safety_settings = [
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE
                    ),
                ]
                print(f"✅ [DEBUG] Safety Settings 설정 완료 (모든 카테고리 BLOCK_NONE)", file=sys.stderr)
            except (AttributeError, TypeError) as e:
                # types.SafetySetting이 없으면 dict 형태로 시도
                try:
                    safety_settings = {
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                    print(f"✅ [DEBUG] Safety Settings 설정 완료 (dict 형태, 모든 카테고리 BLOCK_NONE)", file=sys.stderr)
                except Exception as e2:
                    print(f"⚠️ [WARN] Safety Settings 설정 실패: {e2}, 기본 설정 사용", file=sys.stderr)
        else:
            print(f"⚠️ [WARN] Safety Settings 사용 불가 (import 실패), 기본 설정 사용", file=sys.stderr)
        
        # AI 모델 호출 (System Instruction을 프롬프트 앞부분에 포함)
        print(f"📤 [INFO] Gemini API 호출 중... (System Instruction 포함)", file=sys.stderr)
        
        # GenerateContentConfig 구성
        config_kwargs = {
            "temperature": 0.7,  # 월간 리포트와 동일
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": max_tokens,  # 8192 유지
        }
        
        # Safety Settings 추가 (있는 경우)
        if safety_settings:
            config_kwargs["safety_settings"] = safety_settings
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
            config=types.GenerateContentConfig(**config_kwargs)
        )
        
        # Finish Reason 및 Safety Ratings 확인 (정밀 디버깅)
        finish_reason = None
        safety_ratings = None
        prompt_feedback = None
        
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            # Finish Reason 확인
            if hasattr(candidate, 'finish_reason'):
                finish_reason = candidate.finish_reason
            elif hasattr(candidate, 'finishReason'):
                finish_reason = candidate.finishReason
            elif hasattr(candidate, 'finishMessage'):
                finish_reason = candidate.finishMessage
            
            # Safety Ratings 확인
            if hasattr(candidate, 'safety_ratings'):
                safety_ratings = candidate.safety_ratings
            elif hasattr(candidate, 'safetyRatings'):
                safety_ratings = candidate.safetyRatings
        
        # Prompt Feedback 확인
        if hasattr(response, 'prompt_feedback'):
            prompt_feedback = response.prompt_feedback
        elif hasattr(response, 'promptFeedback'):
            prompt_feedback = response.promptFeedback
        
        # 디버깅 정보 출력
        print(f"🔍 [DEBUG] 종료 원인(Finish Reason): {finish_reason}", file=sys.stderr)
        if finish_reason and finish_reason in ['SAFETY', 'RECITATION', 'OTHER']:
            print(f"⚠️ [WARN] ⚠️⚠️⚠️ 중대한 문제 발견: Finish Reason이 '{finish_reason}'입니다!", file=sys.stderr)
            print(f"   - SAFETY: 안전 설정에 의해 차단됨 (한글 필터링 가능성)", file=sys.stderr)
            print(f"   - RECITATION: 저작권 보호에 의해 차단됨", file=sys.stderr)
            print(f"   - OTHER: 기타 이유로 차단됨", file=sys.stderr)
        elif finish_reason and 'MAX_TOKENS' in str(finish_reason):
            print(f"⚠️ [WARN] ⚠️⚠️⚠️ 응답이 토큰 제한에 걸려서 잘렸습니다 (MAX_TOKENS)!", file=sys.stderr)
            print(f"   - 현재 max_output_tokens: {max_tokens}", file=sys.stderr)
            print(f"   - 생성된 리포트가 불완전할 수 있습니다. 토큰 제한을 늘려야 할 수 있습니다.", file=sys.stderr)
        
        print(f"🔍 [DEBUG] 안전 등급(Safety Ratings): {safety_ratings}", file=sys.stderr)
        print(f"🔍 [DEBUG] 프롬프트 피드백(Prompt Feedback): {prompt_feedback}", file=sys.stderr)
        
        # Safety Ratings 상세 출력
        if safety_ratings:
            print(f"🔍 [DEBUG] Safety Ratings 상세:", file=sys.stderr)
            if isinstance(safety_ratings, list):
                for rating in safety_ratings:
                    category = getattr(rating, 'category', getattr(rating, 'categoryName', 'UNKNOWN'))
                    probability = getattr(rating, 'probability', getattr(rating, 'severity', 'UNKNOWN'))
                    threshold = getattr(rating, 'threshold', 'UNKNOWN')
                    print(f"   - {category}: probability={probability}, threshold={threshold}", file=sys.stderr)
            elif isinstance(safety_ratings, dict):
                for key, value in safety_ratings.items():
                    print(f"   - {key}: {value}", file=sys.stderr)
        
        # Prompt Feedback 상세 출력
        if prompt_feedback:
            print(f"🔍 [DEBUG] Prompt Feedback 상세:", file=sys.stderr)
            if hasattr(prompt_feedback, 'block_reason'):
                print(f"   - Block Reason: {prompt_feedback.block_reason}", file=sys.stderr)
            if hasattr(prompt_feedback, 'safety_ratings'):
                print(f"   - Safety Ratings: {prompt_feedback.safety_ratings}", file=sys.stderr)
        
        # 응답 파싱
        analysis_text = None
        if hasattr(response, 'text'):
            analysis_text = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts') and candidate.content.parts:
                analysis_text = candidate.content.parts[0].text
            elif hasattr(candidate, 'content'):
                analysis_text = str(candidate.content)
            else:
                analysis_text = str(candidate)
        
        if not analysis_text:
            analysis_text = str(response)
        
        # 한글 포함 여부 확인 (디버깅)
        if analysis_text:
            korean_count = sum(1 for char in analysis_text if '\uac00' <= char <= '\ud7a3')
            total_chars = len(analysis_text)
            korean_ratio = (korean_count / total_chars * 100) if total_chars > 0 else 0
            print(f"🔍 [DEBUG] 생성된 리포트 한글 포함 여부:", file=sys.stderr)
            print(f"   - 한글 문자 개수: {korean_count}/{total_chars} ({korean_ratio:.1f}%)", file=sys.stderr)
            if korean_ratio < 10:
                print(f"⚠️ [WARN] ⚠️⚠️⚠️ 생성된 리포트에 한글이 거의 없습니다 ({korean_ratio:.1f}%)!", file=sys.stderr)
                print(f"   - 응답 미리보기 (처음 500자): {analysis_text[:500]}", file=sys.stderr)
            
        # Finish Reason이 문제가 있는 경우 경고
        if finish_reason and finish_reason in ['SAFETY', 'RECITATION']:
            print(f"⚠️ [WARN] ⚠️⚠️⚠️ 응답이 '{finish_reason}'로 인해 차단되었습니다!", file=sys.stderr)
            print(f"   - analysis_text 길이: {len(analysis_text) if analysis_text else 0}자", file=sys.stderr)
            if analysis_text:
                print(f"   - analysis_text 미리보기 (처음 200자): {analysis_text[:200]}", file=sys.stderr)
        
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

