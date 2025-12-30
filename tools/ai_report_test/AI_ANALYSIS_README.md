# AI 분석 기능 가이드

## 📋 개요

월간 리포트 스냅샷 데이터를 Google Gemini API로 분석하여 각 섹션별 AI 분석 텍스트를 생성하는 기능입니다.

## 🏗️ 프로젝트 구조

### 백엔드 (Flask)
```
ngn_wep/dashboard/
├── app.py                    # Flask 앱 진입점
├── handlers/
│   └── data_handler.py       # API 엔드포인트 (Blueprint)
├── services/                  # 비즈니스 로직
└── utils/                     # 유틸리티 함수
```

### 리포트 스냅샷 생성
```
tools/ai_report_test/
├── bq_monthly_snapshot.py    # 스냅샷 생성 메인 로직
├── ai_analyst.py             # AI 분석 모듈 (신규)
└── system_prompt_v44.txt     # System Prompt 파일 (신규)
```

## 📊 JSON 스냅샷 구조

### 최종 생성되는 JSON 구조

```json
{
  "report_meta": {
    "company_name": "piscess",
    "report_month": "2025-12",
    "period_this": {"from": "...", "to": "..."},
    "period_prev": {"from": "...", "to": "..."},
    "period_yoy": {"from": "...", "to": "..."},
    "yoy_available": {...}
  },
  "facts": {
    "mall_sales": {...},
    "meta_ads": {...},
    "ga4_traffic": {...},
    "products": {...},
    "viewitem": {...},
    "comparisons": {...},
    "forecast_next_month": {...},
    "29cm_best": {...},
    "events": {...}
  },
  "signals": {
    "attention_without_conversion_exists": true,
    "efficient_conversion_exists": false,
    "meta_ads_interpretable_monthly": true,
    "core_product_risk": false,
    "new_product_dependency": false,
    "mall_sales_mom_pct": 12.5,
    "note_if_base_small_mom": false,
    // ✅ AI 분석 필드 (신규 추가)
    "section_1_analysis": "AI 분석 텍스트...",
    "section_2_analysis": "AI 분석 텍스트...",
    "section_3_analysis": "AI 분석 텍스트...",
    "section_4_analysis": "AI 분석 텍스트...",
    "section_5_analysis": "AI 분석 텍스트...",
    "section_6_analysis": "AI 분석 텍스트...",
    "section_7_analysis": "AI 분석 텍스트...\n```json\n{...}\n```",
    "section_8_analysis": "AI 분석 텍스트...",
    "section_9_analysis": "AI 분석 텍스트..."
  }
}
```

### 섹션별 필드 매핑

| 섹션 번호 | 필드명 | 설명 |
|----------|--------|------|
| 1 | `section_1_analysis` | 지난달 매출 분석 |
| 2 | `section_2_analysis` | 주요 유입 채널 |
| 3 | `section_3_analysis` | 고객 방문 및 구매 여정 |
| 4 | `section_4_analysis` | 자사몰 베스트 상품 성과 |
| 5 | `section_5_analysis` | 시장 트렌드 확인 (29CM) |
| 6 | `section_6_analysis` | 매체 성과 및 효율 진단 |
| 7 | `section_7_analysis` | 시장 트렌드와 자사몰 비교 (JSON 비교표 포함) |
| 8 | `section_8_analysis` | 익월 목표 설정 및 시장 전망 |
| 9 | `section_9_analysis` | 데이터 기반 전략 액션 플랜 |

## 🚀 사용 방법

### 1. System Prompt 설정

`tools/ai_report_test/system_prompt_v44.txt` 파일에 System Prompt v44.0 내용을 붙여넣으세요.

### 2. 환경 변수 설정

```bash
export GEMINI_API_KEY="your-api-key-here"
export GEMINI_MODEL="gemini-2.0-flash-exp"  # 선택사항, 기본값
```

### 3. AI 분석 실행

#### 방법 1: Python 함수로 직접 호출

```python
from tools.ai_report_test.ai_analyst import generate_ai_analysis
import json

# 스냅샷 데이터 로드
with open('snapshot.json', 'r', encoding='utf-8') as f:
    snapshot_data = json.load(f)

# AI 분석 수행
snapshot_with_analysis = generate_ai_analysis(
    snapshot_data,
    system_prompt_file="tools/ai_report_test/system_prompt_v44.txt",
    sections=[1, 2, 3, 4, 5, 6, 7, 8, 9]  # 모든 섹션 분석
)

# 결과 저장
with open('snapshot_with_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(snapshot_with_analysis, f, ensure_ascii=False, indent=2)
```

#### 방법 2: CLI로 실행

```bash
# 전체 섹션 분석
python3 tools/ai_report_test/ai_analyst.py snapshot.json output.json system_prompt_v44.txt

# 특정 섹션만 분석 (코드 수정 필요)
```

#### 방법 3: 스냅샷 생성 후 자동 분석 (통합)

`bq_monthly_snapshot.py`의 `run()` 함수 끝에 추가:

```python
# AI 분석 수행 (선택사항)
if os.environ.get("ENABLE_AI_ANALYSIS") == "true":
    from tools.ai_report_test.ai_analyst import generate_ai_analysis
    out_safe = generate_ai_analysis(
        out_safe,
        system_prompt_file="tools/ai_report_test/system_prompt_v44.txt"
    )
```

### 4. GCS에서 스냅샷 로드 후 AI 분석

```python
from google.cloud import storage
import gzip
import json
from tools.ai_report_test.ai_analyst import generate_ai_analysis

# GCS에서 스냅샷 다운로드
storage_client = storage.Client()
bucket = storage_client.bucket("winged-precept-443218-v8.appspot.com")
blob = bucket.blob("ai-reports/monthly/piscess/2025-12/snapshot.json.gz")

# 압축 해제 및 로드
snapshot_bytes = blob.download_as_bytes()
snapshot_json_str = gzip.decompress(snapshot_bytes).decode('utf-8')
snapshot_data = json.loads(snapshot_json_str)

# AI 분석 수행
snapshot_with_analysis = generate_ai_analysis(
    snapshot_data,
    system_prompt_file="tools/ai_report_test/system_prompt_v44.txt"
)

# GCS에 다시 저장
snapshot_json_str = json.dumps(snapshot_with_analysis, ensure_ascii=False, indent=2)
snapshot_gzip_bytes = gzip.compress(snapshot_json_str.encode('utf-8'))
blob.upload_from_string(snapshot_gzip_bytes, content_type='application/json')
blob.content_encoding = 'gzip'
```

## 🔧 함수 상세 설명

### `generate_ai_analysis()`

**시그니처:**
```python
def generate_ai_analysis(
    snapshot_data: Dict,
    system_prompt: Optional[str] = None,
    system_prompt_file: Optional[str] = None,
    sections: Optional[List[int]] = None,
    api_key: Optional[str] = None
) -> Dict
```

**파라미터:**
- `snapshot_data`: 스냅샷 JSON 데이터 (Dict)
- `system_prompt`: System Prompt 문자열 (직접 제공)
- `system_prompt_file`: System Prompt 파일 경로
- `sections`: 분석할 섹션 번호 리스트 (기본값: [1, 2, 3, 4, 5, 6, 7, 8, 9])
- `api_key`: Gemini API 키 (기본값: 환경변수 `GEMINI_API_KEY`)

**반환값:**
- `signals` 필드에 AI 분석 텍스트가 추가된 `snapshot_data`

**에러 처리:**
- API 호출 실패 시 해당 섹션 필드에 에러 메시지 저장
- 다른 섹션은 계속 진행

### `build_section_prompt()`

각 섹션별로 적절한 프롬프트를 생성합니다. 섹션 7의 경우 JSON 비교표를 포함하도록 특별히 처리됩니다.

## 📦 의존성

```bash
pip install google-generativeai
```

또는 `requirements.txt`에 추가:
```
google-generativeai>=0.3.0
```

## ⚠️ 주의사항

1. **API 키 보안**: `GEMINI_API_KEY`는 환경변수로 관리하세요.
2. **비용 관리**: Gemini API 호출은 비용이 발생할 수 있습니다. 섹션별로 선택적으로 분석하세요.
3. **에러 처리**: API 호출 실패 시에도 스냅샷 생성은 계속 진행됩니다.
4. **System Prompt**: 반드시 `system_prompt_v44.txt`에 실제 System Prompt를 붙여넣으세요.

## ⚙️ 설정 및 최적화

### 토큰 한도 설정

`ai_analyst.py`의 `generate_ai_analysis` 함수에서 `max_output_tokens`를 설정합니다:

```python
max_output_tokens=8192  # 답변이 중간에 잘리지 않도록 토큰 한도 증량
```

- **기본값**: `8192` (한글 기준 약 12,000자 이상 지원)
- **이전 값**: `600` (너무 낮아서 답변이 중간에 잘림 발생)
- **권장**: 긴 섹션(섹션 7, 9 등)도 온전히 출력되도록 `8192` 유지

### 길이 제한 처리

- **1000자 초과 시**: 재시도하지 않고 WARN 로그만 남기고 그대로 사용
- **이유**: 내용이 잘리는 것보다 긴 응답이 더 유용함
- **로그 예시**: `⚠️ [WARN] 섹션 7 응답이 1000자 초과 (3500자). 그대로 사용합니다.`

## 🔄 통합 워크플로우

1. **스냅샷 생성**: `bq_monthly_snapshot.py` 실행
2. **AI 분석**: `ai_analyst.py` 실행 (또는 통합)
3. **GCS 저장**: 분석 결과 포함된 스냅샷 저장
4. **프론트엔드 표시**: `monthly_report.js`에서 `signals.section_X_analysis` 읽어서 표시

## 📝 변경 이력

- **2025-01-XX**: AI 분석 기능 추가
  - `ai_analyst.py` 모듈 생성
  - `signals` 필드에 `section_X_analysis` 추가
  - System Prompt 파일 템플릿 생성

