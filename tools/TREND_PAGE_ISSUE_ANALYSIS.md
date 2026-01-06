# Trend 페이지 Section 2, 3 표시 문제 원인 분석

## 발견된 문제점들

### 1. 조건문 검사 문제 (심각도: 높음)

**위치**: `renderTrendAnalysisReport()` 함수 (565줄, 575줄)

**문제**:
```javascript
if (sections.section2) {  // 빈 문자열도 truthy로 평가됨!
    const section2Container = renderSection2AsCards(section2Data);
    ...
}
```

**원인**: JavaScript에서 빈 문자열(`''`)은 falsy이지만, 빈 문자열이 아닌 공백만 있는 문자열(`' '`)은 truthy입니다. 또한 section2가 빈 문자열이 아니더라도 파싱이 제대로 안되면 빈 카드가 생성될 수 있습니다.

**해결책**: 더 엄격한 검사 필요
```javascript
if (sections.section2 && sections.section2.trim().length > 0) {
    const section2Data = parseSection2IntoMaterialAndTPO(sections.section2);
    if (section2Data.material || section2Data.mood) {
        const section2Container = renderSection2AsCards(section2Data);
        ...
    }
}
```

### 2. Section 파싱 로직 문제 (심각도: 높음)

**위치**: `parseAnalysisReportSections()` 함수 (1542줄)

**문제**:
- 정규식 패턴이 실제 리포트 형식과 맞지 않을 수 있음
- Section 2가 Section 1과 Section 3 사이에 있지 않으면 파싱 실패
- Section 헤더의 정확한 형식을 모르면 매칭 실패

**원인**: 
- AI 리포트의 실제 형식이 예상과 다를 수 있음 (예: `## Section 2:` vs `## Section 2.` vs `## 섹션 2`)
- `replace()` 로직이 헤더를 제대로 제거하지 못할 수 있음

**해결책**: 
- 더 유연한 정규식 패턴 사용
- 디버깅 로그 추가하여 실제 리포트 형식 확인
- 파싱 실패 시 fallback 로직 추가

### 3. Section 2 Material/Mood 파싱 문제 (심각도: 중간)

**위치**: `parseSection2IntoMaterialAndTPO()` 함수 (1580줄)

**문제**:
- `Material` 또는 `Mood` 헤더가 정확한 형식이 아니면 추출 실패
- 헤더 패턴이 실제 리포트와 맞지 않을 수 있음

**원인**: 
- 실제 리포트에서 `Material (소재):` vs `Material:` vs 다른 형식 사용 가능
- 마크다운 형식 차이 (`**Material:**` vs `**Material (소재):**`)

**해결책**:
- 더 유연한 패턴 매칭
- 여러 패턴 시도
- 파싱 실패 시 전체 section2 텍스트를 표시하는 fallback

### 4. 빈 카드 렌더링 문제 (심각도: 중간)

**위치**: `renderSection2AsCards()` 함수 (1826줄)

**문제**:
- material과 mood가 모두 비어있어도 빈 그리드가 표시될 수 있음
- 빈 카드를 생성하지만 내용이 없어서 보이지 않을 수 있음

**원인**:
- `createSection2Card()`에서 빈 content일 때 "분석 데이터가 없습니다"를 표시하지만, 카드 자체는 여전히 생성됨

**해결책**:
- material과 mood가 모두 비어있으면 Section 2를 렌더링하지 않음

### 5. Section 3 파싱 및 렌더링 문제 (심각도: 높음)

**위치**: `parseSection3BySegment()`, `renderSection3WithTabs()`, `renderSection3SegmentContent()` 함수

**문제**:
- `parseSection3BySegment()`가 빈 객체를 반환하면 `renderSection3WithTabs()`가 빈 탭만 표시
- 카테고리 헤더 패턴(`**상의:**`)이 실제 리포트와 맞지 않으면 썸네일이 표시되지 않음
- `window.allTabsData`가 준비되지 않으면 썸네일이 표시되지 않음

**원인**:
- 여러 단계의 파싱 과정에서 어느 한 단계라도 실패하면 전체가 실패
- 비동기 데이터 로딩 타이밍 문제

**해결책**:
- 각 단계마다 fallback 로직 추가
- `window.allTabsData` 준비 상태 확인 개선
- 디버깅 로그 추가

### 6. DOM 초기화 타이밍 문제 (심각도: 낮음)

**위치**: `renderTrendAnalysisReport()` 함수 (587줄)

**문제**:
```javascript
contentElement.innerHTML = '';
contentElement.appendChild(container);
```

**원인**: 
- `innerHTML = ''`로 초기화한 직후에 appendChild를 하면, 기존에 있던 섹션들이 사라질 수 있음
- 하지만 이건 일반적으로 문제가 되지 않음 (의도된 동작)

**해결책**: 특별한 조치 불필요 (현재 로직 유지)

### 7. CSS 스타일 오버라이드 문제 (심각도: 중간)

**위치**: CSS 파일 및 인라인 스타일

**문제**:
- `!important`를 많이 사용했지만, 다른 CSS 규칙이 여전히 우선순위를 가질 수 있음
- 부모 요소의 `display: none` 또는 `height: 0` 등이 자식 요소를 숨길 수 있음

**원인**:
- CSS 특이성(specificity) 문제
- 부모 요소의 스타일 상속

**해결책**:
- 더 구체적인 CSS 선택자 사용
- 부모 요소의 스타일도 확인

## 진단을 위한 디버깅 포인트

### 1. 브라우저 콘솔에서 확인할 사항:

```javascript
// 1. analysis_report가 있는지 확인
console.log('insights:', insights);
console.log('analysis_report 길이:', insights?.analysis_report?.length);

// 2. Section 파싱 결과 확인
const sections = parseAnalysisReportSections(insights.analysis_report);
console.log('Section 1 길이:', sections.section1.length);
console.log('Section 2 길이:', sections.section2.length);
console.log('Section 3 길이:', sections.section3.length);
console.log('Section 2 내용 (첫 500자):', sections.section2.substring(0, 500));
console.log('Section 3 내용 (첫 500자):', sections.section3.substring(0, 500));

// 3. Section 2 파싱 결과 확인
const section2Data = parseSection2IntoMaterialAndTPO(sections.section2);
console.log('Material 길이:', section2Data.material.length);
console.log('Mood 길이:', section2Data.mood.length);

// 4. Section 3 파싱 결과 확인
const section3Data = parseSection3BySegment(sections.section3);
console.log('Section 3 세그먼트:', section3Data);

// 5. DOM 요소 확인
const section2Container = document.querySelector('.trend-section2-container');
const section3Container = document.querySelector('.trend-section3-container');
console.log('Section 2 DOM:', section2Container);
console.log('Section 3 DOM:', section3Container);
if (section2Container) {
    console.log('Section 2 display:', window.getComputedStyle(section2Container).display);
    console.log('Section 2 visibility:', window.getComputedStyle(section2Container).visibility);
    console.log('Section 2 offsetHeight:', section2Container.offsetHeight);
}
```

### 2. 실제 리포트 형식 확인:

AI 리포트의 실제 형식을 확인하여 파싱 패턴을 조정해야 합니다:

```javascript
// analysis_report의 실제 형식 확인
console.log('analysis_report 전체 내용:');
console.log(insights.analysis_report);

// Section 헤더 패턴 찾기
const sectionHeaders = insights.analysis_report.match(/##\s*Section\s*\d[^\n]*/gi);
console.log('발견된 Section 헤더:', sectionHeaders);
```

## 권장 해결 순서

1. **먼저**: 브라우저 콘솔에서 디버깅 포인트 확인하여 실제 문제 위치 파악
2. **1순위**: 조건문 검사 강화 (빈 문자열 체크)
3. **2순위**: Section 파싱 로직 개선 (더 유연한 패턴 매칭)
4. **3순위**: Section 2 Material/Mood 파싱 개선
5. **4순위**: 빈 카드 렌더링 방지
6. **5순위**: Section 3 파싱 및 렌더링 개선
7. **6순위**: CSS 스타일 확인 및 조정

## 즉시 적용 가능한 임시 해결책

```javascript
// renderTrendAnalysisReport() 함수 수정
function renderTrendAnalysisReport(insights, createdAtElement) {
    // ... 기존 코드 ...
    
    // Section 2 카드 레이아웃 추가 (수정)
    if (sections.section2 && sections.section2.trim().length > 0) {
        const section2Data = parseSection2IntoMaterialAndTPO(sections.section2);
        console.log('[DEBUG] Section 2 데이터:', section2Data);
        
        // material 또는 mood 중 하나라도 있으면 렌더링
        if (section2Data.material.trim() || section2Data.mood.trim()) {
            const section2Container = renderSection2AsCards(section2Data);
            if (section2Container) {
                section2Container.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; margin-top: 32px !important; margin-bottom: 32px !important;';
                container.appendChild(section2Container);
            }
        } else {
            console.warn('[DEBUG] Section 2 Material과 Mood가 모두 비어있음');
        }
    } else {
        console.warn('[DEBUG] Section 2 텍스트가 비어있음');
    }
    
    // Section 3 탭 기반 UI 추가 (수정)
    if (sections.section3 && sections.section3.trim().length > 0) {
        const section3Data = parseSection3BySegment(sections.section3);
        console.log('[DEBUG] Section 3 데이터:', section3Data);
        
        // 최소한 하나의 세그먼트라도 있으면 렌더링
        if (section3Data.rising_star.trim() || section3Data.new_entry.trim() || section3Data.rank_drop.trim()) {
            const section3Container = renderSection3WithTabs(section3Data);
            if (section3Container) {
                section3Container.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; margin-top: 32px !important; margin-bottom: 24px !important;';
                container.appendChild(section3Container);
            }
        } else {
            console.warn('[DEBUG] Section 3 세그먼트가 모두 비어있음');
        }
    } else {
        console.warn('[DEBUG] Section 3 텍스트가 비어있음');
    }
    
    // ... 기존 코드 ...
}
```

