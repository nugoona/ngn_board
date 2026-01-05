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
    import google.genai as genai
    from google.genai import types
    GENAI_AVAILABLE = True
    
    # Safety Settings
    try:
        from google.genai.types import HarmCategory, HarmBlockThreshold
        SAFETY_SETTINGS_AVAILABLE = True
    except (ImportError, AttributeError):
        HarmCategory = None
        HarmBlockThreshold = None
        SAFETY_SETTINGS_AVAILABLE = False
        
except ImportError:
    genai = None
    types = None
    GENAI_AVAILABLE = False
    HarmCategory = None
    HarmBlockThreshold = None
    SAFETY_SETTINGS_AVAILABLE = False
    print("⚠️ [WARN] google-genai 패키지가 설치되지 않았습니다.", file=sys.stderr)
    print("   설치: pip install google-genai", file=sys.stderr)

# 환경 변수
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

# 핵심 6대 카테고리
CORE_CATEGORIES = ["상의", "바지", "스커트", "원피스", "니트웨어", "셋업"]


# ============================================
# System Instruction (지침서)
# ============================================

SYSTEM_INSTRUCTION = """당신은 여성 의류 쇼핑몰 MD를 위한 수석 데이터 분석가입니다.
제공된 29CM 랭킹 데이터를 분석하여, 소싱/마케팅/가격 전략에 적용 가능한 '액션 아이템'을 도출하세요.

[리포트 구조 (반드시 준수)]
리포트는 다음 3가지 섹션으로 구성되며, **반드시 글머리 기호(Bullet Points)**를 사용하여 구조화해야 합니다.

## Section 1. Market Overview (시장 핵심 키워드 3가지)
전체 시장을 관통하는 3가지 키워드를 아래 항목별로 요약하세요.
* **Material (소재):** 유행하는 텍스처나 원단의 트렌드를 데이터 기반으로 분석하여 제시하세요. 실제 데이터에 나타난 소재들을 중심으로 작성하세요.
* **Occasion (TPO):** 소비 목적과 착용 시나리오를 분석하세요. 데이터에 나타난 패턴을 바탕으로 소비자의 구매 목적을 파악하여 제시하세요.
* **Price (가격):** 소비 패턴과 가격대별 트렌드를 분석하세요. 데이터에 나타난 가격 분포와 소비 행태를 바탕으로 패턴을 제시하세요.

## Section 2. Segment Deep Dive (세그먼트별 심층 분석)
3가지 세그먼트의 '속도와 방향성'을 분석하세요.
* **🔥 급상승 (Rising Star):** 무엇이 트렌드를 주도하며 치고 올라오는가? 실제 데이터에 나타난 급상승 아이템의 특징과 패턴을 분석하세요.
* **🚀 신규 진입 (New Entry):** 새로운 루키 브랜드나 고단가 아이템의 등장을 분석하세요. 데이터에 나타난 신규 진입 아이템의 특징을 제시하세요.
* **📉 순위 하락 (Rank Drop):** 무엇이 시즌 아웃되거나 대체되었는가? 데이터에 나타난 순위 하락 아이템의 패턴을 분석하세요.

## Section 3. Category Deep Dive (6대 핵심 카테고리 상세)
각 카테고리별 트렌드와 Key Item을 분석하세요. (대상: 상의, 바지, 스커트, 원피스, 니트웨어, 셋업)
각 카테고리마다 아래 형식으로 작성하세요:
* **카테고리명:** (해당 카테고리의 트렌드를 1줄로 요약)
  - Key Item: **'브랜드명'**의 **'상품명'** (구체적 순위 변동 수치 포함)

[작성 원칙 (매우 중요)]
1. **가독성 최우선:** 긴 줄글(Essay)을 금지합니다. 간결한 문장과 리스트 형식을 사용하세요.
2. **근거 필수:** 추상적 표현을 피하고, 구체적인 수치나 데이터를 포함하세요. 예를 들어 "급상승했다"가 아닌 "XX계단 상승하여 X위를 기록했다"와 같이 구체적 근거를 제시하세요.
3. **정확한 명칭:** 브랜드/상품명은 제공된 데이터의 원문 그대로 **'작은따옴표'**와 **굵게(Bold)** 처리하여 표기하세요.
4. **데이터 기반 분석:** 모든 주장은 제공된 데이터에 기반해야 합니다. 데이터에 없는 내용은 추측하지 마세요.
5. **톤앤매너:** 전문적이고 드라이한 분석가 어조를 사용하세요 (해요체 사용). 서론이나 결론은 생략하고 핵심 분석에 집중하세요.
6. **시즌 독립성:** 특정 시즌이나 기간에 종속되지 않는 일반적이고 재현 가능한 분석을 작성하세요. 매주 다른 데이터에도 적용 가능한 프레임워크를 유지하세요.
"""


# ============================================
# 데이터 최적화 함수
# ============================================

def optimize_data_for_flash(json_data: Dict) -> str:
    """
    JSON 데이터를 텍스트 형태로 압축하여 Flash 모델이 처리하기 쉽게 변환
    상품명 길이를 파격적으로 줄여 토큰 절약 및 가독성 확보
    """
    lines = []
    
    # JSON 구조 순회
    for category, cat_data in json_data.items():
        if category == 'insights':
            continue  # 불필요한 메타데이터 제외
        
        lines.append(f"\n== {category} ==")
        
        for segment, items in cat_data.items():  # rising_star, new_entry, rank_drop
            if not items:  # 빈 리스트는 건너뛰기
                continue
                
            segment_name = segment.upper()
            lines.append(f"[{segment_name}]")
            
            # 상위 15개 아이템만 처리 (데이터 줄이기)
            for item in items[:15]:
                brand = item.get('Brand', '') or ''
                product = item.get('Product', '') or ''
                
                # 상품명 단축 로직 (20자 초과 시 18자 + ..)
                if len(product) > 20:
                    product = product[:18] + ".."
                
                # 한글 깨짐 방지를 위해 변수 직접 사용
                change = item.get('Rank_Change', 0) or 0
                price = item.get('Price', 0) or 0
                
                # 순위 변화 포맷팅
                if change is None or change == 0:
                    change_str = "변동없음"
                elif change > 0:
                    change_str = f"+{change}위 상승"
                else:
                    change_str = f"{change}위 하락"
                
                # 한 줄 요약 포맷
                line = f"- {brand} | {product} | {change_str} | {price}원"
                lines.append(line)
    
    return "\n".join(lines)


# ============================================
# 프롬프트 생성 함수
# ============================================

def build_trend_analysis_prompt(snapshot_data: Dict, section_num: int = None) -> str:
    """
    29CM 트렌드 분석 프롬프트 생성 (섹션별)
    
    Args:
        snapshot_data: 트렌드 스냅샷 데이터
        section_num: 섹션 번호 (1=시장개요, 2=세그먼트분석, 3=카테고리분석), None이면 전체
    """
    tabs_data = snapshot_data.get("tabs_data", {})
    current_week = snapshot_data.get("current_week", "")
    
    # 데이터 요약 및 필수 필드만 추출
    def extract_essential_fields(items: list, max_items: int = 15) -> list:
        """필수 필드만 추출하여 AI 프롬프트 크기 최적화"""
        essential = []
        for item in items[:max_items]:  # 상위 N개만 사용
            essential.append({
                "Brand": item.get("Brand_Name"),  # 필수: 브랜드명
                "Product": item.get("Product_Name"),  # 필수: 상품명
                "Rank_Change": item.get("Rank_Change"),  # 필수: 순위 변화
                "Price": item.get("price")  # 필수: 가격
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
    
    # 데이터 준비 (핵심 6대 카테고리만, 각 세그먼트당 상위 15개)
    all_categories_data = {}
    
    for tab_name in core_tabs:
        if tab_name not in tabs_data:
            continue
        tab_data = tabs_data[tab_name]
        all_categories_data[tab_name] = {
            "rising_star": extract_essential_fields(tab_data.get("rising_star", []), max_items=15),
            "new_entry": extract_essential_fields(tab_data.get("new_entry", []), max_items=15),
            "rank_drop": extract_essential_fields(tab_data.get("rank_drop", []), max_items=15)
        }
    
    # 데이터 요약 통계 (전체 탭 기준)
    total_rising = sum(len(tab_data.get("rising_star", [])) for tab_data in tabs_data.values())
    total_new_entry = sum(len(tab_data.get("new_entry", [])) for tab_data in tabs_data.values())
    total_rank_drop = sum(len(tab_data.get("rank_drop", [])) for tab_data in tabs_data.values())
    
    # 데이터를 텍스트 형태로 압축 (Flash 모델 최적화 + 상품명 단축)
    optimized_data = optimize_data_for_flash(all_categories_data)
    
    # 디버깅: 압축된 데이터 확인
    print(f"🔍 [DEBUG] 압축된 데이터 길이: {len(optimized_data):,} 자", file=sys.stderr)
    print(f"🔍 [DEBUG] 압축된 데이터 일부 (처음 300자):\n{optimized_data[:300]}", file=sys.stderr)
    
    # 한글 포함 여부 확인
    has_korean = any('\uac00' <= char <= '\ud7a3' for char in optimized_data)
    print(f"🔍 [DEBUG] 압축된 데이터 한글 포함 여부: {has_korean}", file=sys.stderr)
    
    # 섹션별 프롬프트 구성
    section_prompts = {
        1: f"""
[섹션 1: Market Overview (시장 핵심 키워드 3가지)]
⚠️ **중요: 이 섹션 1만 분석하고 답변하세요.**

현재 주차: {current_week}

데이터 요약:
- 급상승 상품: {total_rising}개
- 신규 진입 상품: {total_new_entry}개
- 순위 하락 상품: {total_rank_drop}개

핵심 6대 카테고리 데이터:
{optimized_data}

위 데이터를 바탕으로 **시장 개요**를 작성하세요:
* **Material (소재):** 유행하는 텍스처나 원단
* **Occasion (TPO):** 소비 목적
* **Price (가격):** 소비 패턴

각 항목을 글머리 기호로 간결하게 작성하세요.
""",
        2: f"""
[섹션 2: Segment Deep Dive (세그먼트별 심층 분석)]
⚠️ **중요: 이 섹션 2만 분석하고 답변하세요.**

현재 주차: {current_week}

핵심 6대 카테고리 데이터:
{optimized_data}

위 데이터를 바탕으로 **세그먼트별 심층 분석**을 작성하세요:
* **🔥 급상승 (Rising Star):** 무엇이 트렌드를 주도하며 치고 올라오는가?
* **🚀 신규 진입 (New Entry):** 새로운 루키 브랜드나 고단가 아이템의 등장
* **📉 순위 하락 (Rank Drop):** 무엇이 시즌 아웃되거나 대체되었는가?

각 세그먼트를 글머리 기호로 간결하게 작성하세요. 근거(구체적 순위 변동)를 반드시 포함하세요.
""",
        3: f"""
[섹션 3: Category Deep Dive (6대 핵심 카테고리 상세)]
⚠️ **중요: 이 섹션 3만 분석하고 답변하세요.**

현재 주차: {current_week}

핵심 6대 카테고리 데이터:
{optimized_data}

위 데이터를 바탕으로 **카테고리별 심층 분석**을 작성하세요:
각 카테고리(상의, 바지, 스커트, 원피스, 니트웨어, 셋업)별로:
* **카테고리명:** (트렌드 1줄 요약)
  - Key Item: **'브랜드'**의 **'상품명'** (구체적 순위 변동 포함)

각 카테고리를 글머리 기호로 간결하게 작성하세요.
"""
    }
    
    if section_num and section_num in section_prompts:
        return section_prompts[section_num]
    else:
        # 전체 프롬프트 (하위 호환성)
        return f"""
[분석할 데이터]
현재 주차: {current_week}

데이터 요약:
- 급상승 상품: {total_rising}개
- 신규 진입 상품: {total_new_entry}개
- 순위 하락 상품: {total_rank_drop}개

핵심 6대 카테고리 데이터 (각 세그먼트당 상위 15개):
{optimized_data}

위 데이터를 바탕으로 다음 3가지 섹션으로 구성된 트렌드 리포트를 작성해주세요.
"""
"""

    return ""


# ============================================
# AI 분석 생성 함수
# ============================================

def generate_trend_analysis(
    snapshot_data: Dict,
    api_key: Optional[str] = None,
    max_tokens: int = 8192
) -> Optional[str]:
    """
    29CM 트렌드 스냅샷 데이터를 AI로 분석하여 리포트 생성 (섹션별 분리 생성)
    
    Args:
        snapshot_data: 트렌드 스냅샷 데이터 (tabs_data, current_week 포함)
        api_key: Gemini API 키 (None이면 환경변수에서 로드)
        max_tokens: 최대 토큰 수 (각 섹션별 기본값 8192)
    
    Returns:
        AI 분석 리포트 텍스트 (마크다운 형식, 섹션별 결과 합침)
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
        print(f"🤖 [INFO] 29CM 트렌드 분석 AI 리포트 생성 시작... (섹션별 분리 생성)", file=sys.stderr)
        
        # Safety Settings 설정 (한글 필터링 방지 - 필수)
        safety_settings = None
        if SAFETY_SETTINGS_AVAILABLE and HarmCategory is not None and HarmBlockThreshold is not None:
            try:
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
                print(f"⚠️ [WARN] Safety Settings 설정 실패: {e}, 기본 설정 사용", file=sys.stderr)
        else:
            print(f"⚠️ [WARN] Safety Settings 사용 불가 (import 실패), 기본 설정 사용", file=sys.stderr)
        
        # 섹션별로 개별 API 호출
        sections = [1, 2, 3]  # 1=시장개요, 2=세그먼트분석, 3=카테고리분석
        section_results = {}
        section_names = {1: "Market Overview", 2: "Segment Deep Dive", 3: "Category Deep Dive"}
        
        for section_num in sections:
            try:
                print(f"🤖 [INFO] 섹션 {section_num} ({section_names[section_num]}) AI 분석 시작...", file=sys.stderr)
                
                # 섹션별 프롬프트 생성
                section_prompt = build_trend_analysis_prompt(snapshot_data, section_num=section_num)
                
                # System Instruction과 섹션 프롬프트 결합
                full_prompt = f"{SYSTEM_INSTRUCTION}\n\n{section_prompt}"
                
                # 프롬프트 크기 확인
                prompt_length = len(full_prompt)
                print(f"📊 [INFO] 섹션 {section_num} 프롬프트 크기: {prompt_length:,}자", file=sys.stderr)
                
                # AI 모델 호출
                print(f"📤 [INFO] 섹션 {section_num} Gemini API 호출 중...", file=sys.stderr)
                
                # GenerateContentConfig 구성
                config_kwargs = {
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": max_tokens,
                }
                
                # Safety Settings 추가 (있는 경우)
                if safety_settings:
                    config_kwargs["safety_settings"] = safety_settings
                
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(**config_kwargs)
                )
                
                # 응답 파싱
                section_text = None
                if hasattr(response, 'text'):
                    section_text = response.text
                elif hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts') and candidate.content.parts:
                        section_text = candidate.content.parts[0].text
                    elif hasattr(candidate, 'content'):
                        section_text = str(candidate.content)
                    else:
                        section_text = str(candidate)
                
                if not section_text:
                    section_text = str(response)
                
                # 섹션 제목 제거 (AI가 섹션 제목을 포함할 수 있음) - 보수적으로 처리
                section_text = section_text.strip()
                
                # 원본 첫 줄 로그 출력
                first_line_raw = section_text.split('\n')[0].strip() if section_text else ""
                print(f"📄 [RESPONSE] 섹션 {section_num} 원본 첫 줄: {first_line_raw[:200]}", file=sys.stderr)
                
                # 섹션 제목 패턴 제거 (첫 줄만 확인)
                lines = section_text.split('\n')
                if lines and (lines[0].strip().startswith('##') or lines[0].strip().startswith('# 섹션')):
                    if len(lines) > 1:
                        section_text = '\n'.join(lines[1:]).strip()
                    else:
                        section_text = section_text.strip()
                
                # 제목 제거 후 첫 줄 로그 출력
                first_line_after = section_text.split('\n')[0].strip() if section_text else ""
                print(f"📄 [RESPONSE] 섹션 {section_num} 제목 제거 후 첫 줄: {first_line_after[:200]}", file=sys.stderr)
                
                # 한글 포함 여부 확인 (디버깅)
                if section_text:
                    korean_count = sum(1 for char in section_text if '\uac00' <= char <= '\ud7a3')
                    total_chars = len(section_text)
                    korean_ratio = (korean_count / total_chars * 100) if total_chars > 0 else 0
                    print(f"🔍 [DEBUG] 섹션 {section_num} 한글 포함 여부: {korean_count}/{total_chars} ({korean_ratio:.1f}%)", file=sys.stderr)
                    if korean_ratio < 30:
                        print(f"⚠️ [WARN] 섹션 {section_num}에 한글이 적습니다 ({korean_ratio:.1f}%)!", file=sys.stderr)
                
                # 후처리 없이 원본 그대로 저장 (remove_icons_and_emojis 호출 금지)
                section_results[section_num] = section_text
                print(f"✅ [SUCCESS] 섹션 {section_num} AI 분석 완료 ({len(section_text)}자)", file=sys.stderr)
                
            except Exception as e:
                error_msg = f"섹션 {section_num} AI 분석 실패: {str(e)}"
                print(f"❌ [ERROR] {error_msg}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                section_results[section_num] = f"[AI 분석 오류: {error_msg}]"
        
        # 섹션별 결과 합치기
        if not section_results:
            print(f"⚠️ [WARN] 모든 섹션 분석 실패", file=sys.stderr)
            return None
        
        # 리포트 구성 (섹션 제목 포함)
        analysis_parts = []
        
        if 1 in section_results:
            analysis_parts.append(f"## Section 1. Market Overview (시장 핵심 키워드 3가지)\n\n{section_results[1]}")
        
        if 2 in section_results:
            analysis_parts.append(f"\n\n## Section 2. Segment Deep Dive (세그먼트별 심층 분석)\n\n{section_results[2]}")
        
        if 3 in section_results:
            analysis_parts.append(f"\n\n## Section 3. Category Deep Dive (6대 핵심 카테고리 상세)\n\n{section_results[3]}")
        
        analysis_text = "\n".join(analysis_parts)
        
        # 최종 한글 포함 여부 확인
        if analysis_text:
            korean_count = sum(1 for char in analysis_text if '\uac00' <= char <= '\ud7a3')
            total_chars = len(analysis_text)
            korean_ratio = (korean_count / total_chars * 100) if total_chars > 0 else 0
            print(f"🔍 [DEBUG] 최종 리포트 한글 포함 여부: {korean_count}/{total_chars} ({korean_ratio:.1f}%)", file=sys.stderr)
            
        char_count = len(analysis_text)
        print(f"✅ [INFO] 전체 분석 리포트 생성 완료 ({char_count}자)", file=sys.stderr)
        
        return analysis_text.strip() if analysis_text else None
        
    except Exception as e:
        print(f"❌ [ERROR] AI 분석 생성 실패: {e}", file=sys.stderr)
        traceback.print_exc()
        return None


# ============================================
# 스냅샷 처리 함수
# ============================================

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
        snapshot_bytes = blob.download_as_bytes(raw_download=True)
        try:
            snapshot_json_str = gzip.decompress(snapshot_bytes).decode('utf-8')
            print(f"✅ [DEBUG] Gzip 압축 해제 성공", file=sys.stderr)
        except (gzip.BadGzipFile, OSError) as e:
            snapshot_json_str = snapshot_bytes.decode('utf-8')
            print(f"⚠️ [WARN] Gzip 압축 해제 실패, 일반 텍스트로 처리: {e}", file=sys.stderr)
        
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
    
    # AI 분석 결과 확인 (디버깅)
    if "insights" in snapshot_data and snapshot_data["insights"].get("analysis_report"):
        analysis_report_len = len(snapshot_data["insights"]["analysis_report"])
        print(f"✅ [DEBUG] AI 분석 리포트가 스냅샷 데이터에 포함되어 있습니다 ({analysis_report_len}자).", file=sys.stderr)
    else:
        print(f"⚠️ [DEBUG] AI 분석 리포트가 스냅샷 데이터에 포함되지 않았습니다.", file=sys.stderr)
    
    # 결과 저장 (출력 경로 미지정 시 입력 파일 경로에 덮어쓰기)
    output_path = output_file or snapshot_file
    
    if output_path.startswith("gs://"):
        print(f"📤 [INFO] GCS에 파일 업로드 중: {output_path}", file=sys.stderr)
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
        print(f"✅ [DEBUG] GCS 업로드 완료. 파일 크기: {len(compressed_bytes):,} bytes", file=sys.stderr)
    else:
        print(f"📤 [INFO] 로컬 파일 저장 중: {output_path}", file=sys.stderr)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2, sort_keys=True)
    
    print(f"✅ [SUCCESS] AI 분석 결과 저장 완료: {output_path}", file=sys.stderr)
    
    return snapshot_data


# ============================================
# CLI 진입점
# ============================================

if __name__ == "__main__":
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
