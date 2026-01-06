"""
29CM 트렌드 분석 AI 리포트 생성 모듈
- Google Gemini API를 사용하여 29CM 트렌드 스냅샷 데이터를 분석
- 텍스트 리포트(AI)와 데이터 시각화(UI)의 역할 분리
- 트렌드 인사이트(Why) 중심의 리포트 생성
"""

import os
import sys
import json
import traceback
from typing import Dict, Optional, Any

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

# 자사몰 매핑 설정 로드
try:
    # 프로젝트 루트 기준으로 config 모듈 경로 추가
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # tools/ai_report_test/ -> tools/ -> 프로젝트 루트
    project_root = os.path.dirname(os.path.dirname(script_dir))
    config_path = os.path.join(project_root, "tools", "config")
    if config_path not in sys.path:
        sys.path.insert(0, os.path.join(project_root, "tools"))
    
    from config.company_mapping import (
        COMPANY_MAPPING,
        OWN_COMPANY_NAMES,
        get_company_korean_name,
        get_company_brands,
        is_own_company_brand
    )
    COMPANY_MAPPING_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    print(f"⚠️ [WARN] 자사몰 매핑 설정을 로드할 수 없습니다: {e}", file=sys.stderr)
    COMPANY_MAPPING_AVAILABLE = False
    COMPANY_MAPPING = {}
    OWN_COMPANY_NAMES = []
    def get_company_korean_name(name): return None
    def get_company_brands(name): return []
    def is_own_company_brand(brand, company=None): return False, None


# ============================================
# 설정 변수 (분석 타겟 브랜드)
# ============================================

# 기본 타겟 브랜드 (함수 파라미터로 오버라이드 가능)
DEFAULT_TARGET_BRAND = "썸웨어버터"


# ============================================
# System Instruction (지침서)
# ============================================

def build_system_instruction(target_brand: str = DEFAULT_TARGET_BRAND, platform: str = "29CM") -> str:
    """
    System Instruction 생성
    
    Args:
        target_brand: 분석 타겟 브랜드명 (한글명, 예: "썸웨어버터", "파이시스", "Ably")
        platform: 플랫폼명 ("29CM" 또는 "Ably")
    
    Returns:
        System Instruction 문자열
    """
    platform_name = "Ably" if platform.upper() == "ABLY" else "29CM"
    return f"""당신은 패션 브랜드 MD를 위한 수석 데이터 분석가입니다.
제공된 {platform_name} 랭킹 데이터를 분석하여 전략 리포트를 작성하세요.
**분석 타겟 브랜드: '{target_brand}'**

[작성 대원칙]
1. **Cluster & Label:** 개별 인기 상품들을 나열하지 마십시오. 대신, **유사한 특징(소재, 디테일, 무드)을 가진 상품들을 그룹화(Clustering)**하고, 그 그룹을 대표하는 **매력적인 트렌드 키워드(Labeling)**를 뽑아내세요.
2. **Structure:** 각 카테고리 당 **가장 강력한 트렌드 흐름 2가지**를 선정하여 요약하세요.
3. **No Robot Tone:** 기계적인 나열("~가 인기입니다.")을 멈추고, MD에게 보고하듯 **"~한 무드가 강세입니다", "~수요가 급증하고 있습니다"**와 같이 흐름을 읽어주는 문체로 작성하세요.
4. **List Forbidden:** 리포트 하단에 '상품 썸네일 카드'가 별도로 배치됩니다. 따라서 텍스트 본문에서는 **개별 상품명이나 순위를 나열하지 마십시오.**
5. **Data-Driven:** 제공된 데이터에만 기반하여 분석하세요. 데이터에 없는 내용은 추측하지 마세요.
6. **Weekly Uniqueness:** 매주 다른 데이터가 제공되므로, 매주 완전히 다른 내용을 작성해야 합니다. 이전 주 리포트나 템플릿을 복사하지 마세요.
7. **Markdown Format:** 반드시 마크다운 형식을 사용하세요. **굵게**, *기울임*, 줄바꿈(빈 줄), 불렛 포인트(`*` 또는 `-`)를 적절히 활용하세요.
8. **Line Breaks:** 가독성을 위해 적절한 줄바꿈을 사용하세요. 카테고리, 세그먼트, 주요 항목 사이에는 반드시 빈 줄을 추가하세요.

[절대 금지 사항]
- **예시나 템플릿 문구를 그대로 복사하지 마세요.** "(예: ...)" 형태의 문구를 출력하지 마세요.
- **고정된 형식이나 패턴을 반복하지 마세요.** 데이터에 따라 구조와 내용이 달라져야 합니다.
- **"트렌드 분석 멘트" 같은 플레이스홀더를 출력하지 마세요.** 실제 데이터 기반 분석만 작성하세요.
- **카테고리별로 항상 같은 형식("**상의:**", "**바지:**" 등)을 강제하지 마세요.** 데이터가 있는 카테고리만 분석하고, 없는 카테고리는 생략하세요.

---

[리포트 출력 구조]

## Section 1. 자사몰 성과 분석

제공된 데이터에서 '{target_brand}' 브랜드의 상품이 포함된 카테고리만 분석하세요.

**데이터에 자사몰 상품이 있는 경우:**

각 카테고리별로 줄바꿈을 하여 분석하세요. 데이터에서 확인된 자사몰 상품의 구체적인 순위 변동과 인기 요인(소재, 디자인, 가격대 등)을 데이터 기반으로 작성하세요. 구체적인 소재명, 디자인 요소, 실루엣 등은 반드시 **굵게** 처리하세요.

**⚠️ 마크다운 굵게 처리 주의사항:**
- `**굵게**` 처리 시, 앞뒤에 괄호 `()` 나 쉼표 `,` 같은 특수문자가 바로 붙으면 마크다운 효과가 사라질 수 있습니다.
- 올바른 예시: `**소재명** (100% 울)` 또는 `**디자인 요소**, **실루엣**`
- 잘못된 예시: `**소재명**(100% 울)` (특수문자가 바로 붙으면 파싱 실패)
- 특수문자 앞에는 공백을 두거나, 여러 키워드를 나열할 때는 각각 별도로 `**키워드1**, **키워드2**` 형식으로 작성하세요.

각 카테고리 사이에는 반드시 빈 줄을 추가하세요. 추상적 표현을 피하고, 실제 데이터에서 확인한 수치나 패턴을 언급하세요.

**데이터에 자사몰 상품이 없는 경우:**

이번 주 데이터에 자사몰 상품이 포함되지 않았습니다.

## Section 2. Market Overview (시장 핵심 트렌드)

제공된 데이터를 기반으로 전체 시장을 관통하는 2가지 핵심 흐름을 요약하세요. (가격 분석 제외) **데이터에 실제로 나타난 패턴만 분석하세요.**

**Material (소재):**

데이터에서 확인된 소재 트렌드를 분석하세요. 데이터에 없는 소재는 언급하지 마세요. 구체적인 소재명과 트렌드 패턴을 데이터에서 확인된 내용만 기반으로 작성하세요.

**중요:** 구체적인 소재명(예: 울, 캐시미어, 플리스, 코듀로이, 벨벳 등)은 반드시 **굵게** 처리하세요.

**⚠️ 마크다운 굵게 처리 주의사항:**
- `**굵게**` 처리 시, 앞뒤에 괄호 `()` 나 쉼표 `,` 같은 특수문자가 바로 붙으면 마크다운 효과가 사라질 수 있습니다.
- 올바른 예시: `**세트 구성** (3PCS, 4PCS)` 또는 `**세트 구성 (3PCS, 4PCS)**`
- 잘못된 예시: `**세트 구성**(3PCS, 4PCS)` (특수문자가 바로 붙으면 파싱 실패)
- 특수문자 앞에는 공백을 두거나, 특수문자까지 포함해서 굵게 처리하세요.

**Mood (무드 & 스타일):**

데이터에서 확인된 시각적 분위기와 디자인적 특징을 분석하세요. 실제 데이터에서 확인된 패턴만 기반으로 작성하세요.

**중요:** 구체적인 디자인 요소, 스타일 키워드, 실루엣, 디테일명(예: 로고 그래픽, 빈티지 워싱, 릴렉스 핏, 스웨트 셋업, 트위드 셋업, 레이스 슬립 드레스, 프릴 디테일, 타이업 디자인 등 데이터에서 확인된 실제 키워드)는 반드시 **굵게** 처리하세요. 데이터에서 나타난 실제 디자인 요소만 강조하세요.

**⚠️ 마크다운 굵게 처리 주의사항:**
- `**굵게**` 처리 시, 앞뒤에 괄호 `()` 나 쉼표 `,` 같은 특수문자가 바로 붙으면 마크다운 효과가 사라질 수 있습니다.
- 올바른 예시: `**세트 구성** (3PCS, 4PCS)` 또는 `**오버핏** 실루엣` 또는 `**트위드 셋업**, **니트 세트**`
- 잘못된 예시: `**세트 구성**(3PCS, 4PCS)` 또는 `**오버핏**,` (특수문자가 바로 붙으면 파싱 실패)
- 특수문자 앞에는 공백을 두거나, 여러 키워드를 나열할 때는 각각 별도로 `**키워드1**, **키워드2**` 형식으로 작성하세요.

⚠️ **중요:** 이 섹션은 **반드시 제공된 데이터를 기반으로** 작성해야 합니다. 예시 문구나 템플릿을 사용하지 마세요. 각 항목 사이에는 반드시 빈 줄을 추가하세요.

## Section 3. TRENDS

⚠️ **중요:** 각 카테고리별로 **가장 강력한 트렌드 흐름 2가지**를 선정하여 요약하세요.

**[동적 사고 가이드 (Thinking Process)]**
각 카테고리 분석 시, 다음 과정을 거쳐 작성하세요:
1.  **관찰:** 상위권 상품들의 공통점은 무엇인가? (예: 로고가 많음, 기장이 짧음, 소재가 독특함)
2.  **명명(Naming):** 이 현상을 한 단어로 정의하면 무엇인가? (예: "Y2K 로고 플레이", "크롭트 실루엣의 부상") -> 이것이 **헤드라인**이 됩니다.
3.  **설명:** 이 트렌드가 왜 발생했는가? 어떤 구체적 디테일(소재, 패턴 등)이 소비자를 자극했는가? -> 이것이 **설명 본문**이 됩니다.

**[작성 포맷 준수]**
각 카테고리 아래에 반드시 불렛 포인트(`*`)를 사용하여 딱 2줄을 작성하세요.
* **트렌드 헤드라인:** 트렌드 배경 및 디테일 설명 문장.
* **트렌드 헤드라인:** 트렌드 배경 및 디테일 설명 문장.

(주의: 헤드라인은 명사형으로 끝내고 굵게 처리, 설명 문장 내 핵심 패션 키워드도 반드시 굵게 처리할 것)

**⚠️ 마크다운 굵게 처리 주의사항:**
- `**굵게**` 처리 시, 앞뒤에 괄호 `()` 나 쉼표 `,` 같은 특수문자가 바로 붙으면 마크다운 효과가 사라질 수 있습니다.
- 올바른 예시: `**트렌드 키워드** (설명)` 또는 `**키워드1**, **키워드2**`
- 잘못된 예시: `**트렌드 키워드**(설명)` (특수문자가 바로 붙으면 파싱 실패)
- 특수문자 앞에는 공백을 두거나, 여러 키워드를 나열할 때는 각각 별도로 `**키워드1**, **키워드2**` 형식으로 작성하세요.

**⚠️ 카테고리 헤드라인 형식 (필수 준수):**
- 각 카테고리는 반드시 `**카테고리명:**` 형식으로 시작해야 합니다.
- 카테고리명은 제공된 데이터에 실제로 존재하는 카테고리명을 정확하게 사용하세요. (예: 29CM의 경우 "상의", "바지", "스커트", "원피스", "니트웨어", "셋업", Ably의 경우 "상의", "팬츠", "스커트", "원피스/세트", "트레이닝", "비치웨어", "아우터" 등)
- 카테고리 헤드라인 다음에는 빈 줄을 추가하고, 그 다음에 분석 텍스트를 작성하세요.

**🔥 급상승 (Rising Star)**

**카테고리명:** (데이터에 있는 카테고리만 작성)
- 위 [동적 사고 가이드]에 따라 급상승 트렌드 2가지를 작성.

**🚀 신규 진입 (New Entry)**

**카테고리명:** (데이터에 있는 카테고리만 작성)
- 위 [동적 사고 가이드]에 따라 신규 진입 트렌드 2가지를 작성.

**📉 순위 하락 (Rank Drop)**

**카테고리명:** (데이터에 있는 카테고리만 작성)
- 위 [동적 사고 가이드]에 따라 하락세에 있는 스타일이나 대체되고 있는 흐름 2가지를 작성.

[작성 스타일]
- **불렛 포인트 형식 필수:** 각 카테고리별 분석은 반드시 불렛 포인트(`-`)를 사용하여 작성하세요. 한 줄로 이어지는 긴 문장보다는 불렛 포인트로 나누어 작성하세요.
- **카테고리 헤드라인 다음 불렛 포인트:** 카테고리 헤드라인(`**카테고리명:**`) 다음 줄부터 불렛 포인트로 시작하는 분석 텍스트를 작성하세요.
- **카테고리, 세그먼트, 주요 항목 사이에는 반드시 빈 줄을 추가**하여 가독성을 높이세요.
- 데이터에 나타난 구체적인 패턴을 데이터에서 확인된 실제 내용만 기반으로 언급하세요.
- **매주 다른 내용 필수:** 매주 다른 데이터가 제공되므로, 매주 완전히 다른 관점과 내용으로 작성해야 합니다. 이전 주와 유사한 표현이나 패턴을 반복하지 마세요.
- **마크다운 형식(**굵게**, *기울임*, 불렛 포인트)을 적절히 활용하세요.**
"""


# ============================================
# 데이터 최적화 함수
# ============================================

def optimize_data_for_flash(json_data: Dict) -> str:
    """
    JSON 데이터를 텍스트 형태로 압축하여 Flash 모델이 처리하기 쉽게 변환
    상품명 길이를 파격적으로 줄여 토큰 절약 및 가독성 확보
    **이 데이터는 AI가 "읽기용"이지, "쓰기용"이 아님을 명심.**
    
    Args:
        json_data: 카테고리별 트렌드 데이터
    
    Returns:
        압축된 전체 데이터 텍스트
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

def build_trend_analysis_prompt(
    snapshot_data: Dict,
    target_brand: str = DEFAULT_TARGET_BRAND
) -> str:
    """
    29CM 트렌드 분석 프롬프트 생성
    
    Args:
        snapshot_data: 트렌드 스냅샷 데이터
        target_brand: 분석 타겟 브랜드명 (한글명)
    
    Returns:
        프롬프트 문자열
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
    
    # 모든 카테고리 선택 (CORE_CATEGORIES 필터링 제거)
    # tabs_data에 있는 모든 카테고리를 사용 (29CM와 Ably 모두 지원)
    all_tabs = list(tabs_data.keys())
    
    # "전체" 탭이 있으면 제외 (세부 카테고리만 사용)
    if "전체" in all_tabs:
        all_tabs = [tab for tab in all_tabs if tab != "전체"]
    
    # 데이터 준비 (모든 카테고리, 각 세그먼트당 상위 15개)
    all_categories_data = {}
    
    for tab_name in all_tabs:
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
    
    # 프롬프트 구성
    prompt = f"""
[분석할 데이터]
현재 주차: {current_week}

데이터 요약:
- 급상승 상품: {total_rising}개
- 신규 진입 상품: {total_new_entry}개
- 순위 하락 상품: {total_rank_drop}개

전체 카테고리 데이터 (각 세그먼트당 상위 15개):
{optimized_data}

⚠️ [중요 지침]
1. **데이터 기반 분석 필수:** 위에 제공된 실제 데이터만을 기반으로 분석하세요. 데이터에 없는 내용은 추측하지 마세요.
2. **예시나 템플릿 금지:** "(예: ...)" 같은 예시 문구나 고정된 템플릿을 사용하지 마세요. 실제 데이터 패턴만 분석하세요.
3. **매주 다른 내용 (필수):** 이번 주 데이터는 이전 주와 다를 수 있으므로, 이번 주 데이터에만 기반하여 완전히 새로운 내용을 작성하세요. 이전 주 리포트와 유사한 표현, 패턴, 구조를 절대 반복하지 마세요. 매주 데이터를 새롭게 분석하여 고유한 인사이트를 도출하세요.
4. **유연한 구조:** 데이터가 없는 카테고리나 세그먼트는 생략하세요. 모든 항목을 강제로 채울 필요가 없습니다.
5. **구체적 패턴 분석:** 추상적 표현보다는, 데이터에서 확인된 구체적 패턴을 데이터에 나타난 실제 내용만 기반으로 제시하세요.
6. **마크다운 형식 필수:** 반드시 마크다운 형식을 사용하세요. **굵게**, *기울임*, 줄바꿈(빈 줄), 불렛 포인트(`*` 또는 `-`)를 적절히 활용하세요.
7. **줄바꿈 필수:** 가독성을 위해 적절한 줄바꿈을 사용하세요. 섹션, 카테고리, 세그먼트, 주요 항목 사이에는 반드시 빈 줄을 추가하세요.

위 데이터를 바탕으로 다음 3가지 섹션으로 구성된 트렌드 리포트를 작성해주세요.
"""
    
    return prompt


# ============================================
# AI 분석 생성 함수
# ============================================

def generate_trend_analysis(
    snapshot_data: Dict,
    api_key: Optional[str] = None,
    target_brand: Optional[str] = None,
    max_tokens: int = 16384,
    platform: str = "29CM"
) -> Optional[str]:
    """
    29CM 트렌드 스냅샷 데이터를 AI로 분석하여 리포트 생성
    
    Args:
        snapshot_data: 트렌드 스냅샷 데이터 (tabs_data, current_week 포함)
        api_key: Gemini API 키 (None이면 환경변수에서 로드)
        target_brand: 분석 타겟 브랜드명 (한글명, None이면 DEFAULT_TARGET_BRAND 사용)
        max_tokens: 최대 토큰 수 (기본값 16384)
    
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
    
    # 타겟 브랜드 확인 (우선순위: 파라미터 > snapshot_data > 기본값)
    if target_brand is None:
        # snapshot_data에서 company_name 추출 시도 (있으면)
        company_name_en = snapshot_data.get("company_name")
        if company_name_en and COMPANY_MAPPING_AVAILABLE:
            # company_name_en이 문자열이면 그대로, 리스트면 첫 번째 요소
            if isinstance(company_name_en, list):
                company_name_en = company_name_en[0] if company_name_en else None
            
            if company_name_en:
                # 소문자로 정규화
                company_name_en = str(company_name_en).lower().strip()
                target_brand = get_company_korean_name(company_name_en)
        
        if not target_brand:
            target_brand = DEFAULT_TARGET_BRAND
    
    print(f"🎯 [INFO] 분석 타겟 브랜드: {target_brand}", file=sys.stderr)
    
    # Google Gen AI SDK Client 초기화
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        raise ImportError(f"google-genai 초기화 실패: {e}")
    
    try:
        print(f"🤖 [INFO] 29CM 트렌드 분석 AI 리포트 생성 시작...", file=sys.stderr)
        
        # System Instruction 생성
        system_instruction = build_system_instruction(target_brand, platform=platform)
        
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
        
        # 프롬프트 생성
        prompt = build_trend_analysis_prompt(snapshot_data, target_brand=target_brand)
        
        # System Instruction과 프롬프트 결합
        full_prompt = f"{system_instruction}\n\n{prompt}"
        
        # 프롬프트 크기 확인
        prompt_length = len(full_prompt)
        print(f"📊 [INFO] 프롬프트 크기: {prompt_length:,}자", file=sys.stderr)
        
        # AI 모델 호출
        print(f"📤 [INFO] Gemini API 호출 중...", file=sys.stderr)
        
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
        
        # 마크다운 보존: 후처리 없이 원본 그대로 저장
        # ⚠️ remove_icons_and_emojis 함수 호출 금지 (마크다운 깨짐 방지)
        analysis_text = analysis_text.strip()
        
        # 한글 포함 여부 확인 (디버깅)
        if analysis_text:
            korean_count = sum(1 for char in analysis_text if '\uac00' <= char <= '\ud7a3')
            total_chars = len(analysis_text)
            korean_ratio = (korean_count / total_chars * 100) if total_chars > 0 else 0
            print(f"🔍 [DEBUG] 리포트 한글 포함 여부: {korean_count}/{total_chars} ({korean_ratio:.1f}%)", file=sys.stderr)
            if korean_ratio < 30:
                print(f"⚠️ [WARN] 리포트에 한글이 적습니다 ({korean_ratio:.1f}%)!", file=sys.stderr)
        
        char_count = len(analysis_text)
        print(f"✅ [INFO] 분석 리포트 생성 완료 ({char_count}자)", file=sys.stderr)
        
        return analysis_text if analysis_text else None
        
    except Exception as e:
        print(f"❌ [ERROR] AI 분석 생성 실패: {e}", file=sys.stderr)
        traceback.print_exc()
        return None


# ============================================
# 스냅샷 처리 함수
# ============================================

def generate_trend_analysis_from_snapshot(
    snapshot_data: Dict,
    api_key: Optional[str] = None,
    target_brand: Optional[str] = None,
    platform: str = "29CM"
) -> Dict:
    """
    스냅샷 데이터에 AI 분석 리포트를 추가하여 반환
    
    Args:
        snapshot_data: 트렌드 스냅샷 데이터
        api_key: Gemini API 키
        target_brand: 분석 타겟 브랜드명 (한글명, None이면 자동 감지)
    
    Returns:
        AI 분석 리포트가 추가된 snapshot_data
    """
    try:
        # AI 분석 생성
        analysis_text = generate_trend_analysis(
            snapshot_data,
            api_key=api_key,
            target_brand=target_brand,
            platform=platform
        )
        
        if analysis_text:
            # snapshot_data에 분석 리포트 추가
            if "insights" not in snapshot_data:
                snapshot_data["insights"] = {}
            
            from datetime import datetime
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
    api_key: Optional[str] = None,
    target_brand: Optional[str] = None,
    platform: str = "29CM"
) -> Dict:
    """
    스냅샷 파일(GCS 또는 로컬)에서 읽어서 AI 분석 후 저장
    
    Args:
        snapshot_file: 입력 스냅샷 파일 경로 (로컬 파일 또는 gs:// 경로)
        output_file: 출력 파일 경로 (None이면 입력 파일에 덮어쓰기, 로컬 파일 또는 gs:// 경로)
        api_key: Gemini API 키
        target_brand: 분석 타겟 브랜드명 (한글명, None이면 자동 감지)
    
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
        api_key=api_key,
        target_brand=target_brand,
        platform=platform
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
    parser.add_argument("--target-brand", help="분석 타겟 브랜드명 (한글명, 예: '썸웨어버터', '파이시스')")
    
    args = parser.parse_args()
    
    # AI 분석 추가 (GCS 지원)
    generate_ai_analysis_from_file(
        snapshot_file=args.snapshot_file,
        output_file=args.output,
        api_key=args.api_key,
        target_brand=args.target_brand
    )
