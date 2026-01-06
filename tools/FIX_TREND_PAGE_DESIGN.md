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

