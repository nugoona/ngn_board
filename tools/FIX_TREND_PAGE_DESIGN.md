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

## 추가 작업: Section 3 탭별 카드 구조 개선

### 문제 상황
현재 Section 3는 각 카테고리(바지, 스커트 등)별로 개별 카드가 생성되어 표시되고 있습니다. 하지만 사용자가 원하는 구조는 **탭별(급상승, 신규 진입, 순위 하락)로 하나의 통합 카드**를 표시하는 것입니다.

### 목표 구조
각 탭을 선택하면 다음과 같은 구조로 표시되어야 합니다:

```
┌─────────────────────────────────────────┐
│ [급상승] (탭 이름 - 텍스트박스/헤더)       │
├─────────────────────────────────────────┤
│ AI 요약 분석 텍스트 (전체 카테고리 통합)  │
│ (모든 카테고리의 분석 내용을 하나로 통합) │
├─────────────────────────────────────────┤
│ [썸네일 그리드]                          │
│ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐        │
│ │바지│ │스커트│ │상의│ │원피스│ │니트│    │
│ └───┘ └───┘ └───┘ └───┘ └───┘        │
│ (모든 카테고리의 썸네일을 한 그룹으로)    │
└─────────────────────────────────────────┘
```

### 작업 명령문

**파일**: `ngn_wep/dashboard/static/js/trend_page.js`

**함수**: `renderSection3SegmentContent()` (2080줄부터)

**작업 내용**:

1. **구조 변경**: 카테고리별 개별 카드 생성을 제거하고, 탭별 하나의 통합 카드로 변경
   - 기존: 각 카테고리마다 `trend-category-card` 생성
   - 변경: 탭 전체를 위한 하나의 `trend-segment-card` 생성

2. **탭 이름 헤더 추가**:
   ```javascript
   // 탭 이름을 헤더로 표시
   const segmentHeader = document.createElement('div');
   segmentHeader.className = 'trend-segment-header';
   segmentHeader.textContent = segmentType === 'rising_star' ? '급상승' 
                               : segmentType === 'new_entry' ? '신규 진입' 
                               : '순위 하락';
   ```

3. **AI 분석 텍스트 통합**:
   - 각 카테고리별 텍스트를 개별 카드로 분리하지 않고
   - 모든 카테고리의 분석 텍스트를 하나로 통합하여 표시
   - 또는 각 카테고리별로 작은 섹션으로 구분하여 표시하되, 하나의 카드 안에 포함

4. **썸네일 그리드 통합**:
   - 모든 카테고리의 썸네일을 하나의 그리드로 통합
   - 각 썸네일에 카테고리 라벨 추가 (예: 상단에 작은 뱃지)
   - 그리드 레이아웃: `grid-template-columns: repeat(auto-fill, minmax(160px, 1fr))`

**수정 예시**:

```javascript
function renderSection3SegmentContent(segmentType, segmentText, container) {
    // ... 기존 텍스트 파싱 로직 유지 ...
    
    // 컨테이너 초기화
    container.innerHTML = '';
    
    // 탭별 통합 카드 컨테이너 생성 (하나의 카드)
    const segmentCard = document.createElement('div');
    segmentCard.className = 'trend-segment-card';
    
    // 1. 탭 이름 헤더
    const segmentHeader = document.createElement('div');
    segmentHeader.className = 'trend-segment-header';
    const segmentLabel = segmentType === 'rising_star' ? '급상승' 
                        : segmentType === 'new_entry' ? '신규 진입' 
                        : '순위 하락';
    segmentHeader.textContent = segmentLabel;
    segmentCard.appendChild(segmentHeader);
    
    // 2. AI 분석 텍스트 영역 (모든 카테고리 통합)
    const analysisSection = document.createElement('div');
    analysisSection.className = 'trend-segment-analysis';
    
    // 카테고리별로 분석 내용을 섹션으로 구분하여 표시
    categories.forEach(categoryName => {
        const categoryText = categoryData[categoryName];
        if (categoryText) {
            const categorySection = document.createElement('div');
            categorySection.className = 'trend-segment-category-section';
            
            const categoryTitle = document.createElement('div');
            categoryTitle.className = 'trend-segment-category-title';
            categoryTitle.textContent = categoryName;
            
            const categoryContent = document.createElement('div');
            categoryContent.className = 'trend-segment-category-content';
            categoryContent.innerHTML = categoryText;
            
            categorySection.appendChild(categoryTitle);
            categorySection.appendChild(categoryContent);
            analysisSection.appendChild(categorySection);
        }
    });
    
    segmentCard.appendChild(analysisSection);
    
    // 3. 통합 썸네일 그리드 (모든 카테고리)
    const thumbnailsSection = document.createElement('div');
    thumbnailsSection.className = 'trend-segment-thumbnails';
    
    // 모든 카테고리의 상품을 하나의 배열로 수집
    const allProducts = [];
    categories.forEach(categoryName => {
        const categoryProducts = getProductsByCategory(categoryName, segmentType);
        // 각 상품에 카테고리 정보 추가
        categoryProducts.forEach(product => {
            allProducts.push({
                ...product,
                category: categoryName
            });
        });
    });
    
    // 통합 썸네일 그리드 생성
    if (allProducts.length > 0) {
        const thumbnailGrid = createUnifiedThumbnailGrid(allProducts, segmentType);
        thumbnailsSection.innerHTML = thumbnailGrid;
    }
    
    segmentCard.appendChild(thumbnailsSection);
    container.appendChild(segmentCard);
}
```

**새로운 헬퍼 함수 추가**:

```javascript
// 통합 썸네일 그리드 생성 (모든 카테고리 포함)
function createUnifiedThumbnailGrid(products, segmentType) {
    if (!products || products.length === 0) return '';
    
    let gridHtml = '<div class="trend-thumbnails-grid">';
    
    products.forEach(product => {
        gridHtml += `
            <div class="trend-thumbnail-card" data-category="${product.category || ''}">
                <div class="trend-thumbnail-category-badge">${product.category || ''}</div>
                <div class="trend-thumbnail-image-wrapper">
                    <img src="${product.thumbnail || product.image || ''}" 
                         alt="${product.title || ''}" 
                         class="trend-thumbnail-image"
                         onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22160%22 height=%22160%22%3E%3Crect fill=%22%23f0f0f0%22 width=%22160%22 height=%22160%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22%23999%22%3ENo Image%3C/text%3E%3C/svg%3E';">
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

**CSS 스타일 추가**:

**파일**: `ngn_wep/dashboard/templates/trend_page.html`

```css
/* 탭별 통합 카드 스타일 */
.trend-segment-card {
  background: #ffffff !important;
  border: 1px solid #E9ECEF !important;
  border-radius: 16px !important;
  padding: 32px !important;
  margin-bottom: 32px !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
}

/* 탭 이름 헤더 */
.trend-segment-header {
  font-size: 24px !important;
  font-weight: 700 !important;
  color: #212529 !important;
  margin-bottom: 24px !important;
  padding-bottom: 16px !important;
  border-bottom: 2px solid #E9ECEF !important;
}

/* AI 분석 텍스트 영역 */
.trend-segment-analysis {
  margin-bottom: 32px !important;
}

.trend-segment-category-section {
  margin-bottom: 20px !important;
}

.trend-segment-category-title {
  font-size: 16px !important;
  font-weight: 600 !important;
  color: #495057 !important;
  margin-bottom: 12px !important;
  padding: 8px 12px !important;
  background: #F8F9FA !important;
  border-radius: 6px !important;
  display: inline-block !important;
}

.trend-segment-category-content {
  font-size: 14px !important;
  line-height: 1.7 !important;
  color: #495057 !important;
  padding-left: 12px !important;
}

/* 통합 썸네일 그리드 */
.trend-segment-thumbnails {
  margin-top: 32px !important;
  padding-top: 24px !important;
  border-top: 1px solid #E9ECEF !important;
}

.trend-segment-thumbnails .trend-thumbnails-grid {
  display: grid !important;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)) !important;
  gap: 20px !important;
}

/* 썸네일 카드에 카테고리 뱃지 추가 */
.trend-thumbnail-card {
  position: relative !important;
}

.trend-thumbnail-category-badge {
  position: absolute !important;
  top: 8px !important;
  left: 8px !important;
  background: rgba(102, 126, 234, 0.9) !important;
  color: #ffffff !important;
  padding: 4px 8px !important;
  border-radius: 4px !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  z-index: 10 !important;
}
```

### 수정 완료 후 확인 사항

1. 탭을 선택하면 하나의 큰 카드가 표시되는지 확인
2. 카드 상단에 탭 이름(급상승, 신규 진입, 순위 하락)이 헤더로 표시되는지 확인
3. AI 분석 텍스트가 카테고리별로 구분되어 표시되는지 확인
4. 모든 카테고리의 썸네일이 하나의 그리드로 통합되어 표시되는지 확인
5. 각 썸네일에 카테고리 뱃지가 표시되는지 확인
6. 스크롤이 정상적으로 작동하는지 확인

