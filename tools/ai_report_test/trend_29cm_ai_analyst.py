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
    
    prompt = f"""당신은 여성 의류 쇼핑몰 MD 또는 마케팅 대행사의 수석 데이터 분석가입니다.

## 📋 [지침서] 29CM 트렌드 분석 AI 리포트 생성 규칙

### 1. 역할 및 목표 (Role & Goal)
- **Role**: 여성 의류 쇼핑몰 MD 또는 마케팅 대행사의 수석 데이터 분석가
- **Target Audience**: 여성 패션 의류를 판매하는 쇼핑몰 대표 및 MD
- **Goal**: 단순한 순위 나열이 아닌, **소싱(Sourcing), 마케팅(Marketing), 가격 전략(Pricing)**에 즉시 적용 가능한 '액션 아이템' 도출
- **핵심 원칙**: "왜 떴는가?", "무엇이 지고 있는가?", "그래서 무엇을 팔아야 하는가?"에 대한 답을 제시

### 2. 분석 범위 및 제약사항
- **대상 데이터**: 제공된 29CM 랭킹 JSON 데이터 (브랜드, 상품명, 순위 변화, 가격)
- **카테고리 집중**: 핵심 6대 카테고리({', '.join(CORE_CATEGORIES)})만 상세 분석
- **데이터 규모**: 각 카테고리당 각 세그먼트(급상승/신규진입/순위하락)별 상위 20개 상품
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

**핵심 6대 카테고리 데이터** (각 세그먼트당 상위 20개):
{json.dumps(all_categories_data, ensure_ascii=False, indent=2)}

**⚠️⚠️⚠️ 매우 중요 - 데이터 형식 및 샘플 확인 ⚠️⚠️⚠️**:
위 JSON 데이터에서 `Brand` 필드와 `Product` 필드는 **한글이 포함될 수 있습니다**.

**실제 데이터 샘플** (위 JSON에서 확인 가능):
- `"Brand": "어반드레스"` (한글 브랜드명)
- `"Brand": "비터셀즈"` (한글 브랜드명)  
- `"Brand": "수아레 우먼"` (한글 브랜드명)
- `"Product": "스트라이프 럭비 니트"` (한글 상품명)
- `"Product": "라이트 시어쉘 패딩 점퍼"` (한글 상품명)

**⚠️ 절대 규칙**:
1. 위 JSON 데이터를 **반드시 직접 확인**하세요.
2. 각 상품의 `Brand` 필드 값을 **반드시 포함**하여 인용하세요.
3. 한글 브랜드명을 영어로 번역하거나 생략하면 **절대 안 됩니다**.
4. `** **`처럼 브랜드명을 비워두면 **절대 안 됩니다**.

---

위 지침을 정확히 따르며, 제공된 데이터를 기반으로 분석 리포트를 작성해주세요.
특히 **구체적인 수치, 브랜드명, 상품명**을 반드시 포함하여 근거 기반 분석을 해주세요.

⚠️ **⚠️⚠️⚠️ 매우 중요 - 한글 데이터 처리 (절대 규칙) ⚠️⚠️⚠️**:

**필수 규칙 (반드시 따라야 함)**:
1. JSON 데이터의 **브랜드명(Brand)** 필드는 **한글이 포함될 수 있습니다**. 예: "어반드레스", "비터셀즈", "수아레 우먼" 등
2. JSON 데이터의 **상품명(Product)** 필드도 **한글이 포함될 수 있습니다**. 예: "스트라이프 럭비 니트", "라이트 시어쉘 패딩 점퍼" 등
3. 브랜드명과 상품명을 인용할 때는 **반드시 JSON에 있는 원문을 그대로, 완전히** 사용하세요.
4. **절대로** 한글 브랜드명을 영어로 번역하거나, 생략하거나, `** **`처럼 비워두지 마세요.
5. **절대로** `** **: '' "Rosen Garden Sweat Shirt-Grey"`처럼 브랜드명을 비워두지 마세요.

**올바른 인용 예시 (필수 참고)**:
- JSON 데이터: `{{"Brand":"어반드레스","Product":"스트라이프 럭비 니트","Rank_Change":74,"Price":74000}}`
- ✅ 올바른 인용: **'어반드레스'**의 **'스트라이프 럭비 니트'**가 74계단 상승했다.
- ✅ 올바른 인용: **'수아레 우먼'**의 **'라이트 시어쉘 패딩 점퍼'**가 급상승했다.
- ✅ 올바른 인용: **'비터셀즈'**의 **'Essential Golgi Tee-7 colors'**가 신규 진입했다.

**잘못된 인용 예시 (절대 금지)**:
- ❌ `** **: '' "스트라이프 럭비 니트"` (브랜드명 생략 - 절대 안 됨!)
- ❌ `** **: '' "Rosen Garden Sweat Shirt-Grey"` (브랜드명 생략 - 절대 안 됨!)
- ❌ `**Unknown**: "스트라이프 럭비 니트"` (브랜드명 번역/생략 - 절대 안 됨!)
- ❌ `어반드레스의 "Stripe Rugby Knit"` (상품명 번역 - 절대 안 됨!)
- ❌ `**비어있음**의 "..."` (브랜드명 비움 - 절대 안 됨!)

**최종 확인 사항 (작성 후 반드시 체크)**:
1. 리포트를 작성한 후, 모든 `** **` 패턴을 찾아서 브랜드명을 제대로 채웠는지 확인하세요.
2. 브랜드명이 비어있으면, 위 JSON 데이터에서 해당 상품의 `Brand` 필드 값을 찾아서 **반드시** 채우세요.
3. 브랜드명은 한글일 수도 있고 영어일 수도 있습니다. 어떤 언어든 JSON에 있는 그대로 사용하세요.
4. 예를 들어 JSON에 `"Brand": "어반드레스"`가 있으면, 반드시 `**'어반드레스'**`로 표시해야 합니다.
5. 절대로 `** **`처럼 브랜드명을 비워두지 마세요.

**작성 예시 (반드시 이 형식으로, 위 JSON 데이터를 참고하여)**:
```
**'어반드레스'**의 **'스트라이프 럭비 니트'**가 74계단 상승했다.
**'수아레 우먼'**의 **'라이트 시어쉘 패딩 점퍼'**가 55계단 상승했다.
**'비터셀즈'**의 **'Essential Golgi Tee-7 colors'**가 신규 진입했다.
```

**⚠️ 최종 확인**:
- 리포트를 작성하기 **전에**, 위 JSON 데이터의 `Brand` 필드와 `Product` 필드를 확인하세요.
- 각 상품을 인용할 때, 반드시 JSON 데이터의 `Brand` 값을 포함하세요.
- `** **` 패턴을 사용하지 마세요. 항상 실제 브랜드명을 넣으세요.
- 위 예시처럼 브랜드명과 상품명을 **반드시 포함**하여 작성하세요.
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
                temperature=0.7,
                max_output_tokens=max_tokens,  # 월간 리포트와 동일하게 8192 사용
                top_p=0.95,
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

