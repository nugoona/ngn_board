# Trend 페이지 디자인 깨짐 및 KEYWORD 섹션 표시 문제 해결

## 문제 상황
1. Trend 페이지 디자인이 깨져서 Section 2 (KEYWORD)와 Section 3 (TRENDS)가 보이지 않음
2. 썸네일이 생성되지만 화면에 표시되지 않음
3. 세로 스크롤이 사라져서 페이지 하단으로 이동할 수 없음

## 해결 목표
1. Section 2 (KEYWORD) 섹션이 정상적으로 표시되도록 수정
2. Section 3 (TRENDS) 섹션의 썸네일이 정상적으로 표시되도록 수정
3. 페이지 스크롤이 정상적으로 작동하도록 수정
4. 부모 요소에 스타일을 강제 적용하면서 사이드바 스크롤 기능을 유지

## 작업 명령문

### 1단계: 현재 상태 확인

다음 파일들을 확인하여 현재 구현 상태를 파악하세요:

```
ngn_wep/dashboard/static/js/trend_page.js
  - renderTrendAnalysisReport() 함수 (517-578줄)
  - renderSection2AsCards() 함수 (1825-1850줄)
  - renderSection3WithTabs() 함수 (1988-2051줄)
  - renderSection3SegmentContent() 함수 (2054-2328줄)
  - parseSection2IntoMaterialAndTPO() 함수 (1579-1606줄)

ngn_wep/dashboard/templates/trend_page.html
  - .trend-section2-container 스타일 (1216-1328줄)
  - .trend-section3-container 스타일 (883-947줄)
  - .trend-analysis-sidebar-content 스타일 (729-733줄)
  - .trend-category-thumbnails 스타일 (512-521줄)
```

### 2단계: Section 2 (KEYWORD) 표시 문제 해결

**파일**: `ngn_wep/dashboard/static/js/trend_page.js`

**작업 내용**:
1. `parseSection2IntoMaterialAndTPO()` 함수에서 Material과 Mood 텍스트가 제대로 추출되는지 확인
   - `section2Text`가 비어있지 않은지 확인
   - Material 패턴과 Mood 패턴이 정확히 매칭되는지 확인
   - 디버깅 로그 추가: `console.log('[parseSection2IntoMaterialAndTPO] material:', material.length, 'mood:', mood.length)`

2. `renderSection2AsCards()` 함수 수정:
   - 함수 시작 부분에 디버깅 로그 추가: `console.log('[renderSection2AsCards] section2Data:', section2Data)`
   - Material과 Mood 카드가 모두 생성되었는지 확인
   - 카드 내용이 비어있어도 카드 자체는 표시되도록 수정 (빈 카드도 표시)

3. `renderTrendAnalysisReport()` 함수에서 Section 2 렌더링 확인:
   - `sections.section2`가 비어있지 않은지 확인
   - `section2Data.material`과 `section2Data.mood`가 존재하는지 확인
   - 디버깅 로그 추가

### 3단계: Section 3 (TRENDS) 썸네일 표시 문제 해결

**파일**: `ngn_wep/dashboard/static/js/trend_page.js`

**작업 내용**:
1. `renderSection3SegmentContent()` 함수 수정:
   - 부모 요소 스타일 적용 시 사이드바 스크롤 컨테이너는 건드리지 않도록 보완
   - 썸네일 그리드 컨테이너에 스타일을 강제 적용하되, 부모 요소의 overflow는 변경하지 않음
   - `trend-section3-content-wrapper`에는 `overflow: visible`을 적용하지 않음

2. 부모 요소 스타일 적용 로직 개선:
   ```javascript
   // 사이드바 스크롤 컨테이너는 건드리지 않음
   if (parent.classList && (
       parent.classList.contains('trend-analysis-sidebar-content') ||
       parent.classList.contains('trend-analysis-sidebar-wrapper') ||
       parent.classList.contains('trend-section3-content-wrapper')
   )) {
       // 스크롤이 필요한 컨테이너는 overflow를 건드리지 않음
       // display, visibility, opacity만 적용
   }
   ```

### 4단계: 스크롤 기능 복구

**파일**: `ngn_wep/dashboard/templates/trend_page.html`

**작업 내용**:
1. `.trend-analysis-sidebar-content` 스타일 확인:
   - `overflow-y: auto`가 유지되는지 확인
   - `max-height`가 적절히 설정되어 있는지 확인

2. 부모 요소에 `overflow: visible !important`를 강제 적용하는 JavaScript 로직 수정:
   - 사이드바 관련 컨테이너에는 overflow를 변경하지 않도록 예외 처리

### 5단계: CSS 스타일 강화

**파일**: `ngn_wep/dashboard/templates/trend_page.html`

**작업 내용**:
1. `.trend-section2-container`에 `!important` 플래그 추가:
   ```css
   .trend-section2-container {
     display: block !important;
     visibility: visible !important;
     opacity: 1 !important;
     margin-top: 32px !important;
     margin-bottom: 32px !important;
   }
   ```

2. `.trend-section3-container`에 `!important` 플래그 추가:
   ```css
   .trend-section3-container {
     display: block !important;
     visibility: visible !important;
     opacity: 1 !important;
     margin-top: 32px !important;
     margin-bottom: 24px !important;
   }
   ```

3. `.trend-section2-grid`에 `!important` 플래그 추가:
   ```css
   .trend-section2-grid {
     display: grid !important;
     grid-template-columns: repeat(2, 1fr) !important;
     gap: 24px !important;
   }
   ```

### 6단계: 디버깅 및 검증

**작업 내용**:
1. 브라우저 콘솔에서 다음 로그 확인:
   - `[renderTrendAnalysisReport] Section 분리 결과` - Section 2 길이가 0이 아닌지 확인
   - `[parseSection2IntoMaterialAndTPO]` - Material과 Mood가 추출되는지 확인
   - `[renderSection2AsCards]` - 카드가 생성되는지 확인
   - `[renderSection3SegmentContent]` - 썸네일이 추가되는지 확인

2. 브라우저 개발자 도구에서 요소 검사:
   - Section 2 컨테이너의 `offsetHeight`와 `offsetWidth` 확인
   - Section 3 컨테이너의 `offsetHeight`와 `offsetWidth` 확인
   - `getBoundingClientRect()`로 실제 렌더링 위치 확인

## 수정 우선순위

1. **최우선**: Section 2 (KEYWORD) 표시 문제 해결
   - `parseSection2IntoMaterialAndTPO()` 함수의 텍스트 추출 로직 확인
   - 빈 데이터일 경우에도 기본 카드를 표시하도록 수정

2. **두 번째**: 스크롤 기능 복구
   - 부모 요소 스타일 적용 시 사이드바 스크롤 컨테이너는 예외 처리

3. **세 번째**: Section 3 썸네일 표시 개선
   - 부모 요소 스타일 적용 로직 개선

## 예상 결과

수정 후:
- Section 2 (KEYWORD) 섹션이 정상적으로 표시됨 (Material Trend, Mood & Style 카드)
- Section 3 (TRENDS) 섹션의 썸네일이 정상적으로 표시됨
- 사이드바 스크롤이 정상적으로 작동함
- 페이지 전체 스크롤이 정상적으로 작동함

---

## 추가 작업: Section 3 카테고리별 카드 구조 확인 및 개선

### 현재 구조 확인 (이미지 기준)
이미지를 보면 다음과 같은 구조로 표시되어야 합니다:

1. **탭 영역**: 상단에 "급상승", "신규 진입", "순위 하락" 탭이 표시됨
2. **카테고리별 카드**: 선택된 탭에 따라 각 카테고리(상의, 바지 등)별로 하나의 카드가 표시됨

**각 카테고리 카드의 구조:**
```
┌─────────────────────────────────────────┐
│ [상의] (카테고리 뱃지 - 보라색)          │
├─────────────────────────────────────────┤
│ AI 요약 분석 텍스트 (카테고리별)         │
│ • 캠퍼스 로고와 빈티지 스웨트의 부상...  │
│ • 유니크한 디테일의 터틀넥 인기...       │
├─────────────────────────────────────────┤
│ [썸네일 그리드]                          │
│ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐        │
│ │상품1│ │상품2│ │상품3│ │상품4│ │상품5│    │
│ └───┘ └───┘ └───┘ └───┘ └───┘        │
│ (해당 카테고리의 썸네일들, 한 줄에 5개)   │
└─────────────────────────────────────────┘
```

**중요**: 
- 각 카테고리는 독립적인 카드로 표시되어야 함
- 한 탭에 여러 카테고리가 있으면, 각각이 별도의 카드로 표시되어야 함
- 탭 이름은 상단에만 표시되고, 각 카드에는 카테고리 이름만 표시됨

### 작업 명령문

**파일**: `ngn_wep/dashboard/static/js/trend_page.js`

**함수**: `renderSection3SegmentContent()` (2080줄부터)

**현재 상태**: 코드를 보면 이미 카테고리별로 개별 카드를 생성하고 있습니다 (2194줄부터). 이 구조는 올바르지만, 다음과 같은 문제가 있을 수 있습니다:

1. **카테고리 카드가 제대로 표시되지 않는 문제**
2. **썸네일 그리드가 표시되지 않는 문제**
3. **레이아웃이 깨지는 문제**

**작업 내용**:

1. **카테고리별 카드 구조 확인 및 수정**:
   - 현재 코드는 각 카테고리마다 `trend-category-card`를 생성하고 있음 (올바름)
   - 각 카드 내부 구조 확인:
     - 카테고리 뱃지 (`.trend-category-badge`)
     - AI 분석 텍스트 (`.trend-category-insight`)
     - 썸네일 그리드 (`.trend-category-thumbnails`)

2. **썸네일 그리드 레이아웃 개선**:
   - 한 줄에 5개씩 표시되도록 그리드 설정
   - `grid-template-columns: repeat(5, 1fr)` 또는 `repeat(auto-fill, minmax(180px, 1fr))`
   - 반응형: 모바일에서는 한 줄에 2-3개

3. **카드 간 간격 및 스타일 확인**:
   - 각 카테고리 카드가 명확히 구분되도록 `margin-bottom` 설정
   - 카드 배경색, 테두리, 그림자 확인

**확인 및 수정 사항**:

현재 코드는 이미 올바른 구조를 가지고 있지만, 다음을 확인하고 개선해야 합니다:

1. **카테고리 카드가 제대로 표시되는지 확인**:
   - `trend-category-card` 클래스가 제대로 적용되는지
   - CSS 스타일이 제대로 적용되는지
   - 카드가 화면에 보이는지 (display, visibility, opacity)

2. **썸네일 그리드 레이아웃 개선**:
   ```javascript
   // createThumbnailGridFromProducts 함수 또는 관련 부분에서
   // 그리드 컬럼 수를 5개로 설정
   const innerGrid = gridContainer.querySelector('.trend-thumbnails-grid');
   if (innerGrid) {
       innerGrid.style.cssText = 'display: grid !important; grid-template-columns: repeat(5, 1fr) !important; gap: 16px !important;';
   }
   ```

3. **카테고리 뱃지 스타일 확인**:
   - 보라색 그라데이션 배경
   - 흰색 텍스트
   - 적절한 패딩과 둥근 모서리

**썸네일 그리드 생성 함수 확인**:

기존의 `createThumbnailGridFromProducts` 함수가 제대로 작동하는지 확인하고, 필요시 다음과 같이 수정:

```javascript
// createThumbnailGridFromProducts 함수에서 그리드 컬럼 수를 5개로 설정
function createThumbnailGridFromProducts(products, segmentType) {
    if (!products || products.length === 0) return '';
    
    let gridHtml = '<div class="trend-thumbnails-grid" style="display: grid !important; grid-template-columns: repeat(5, 1fr) !important; gap: 16px !important;">';
    
    products.forEach(product => {
        gridHtml += `
            <div class="trend-thumbnail-card">
                <div class="trend-thumbnail-image-wrapper">
                    <img src="${product.thumbnail || product.image || ''}" 
                         alt="${product.title || ''}" 
                         class="trend-thumbnail-image">
                </div>
                <div class="trend-thumbnail-info">
                    <div class="trend-thumbnail-title">${product.title || ''}</div>
                    ${product.price ? `<div class="trend-thumbnail-price">${product.price}</div>` : ''}
                </div>
            </div>
        `;
    });
    
    gridHtml += '</div>';
    return gridHtml;
}
```

**CSS 스타일 확인 및 개선**:

**파일**: `ngn_wep/dashboard/templates/trend_page.html`

현재 CSS를 확인하고 다음 사항을 보완:

1. **카테고리 카드 스타일** (이미 존재하지만 확인 필요):
```css
.trend-category-card {
  background: #ffffff !important;
  border: 1px solid #E9ECEF !important;
  border-radius: 12px !important;
  padding: 24px !important;
  margin-bottom: 40px !important;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
}
```

2. **카테고리 뱃지 스타일** (보라색 그라데이션):
```css
.trend-category-badge {
  display: inline-block !important;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: #ffffff !important;
  padding: 6px 16px !important;
  border-radius: 8px !important;
  font-size: 14px !important;
  font-weight: 700 !important;
  margin-bottom: 12px !important;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.2) !important;
  width: fit-content !important;
}
```

3. **썸네일 그리드 스타일** (한 줄에 5개):
```css
.trend-thumbnails-grid {
  display: grid !important;
  grid-template-columns: repeat(5, 1fr) !important;
  gap: 16px !important;
  margin-top: 20px !important;
}

/* 반응형: 모바일에서는 2-3개 */
@media (max-width: 1200px) {
  .trend-thumbnails-grid {
    grid-template-columns: repeat(4, 1fr) !important;
  }
}

@media (max-width: 768px) {
  .trend-thumbnails-grid {
    grid-template-columns: repeat(3, 1fr) !important;
  }
}

@media (max-width: 480px) {
  .trend-thumbnails-grid {
    grid-template-columns: repeat(2, 1fr) !important;
  }
}
```

### 수정 완료 후 확인 사항

1. 탭을 선택하면 각 카테고리별로 별도의 카드가 표시되는지 확인
2. 각 카드 상단에 카테고리 뱃지(예: "상의", "바지")가 보라색 그라데이션으로 표시되는지 확인
3. 각 카드에 AI 분석 텍스트가 카테고리별로 표시되는지 확인
4. 각 카드 하단에 해당 카테고리의 썸네일이 한 줄에 5개씩 그리드로 표시되는지 확인
5. 스크롤이 정상적으로 작동하는지 확인
6. 카드 간 간격이 적절한지 확인 (margin-bottom)

