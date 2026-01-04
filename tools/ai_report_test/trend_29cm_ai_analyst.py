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
당신은 데이터 분석가입니다.
제공된 요약 데이터를 보고 한국어(Korean)로 서술형 리포트를 작성하세요.

[절대 규칙]
1. 모든 답변은 반드시 '완벽한 한국어'로 작성해야 합니다.
2. 자연스러운 줄글(Paragraph) 형태로 쓰세요.
3. 데이터(브랜드명, 상품명)를 문장 속에 자연스럽게 포함시키세요.
4. 중간에 끊기거나 영문만 출력되지 않도록 주의하세요.
5. 섹션 제목도 반드시 한글로 작성하세요 (예: "## 시장 개요", "## 세그먼트별 심층 분석").
6. 빈칸 채우기나 개조식(~함, ~임)을 절대 금지합니다.
7. 반드시 "~했습니다.", "~입니다." 체를 사용하여, 옆에서 말해주듯이 자연스럽게 문장을 이으세요.
"""


def optimize_data_for_flash(json_data: Dict) -> str:
    """
    JSON 데이터를 텍스트 형태로 압축하여 Flash 모델이 처리하기 쉽게 변환
    JSON 기호를 제거하고 깔끔한 텍스트 형태로 변환
    
    Before (JSON): {"Brand": "비터셀즈", "Product": "니트", "Rank": 1} (5만자, 특수문자 밭)
    After (텍스트): - 비터셀즈 | 니트 | 1위 변동 | 50000원 (1.5만자, 깔끔한 텍스트)
    """
    report_lines = []
    
    # JSON 구조 순회
    for category, cat_data in json_data.items():
        if category == 'insights':
            continue  # 불필요한 메타데이터 제외
        
        report_lines.append(f"\n== {category} ==")
        
        for segment, items in cat_data.items():  # rising_star, new_entry, rank_drop
            if not items:  # 빈 리스트는 건너뛰기
                continue
                
            segment_name = segment.upper()
            report_lines.append(f"[{segment_name}]")
            
            # 상위 15개 아이템만 처리 (데이터 줄이기)
            for item in items[:15]:
                brand = item.get('Brand', 'Brand') or 'Brand'
                product = item.get('Product', 'Product') or 'Product'
                # 한글 깨짐 방지를 위해 변수 직접 사용
                change = item.get('Rank_Change', 0) or 0
                price = item.get('Price', 0) or 0
                
                # 한 줄 요약 포맷 (한글 깨짐 방지)
                # 순위 변화가 None이거나 0이면 표시하지 않음
                if change is None or change == 0:
                    change_str = "변동없음"
                elif change > 0:
                    change_str = f"+{change}위 상승"
                else:
                    change_str = f"{change}위 하락"
                
                line = f"- {brand} | {product} | {change_str} | {price}원"
                report_lines.append(line)
    
    return "\n".join(report_lines)


def build_trend_analysis_prompt(snapshot_data: Dict, section_num: int = None) -> str:
    """
    29CM 트렌드 분석 프롬프트 생성 (섹션별)
    
    Args:
        snapshot_data: 트렌드 스냅샷 데이터
        section_num: 섹션 번호 (1=시장개요, 2=세그먼트분석, 3=카테고리분석), None이면 전체
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
    
    # 데이터를 텍스트 형태로 압축 (Flash 모델 최적화)
    optimized_data = optimize_data_for_flash(all_categories_data)
    
    # 섹션별 프롬프트 구성
    section_prompts = {
        1: f"""
[섹션 1: 시장 개요]
⚠️ **중요: 이 섹션 1만 분석하고 답변하세요.**

현재 주차: {current_week}

데이터 요약:
- 급상승 상품: {total_rising}개
- 신규 진입 상품: {total_new_entry}개
- 순위 하락 상품: {total_rank_drop}개

핵심 6대 카테고리 데이터:
{optimized_data}

위 데이터를 바탕으로 **시장 개요**를 작성하세요:
- 소재(Material) 흐름 분석
- TPO(Time, Place, Occasion) 분석
- 가격(Price) 흐름 분석

각 항목을 자연스러운 문단으로 서술하세요.
""",
        2: f"""
[섹션 2: 세그먼트별 심층 분석]
⚠️ **중요: 이 섹션 2만 분석하고 답변하세요.**

현재 주차: {current_week}

핵심 6대 카테고리 데이터:
{optimized_data}

위 데이터를 바탕으로 **세그먼트별 심층 분석**을 작성하세요:
- 급상승(Rising Star) 이슈 분석
- 신규진입(New Entry) 이슈 분석
- 순위하락(Rank Drop) 이슈 분석

각 세그먼트를 자연스러운 문단으로 서술하세요.
""",
        3: f"""
[섹션 3: 카테고리별 심층 분석]
⚠️ **중요: 이 섹션 3만 분석하고 답변하세요.**

현재 주차: {current_week}

핵심 6대 카테고리 데이터:
{optimized_data}

위 데이터를 바탕으로 **카테고리별 심층 분석**을 작성하세요:
- 각 카테고리(상의, 바지, 스커트, 원피스, 니트웨어, 셋업)별 트렌드 분석
- 카테고리별 주요 브랜드 및 상품 패턴 분석

각 카테고리를 자연스러운 문단으로 서술하세요.
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

위 데이터를 바탕으로 다음 3가지 섹션으로 구성된 트렌드 리포트를 작성해주세요:
1. 시장 개요: 소재, TPO, 가격 흐름을 문단으로 서술
2. 세그먼트별 심층 분석: 급상승, 신규진입, 순위하락 이슈를 문단으로 서술
3. 카테고리별 심층 분석: 각 카테고리별 트렌드를 문단으로 서술
"""


def generate_trend_analysis(
    snapshot_data: Dict,
    api_key: Optional[str] = None,
    max_tokens: int = 8192  # 각 섹션별로 8192 사용
) -> Optional[str]:
    """
    29CM 트렌드 스냅샷 데이터를 AI로 분석하여 리포트 생성 (섹션별 분리 생성)
    월간 리포트와 동일하게 섹션별로 나눠서 생성하여 한글 생성 안정성 확보
    
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
        
        # 섹션별로 개별 API 호출 (월간 리포트와 동일한 방식)
        sections = [1, 2, 3]  # 1=시장개요, 2=세그먼트분석, 3=카테고리분석
        section_results = {}
        
        for section_num in sections:
            section_names = {1: "시장 개요", 2: "세그먼트별 심층 분석", 3: "카테고리별 심층 분석"}
            
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
                    "temperature": 0.7,  # 월간 리포트와 동일
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": max_tokens,  # 8192
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
                
                # 원본 첫 줄 로그 출력 (제목 제거 전)
                first_line_raw = section_text.split('\n')[0].strip() if section_text else ""
                print(f"📄 [RESPONSE] 섹션 {section_num} 원본 첫 줄: {first_line_raw[:200]}", file=sys.stderr)
                
                # 섹션 제목 패턴 제거 (더 보수적으로 - 첫 줄만 제거)
                lines = section_text.split('\n')
                if lines and (lines[0].strip().startswith('##') or lines[0].strip().startswith('# 섹션')):
                    # 첫 줄이 섹션 제목이면 제거
                    if len(lines) > 1:
                        section_text = '\n'.join(lines[1:]).strip()
                    else:
                        section_text = section_text.strip()
                
                # 한글 포함 여부 확인 (디버깅) - 제목 제거 후
                if section_text:
                    korean_count = sum(1 for char in section_text if '\uac00' <= char <= '\ud7a3')
                    total_chars = len(section_text)
                    korean_ratio = (korean_count / total_chars * 100) if total_chars > 0 else 0
                    print(f"🔍 [DEBUG] 섹션 {section_num} 한글 포함 여부 (제목 제거 후): {korean_count}/{total_chars} ({korean_ratio:.1f}%)", file=sys.stderr)
                    if korean_ratio < 30:
                        print(f"⚠️ [WARN] 섹션 {section_num}에 한글이 적습니다 ({korean_ratio:.1f}%)!", file=sys.stderr)
                        print(f"   - 응답 미리보기 (처음 500자): {section_text[:500]}", file=sys.stderr)
                    
                    # 섹션 제목 제거 후 첫 줄 로그 출력
                    first_line_after = section_text.split('\n')[0].strip() if section_text else ""
                    if first_line_after:
                        print(f"📄 [RESPONSE] 섹션 {section_num} 제목 제거 후 첫 줄: {first_line_after[:200]}", file=sys.stderr)
                    else:
                        print(f"⚠️ [WARN] 섹션 {section_num} 제목 제거 후 첫 줄이 비어있습니다!", file=sys.stderr)
                else:
                    print(f"⚠️ [WARN] 섹션 {section_num} 전체 응답이 비어있습니다!", file=sys.stderr)
                
                # 아이콘/이모지 제거 (안전장치)
                section_text = remove_icons_and_emojis(section_text)
                
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
        
        # 섹션별 결과 검증 (디버깅)
        for section_num in [1, 2, 3]:
            if section_num in section_results:
                section_content = section_results[section_num]
                korean_count = sum(1 for char in section_content if '\uac00' <= char <= '\ud7a3')
                total_chars = len(section_content)
                korean_ratio = (korean_count / total_chars * 100) if total_chars > 0 else 0
                first_line = section_content.split('\n')[0].strip()[:100] if section_content else ""
                print(f"🔍 [DEBUG] 섹션 {section_num} 최종 저장 내용 검증:", file=sys.stderr)
                print(f"   - 길이: {total_chars}자", file=sys.stderr)
                print(f"   - 한글 포함: {korean_count}/{total_chars} ({korean_ratio:.1f}%)", file=sys.stderr)
                print(f"   - 첫 줄 (100자): {first_line}", file=sys.stderr)
        
        # 리포트 구성 (섹션 제목 포함)
        analysis_parts = []
        
        if 1 in section_results:
            analysis_parts.append(f"## 시장 개요\n\n{section_results[1]}")
        
        if 2 in section_results:
            analysis_parts.append(f"\n\n## 세그먼트별 심층 분석\n\n{section_results[2]}")
        
        if 3 in section_results:
            analysis_parts.append(f"\n\n## 카테고리별 심층 분석\n\n{section_results[3]}")
        
        analysis_text = "\n".join(analysis_parts)
        
        # 합친 직후 검증 (디버깅)
        if analysis_text:
            korean_count_temp = sum(1 for char in analysis_text if '\uac00' <= char <= '\ud7a3')
            total_chars_temp = len(analysis_text)
            korean_ratio_temp = (korean_count_temp / total_chars_temp * 100) if total_chars_temp > 0 else 0
            print(f"🔍 [DEBUG] 합친 직후 리포트 검증:", file=sys.stderr)
            print(f"   - 길이: {total_chars_temp}자", file=sys.stderr)
            print(f"   - 한글 포함: {korean_count_temp}/{total_chars_temp} ({korean_ratio_temp:.1f}%)", file=sys.stderr)
        
        # 최종 한글 포함 여부 확인
        if analysis_text:
            korean_count = sum(1 for char in analysis_text if '\uac00' <= char <= '\ud7a3')
            total_chars = len(analysis_text)
            korean_ratio = (korean_count / total_chars * 100) if total_chars > 0 else 0
            print(f"🔍 [DEBUG] 최종 리포트 한글 포함 여부:", file=sys.stderr)
            print(f"   - 한글 문자 개수: {korean_count}/{total_chars} ({korean_ratio:.1f}%)", file=sys.stderr)
            
        char_count = len(analysis_text)
        print(f"✅ [INFO] 전체 분석 리포트 생성 완료 ({char_count}자)", file=sys.stderr)
        
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

