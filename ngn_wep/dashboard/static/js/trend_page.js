/**
 * 트렌드 페이지 JavaScript (29CM / Ably 공통)
 */

// 페이지 타입 확인 (기본값: 29cm)
const PAGE_TYPE = (typeof pageType !== 'undefined' ? pageType : '29cm').toLowerCase();
const IS_ABLY = PAGE_TYPE === 'ably';

let currentTab = IS_ABLY ? "상의" : "전체";
let availableTabs = IS_ABLY ? ["상의"] : ["전체"];
let allTabsData = {}; // 모든 탭 데이터를 메모리에 저장 (비용 효율화)
let currentWeek = "";
let currentTrendType = "risingStar"; // 현재 선택된 트렌드 타입 (risingStar, newEntry, rankDrop)

// API 엔드포인트 설정
const API_ENDPOINT = IS_ABLY ? '/dashboard/trend/ably' : '/dashboard/trend';
const TABS_ENDPOINT = IS_ABLY ? '/dashboard/trend/ably/tabs' : '/dashboard/trend/tabs';

// 페이지 로드 시 초기화
$(document).ready(function() {
    loadTabs().then(() => {
        // 탭 목록을 받은 후 모든 탭 데이터를 한 번에 로드
        loadAllTabsData();
    });
    setupTrendTypeTabs();
    setupTrendAnalysisToggle();
    // 햄버거 메뉴는 common.js가 처리함
});

// 트렌드 데이터 분석 사이드바 설정
function setupTrendAnalysisToggle() {
    const toggleBtn = document.getElementById('trendAnalysisToggleBtn');
    const sidebar = document.getElementById('trendAnalysisSidebar');
    const closeBtn = document.getElementById('closeTrendAnalysisSidebarBtn');
    
    if (toggleBtn && sidebar) {
        // 사이드바 열기
        toggleBtn.addEventListener('click', function() {
            // 사이드바를 열 때 현재 주차 정보가 있으면 업데이트
            refreshTrendAnalysisTitle();
            // 분석 리포트 로드
            loadTrendAnalysisReport();
            sidebar.classList.remove('hidden');
            sidebar.classList.add('active');
            
            // Section 3는 이제 renderTrendAnalysisReport에서 탭 기반 UI로 렌더링됨
        });
        
        // 사이드바 닫기 (X 버튼)
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                sidebar.classList.remove('active');
                setTimeout(() => {
                    sidebar.classList.add('hidden');
                }, 300); // transition 시간과 동일
            });
        }
        
        // ESC 키로 사이드바 닫기
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && sidebar.classList.contains('active')) {
                sidebar.classList.remove('active');
                setTimeout(() => {
                    sidebar.classList.add('hidden');
                }, 300);
            }
        });
    }
}

// 트렌드 타입 탭 설정 (급상승, 신규진입, 순위하락)
function setupTrendTypeTabs() {
    const buttons = document.querySelectorAll('.trend-type-tab-btn');
    console.log(`[setupTrendTypeTabs] 탭 버튼 ${buttons.length}개 찾음`);
    
    buttons.forEach((btn, index) => {
        console.log(`[setupTrendTypeTabs] 버튼 ${index}: data-type="${btn.dataset.type}", 텍스트="${btn.textContent.trim()}"`);
        
        btn.addEventListener('click', function() {
            const trendType = this.dataset.type;
            console.log(`[setupTrendTypeTabs] 탭 클릭 감지: ${trendType}`);
            
            // 활성화 상태 업데이트
            document.querySelectorAll('.trend-type-tab-btn').forEach(b => {
                b.classList.remove('active');
            });
            this.classList.add('active');
            
            // 트렌드 타입 변경
            currentTrendType = trendType;
            console.log(`[setupTrendTypeTabs] currentTrendType 변경: ${currentTrendType}`);
            
            // 현재 탭 데이터 재표시
            displayCurrentTabData();
        });
    });
}

// 사용 가능한 탭 목록 로드
async function loadTabs() {
    try {
        const response = await fetch(TABS_ENDPOINT);
        const data = await response.json();
        
        if (data.status === 'success' && data.tabs) {
            availableTabs = data.tabs;
            // Ably의 경우 첫 번째 탭이 기본값이 되도록 설정
            if (IS_ABLY && availableTabs.length > 0) {
                currentTab = availableTabs[0];
            }
            renderTabs();
            return Promise.resolve();
        }
    } catch (error) {
        console.error('[ERROR] 탭 목록 로드 실패:', error);
    }
}

// 탭 렌더링
function renderTabs() {
    const tabsContainer = document.getElementById('trendTabs');
    if (!tabsContainer) return;
    
    tabsContainer.innerHTML = '';
    
    availableTabs.forEach(tabName => {
        const tabBtn = document.createElement('button');
        tabBtn.className = `trend-tab-btn ${tabName === currentTab ? 'active' : ''}`;
        tabBtn.textContent = tabName;
        tabBtn.dataset.tab = tabName;
        tabBtn.addEventListener('click', function() {
            switchTab(tabName);
        });
        tabsContainer.appendChild(tabBtn);
    });
}

/**
 * 업체 선택 확인 (월간 리포트와 동일한 방식)
 */
function getSelectedCompany() {
  const companySelect = document.getElementById("accountFilter");
  if (!companySelect) return null;
  const value = companySelect.value;
  return value && value !== "all" ? value : null;
}

/**
 * 토스트 메시지 표시 (월간 리포트와 동일한 방식)
 */
function showToast(message) {
  const existingToast = document.querySelector(".toast-message");
  if (existingToast) existingToast.remove();
  
  const toast = document.createElement("div");
  toast.className = "toast-message";
  toast.textContent = message;
  document.body.appendChild(toast);
  
  setTimeout(() => toast.classList.add("show"), 10);
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// 모든 탭 데이터를 한 번에 로드 (비용 효율화)
async function loadAllTabsData() {
    showLoading();
    
    try {
        // 업체 선택 확인 (쿼리 파라미터 또는 템플릿에서 전달된 값 사용)
        let companyName = null;
        
        // 1순위: URL 쿼리 파라미터에서 가져오기
        const urlParams = new URLSearchParams(window.location.search);
        const companyFromUrl = urlParams.get('company_name');
        if (companyFromUrl) {
            companyName = companyFromUrl.toLowerCase();
        }
        
        // 2순위: 템플릿에서 전달된 selectedCompany 사용
        if (!companyName && typeof window.selectedCompany !== 'undefined' && window.selectedCompany) {
            companyName = window.selectedCompany.toLowerCase();
        }
        
        // 3순위: accountFilter에서 가져오기 (하위 호환성, 트렌드 페이지에는 필터 UI 없음)
        if (!companyName) {
            const companyFromFilter = getSelectedCompany();
            if (companyFromFilter) {
                companyName = companyFromFilter.toLowerCase();
            }
        }
        
        // 데모 계정 제한 체크 (최우선)
        if (companyName && companyName === 'demo') {
            const message = "본 기능은 파트너사 보안 정책 및 권한 설정에 따라 데모 계정에서는 조회가 제한됩니다";
            showError(message);
            
            // 3초 후 사이트 성과 페이지로 리다이렉트
            setTimeout(() => {
                window.location.href = '/';
            }, 3000);
            return;
        }
        
        // 업체가 선택되지 않았으면 에러 표시 및 리다이렉트
        if (!companyName) {
            console.warn("[트렌드 페이지] 업체가 선택되지 않았습니다.");
            showError("업체를 먼저 선택해주세요. 사이트 성과 페이지에서 업체를 선택한 후 다시 시도해주세요.");
            
            // 3초 후 사이트 성과 페이지로 리다이렉트
            setTimeout(() => {
                window.location.href = '/';
            }, 3000);
            return;
        }
        
        console.log("[DEBUG] 선택된 업체:", companyName);
        console.log("[DEBUG] 페이지 타입:", PAGE_TYPE, "API 엔드포인트:", API_ENDPOINT);
        
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tab_names: availableTabs, // 모든 탭을 한 번에 요청
                trend_type: 'all',
                company_name: companyName // 선택된 업체 전달 (소문자로 변환됨)
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            currentWeek = data.current_week || "";
            console.log("[DEBUG] 받은 current_week:", currentWeek);
            updatePageTitle(currentWeek);
            
            // insights 데이터 저장 (분석 리포트)
            if (data.insights) {
                window.trendInsights = data.insights;
            }
            
            // 모든 탭 데이터를 메모리에 저장
            if (data.tabs_data) {
                allTabsData = data.tabs_data;
                window.allTabsData = allTabsData; // 전역으로 설정 (Section 3 썸네일용)
            } else {
                // 단일 탭 응답인 경우 (하위 호환)
                allTabsData[currentTab] = {
                    rising_star: data.rising_star || [],
                    new_entry: data.new_entry || [],
                    rank_drop: data.rank_drop || []
                };
                window.allTabsData = allTabsData; // 전역으로 설정
            }
            
            // 현재 탭 데이터 표시
            displayCurrentTabData();
            
            // Section 3는 이제 renderTrendAnalysisReport에서 탭 기반 UI로 렌더링됨
        } else {
            showError(data.message || '데이터를 불러오는데 실패했습니다.');
        }
    } catch (error) {
        console.error('[ERROR] 트렌드 데이터 로드 실패:', error);
        showError('데이터를 불러오는데 실패했습니다.');
    }
}

// 탭 전환 (클라이언트에서 즉시 처리 - API 호출 없음)
function switchTab(tabName) {
    if (currentTab === tabName) return;
    
    // 데모 계정 제한 체크
    let companyName = null;
    
    // URL 쿼리 파라미터에서 가져오기
    const urlParams = new URLSearchParams(window.location.search);
    const companyFromUrl = urlParams.get('company_name');
    if (companyFromUrl) {
        companyName = companyFromUrl.toLowerCase();
    }
    
    // 템플릿에서 전달된 selectedCompany 사용
    if (!companyName && typeof window.selectedCompany !== 'undefined' && window.selectedCompany) {
        companyName = window.selectedCompany.toLowerCase();
    }
    
    // accountFilter에서 가져오기
    if (!companyName) {
        const companyFromFilter = getSelectedCompany();
        if (companyFromFilter) {
            companyName = companyFromFilter.toLowerCase();
        }
    }
    
    if (companyName && companyName === 'demo') {
        const message = "본 기능은 파트너사 보안 정책 및 권한 설정에 따라 데모 계정에서는 조회가 제한됩니다";
        if (typeof showToast === 'function') {
            showToast(message);
        } else {
            alert(message);
        }
        return;
    }
    
    currentTab = tabName;
    
    // 탭 버튼 활성화 상태 업데이트
    document.querySelectorAll('.trend-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // 메모리에 저장된 데이터로 즉시 표시 (API 호출 없음)
    displayCurrentTabData();
}

// 현재 탭 데이터 표시 (트렌드 타입에 따라 하나의 테이블만 렌더링)
function displayCurrentTabData() {
    const tabData = allTabsData[currentTab];
    const container = document.getElementById('trendTableContent');
    
    if (!tabData || !container) {
        if (container) {
            container.innerHTML = '<div class="trend-loading">데이터를 불러오는 중입니다...</div>';
        }
        return;
    }
    
    // 현재 선택된 트렌드 타입에 따라 데이터 표시
    let data = [];
    let showRankChange = true;
    
    switch(currentTrendType) {
        case 'risingStar':
            data = tabData.rising_star || [];
            showRankChange = true;
            break;
        case 'newEntry':
            data = tabData.new_entry || [];
            showRankChange = false;
            break;
        case 'rankDrop':
            data = tabData.rank_drop || [];
            showRankChange = true;
            break;
        default:
            data = tabData.rising_star || [];
            showRankChange = true;
    }
    
    // 데이터 정렬 (순위변화 순으로 디폴트)
    if (showRankChange && currentTrendType === 'risingStar') {
        // 급상승: 순위변화 내림차순 (큰 수 먼저)
        data = [...data].sort((a, b) => {
            const changeA = a.Rank_Change !== null ? a.Rank_Change : 0;
            const changeB = b.Rank_Change !== null ? b.Rank_Change : 0;
            return changeB - changeA;
        });
    } else if (showRankChange && currentTrendType === 'rankDrop') {
        // 순위하락: Ably는 양수값이므로 내림차순 (큰 수 먼저), 29CM는 음수값이므로 오름차순 (작은 수 먼저)
        data = [...data].sort((a, b) => {
            const changeA = a.Rank_Change !== null ? a.Rank_Change : 0;
            const changeB = b.Rank_Change !== null ? b.Rank_Change : 0;
            if (IS_ABLY) {
                // Ably: 양수값이므로 내림차순 (큰 수 = 더 많이 하락)
                return changeB - changeA;
            } else {
                // 29CM: 음수값이므로 오름차순 (작은 수 = 더 많이 하락)
                return changeA - changeB;
            }
        });
    } else {
        // 신규진입: 이번주 순위 오름차순
        data = [...data].sort((a, b) => {
            const rankA = a.This_Week_Rank !== null ? a.This_Week_Rank : 999;
            const rankB = b.This_Week_Rank !== null ? b.This_Week_Rank : 999;
            return rankA - rankB;
        });
    }
    
    // 테이블 렌더링
    const tableWrapper = createTableWithPagination(data, showRankChange, currentTrendType);
    container.innerHTML = '';
    container.appendChild(tableWrapper);
}

// 페이지 제목 업데이트
// 주차에서 연/월/주 추출 헬퍼 함수
function parseWeekInfo(currentWeek) {
    if (!currentWeek) return null;
    
    const weekMatch = currentWeek.match(/(\d{4})W(\d{2})/);
    if (!weekMatch) return null;
    
    const year = parseInt(weekMatch[1]);
    const week = parseInt(weekMatch[2]);
    
    // ISO 주차를 사용하여 월 계산 (Python과 동일한 로직)
    // 1월 4일을 기준으로 첫 번째 주 목요일 찾기
    const jan4 = new Date(year, 0, 4);  // 1월 4일 (월은 0부터 시작)
    const jan4Day = jan4.getDay();  // 0=일요일, 6=토요일
    // Python weekday()는 0=월요일, 6=일요일이므로 변환 필요
    const pythonWeekday = jan4Day === 0 ? 6 : jan4Day - 1;  // JavaScript -> Python 변환
    const daysToThursday = (3 - pythonWeekday + 7) % 7;  // Python 로직과 동일
    const firstThursday = new Date(year, 0, 4 + daysToThursday);
    
    // 주차 시작일 (목요일 기준 월요일)
    const weekStartDate = new Date(firstThursday);
    weekStartDate.setDate(firstThursday.getDate() - 3 + (week - 1) * 7);
    const month = weekStartDate.getMonth() + 1;
    
    console.log("[DEBUG] 주차 계산:", { 
        currentWeek, 
        year, 
        week, 
        month, 
        weekStartDate: weekStartDate.toISOString().split('T')[0] 
    });
    
    return { year, month, week };
}

function updatePageTitle(currentWeek) {
    const titleElement = document.getElementById('trendPageTitle');
    if (titleElement && currentWeek) {
        const weekInfo = parseWeekInfo(currentWeek);
        const updateInfo = titleElement.querySelector('.trend-page-update-info');
        const updateInfoText = updateInfo ? updateInfo.outerHTML : '<span class="trend-page-update-info">매주 월요일 오전 7시5분 업데이트</span>';
        
        if (weekInfo) {
            const platformName = IS_ABLY ? 'Ably' : '29CM';
            titleElement.innerHTML = `${platformName} ${weekInfo.year}년 ${weekInfo.month}월 ${weekInfo.week}주차 트렌드 ${updateInfoText}`;
        } else {
            const platformName = IS_ABLY ? 'Ably' : '29CM';
            titleElement.innerHTML = `${platformName} ${currentWeek} 트렌드 ${updateInfoText}`;
        }
    }
    
    // 사이드바 제목도 함께 업데이트
    updateTrendAnalysisTitle(currentWeek);
}

function updateTrendAnalysisTitle(currentWeek) {
    const analysisTitleElement = document.getElementById('trendAnalysisTitle');
    if (analysisTitleElement && currentWeek) {
        const weekInfo = parseWeekInfo(currentWeek);
        const platformName = IS_ABLY ? 'Ably' : '29CM';
        const updateInfo = analysisTitleElement.querySelector('.trend-analysis-update-info');
        const updateInfoText = updateInfo ? updateInfo.outerHTML : '<span class="trend-analysis-update-info">매주 월요일 오전 7시5분 업데이트</span>';
        
        if (weekInfo) {
            analysisTitleElement.innerHTML = `${platformName} ${weekInfo.month}월 ${weekInfo.week}주차 트렌드 데이터 분석 ${updateInfoText}`;
        } else {
            analysisTitleElement.innerHTML = `${platformName} ${currentWeek} 트렌드 데이터 분석 ${updateInfoText}`;
        }
    }
}

// 사이드바가 열릴 때 현재 주차 정보 업데이트 (데이터가 이미 로드된 경우)
function refreshTrendAnalysisTitle() {
    if (currentWeek) {
        updateTrendAnalysisTitle(currentWeek);
    }
}

// 트렌드 분석 리포트 로드 및 표시
function loadTrendAnalysisReport() {
    const contentElement = document.getElementById('trendAnalysisContent');
    const createdAtElement = document.getElementById('trendAnalysisCreatedAt');
    
    if (!contentElement) return;
    
    // 이미 로드된 insights가 있으면 바로 표시
    if (window.trendInsights) {
        renderTrendAnalysisReport(window.trendInsights, createdAtElement);
        return;
    }
    
    // 로딩 상태
    contentElement.innerHTML = '<div class="trend-analysis-loading">분석 리포트를 불러오는 중...</div>';
    
    // company_name 가져오기 (URL 파라미터 또는 템플릿 변수)
    const urlParams = new URLSearchParams(window.location.search);
    let companyName = urlParams.get('company_name');
    if (!companyName && typeof window.selectedCompany !== 'undefined' && window.selectedCompany) {
        companyName = window.selectedCompany;
    }
    
    console.log('[loadTrendAnalysisReport] API 호출 시작, company_name:', companyName, 'API_ENDPOINT:', API_ENDPOINT);
    
    // API 호출로 분석 리포트 가져오기
    fetch(API_ENDPOINT, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            tab_names: Object.keys(allTabsData || {}),
            trend_type: 'all',
            company_name: companyName ? companyName.toLowerCase() : null
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('[loadTrendAnalysisReport] API 응답:', data);
        if (data.status === 'success') {
            // insights 데이터 저장
            if (data.insights) {
                window.trendInsights = data.insights;
                console.log('[loadTrendAnalysisReport] insights 저장 완료:', {
                    hasAnalysisReport: !!data.insights.analysis_report,
                    analysisReportLength: data.insights.analysis_report ? data.insights.analysis_report.length : 0
                });
            }
            
            renderTrendAnalysisReport(data.insights || {}, createdAtElement);
        } else {
            console.warn('[loadTrendAnalysisReport] API 응답 실패:', data.message || data);
            // 에러 메시지가 있어도 페이지는 표시 (빈 상태로)
            renderTrendAnalysisReport({}, createdAtElement);
        }
    })
    .catch(error => {
        console.error('[loadTrendAnalysisReport] API 호출 실패:', error);
        // 에러가 발생해도 페이지는 표시 (빈 상태로)
        renderTrendAnalysisReport({}, createdAtElement);
    });
}

// 트렌드 분석 리포트 렌더링 (마크다운 지원 + Section 3 탭 기반 UI)
function renderTrendAnalysisReport(insights, createdAtElement) {
    const contentElement = document.getElementById('trendAnalysisContent');
    if (!contentElement) return;
    
    console.log('[renderTrendAnalysisReport] insights 객체:', {
        hasInsights: !!insights,
        insightsKeys: insights ? Object.keys(insights) : [],
        hasAnalysisReport: !!(insights && insights.analysis_report),
        analysisReportLength: insights && insights.analysis_report ? insights.analysis_report.length : 0
    });
    
    const analysisText = insights ? insights.analysis_report : null;
    
    // 생성일 업데이트
    if (insights && insights.generated_at && createdAtElement) {
        try {
            const date = new Date(insights.generated_at);
            createdAtElement.textContent = `생성일: ${date.toLocaleDateString('ko-KR')} ${date.toLocaleTimeString('ko-KR', {hour: '2-digit', minute: '2-digit'})}`;
        } catch (e) {
            console.warn('생성일 파싱 실패:', e);
        }
    }
    
    // analysis_report가 없어도 페이지는 표시 (섹션이 있을 수 있음)
    if (!analysisText || !analysisText.trim()) {
        console.warn('[renderTrendAnalysisReport] analysis_report가 없거나 비어있음');
        // analysis_report가 없어도 빈 컨테이너는 생성 (섹션이 있을 수 있음)
        // 하지만 일반적으로 analysis_report가 없으면 섹션도 없으므로 메시지 표시
        const container = document.createElement('div');
        container.className = 'trend-analysis-report-container';
        container.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; width: 100% !important;';
        
        const emptyMessage = document.createElement('div');
        emptyMessage.className = 'trend-analysis-empty';
        emptyMessage.innerHTML = '<p>현재 주차의 분석 리포트가 아직 생성되지 않았거나 데이터가 없습니다.</p>';
        container.appendChild(emptyMessage);
        
        contentElement.innerHTML = '';
        contentElement.appendChild(container);
        return;
    }
    
    // Section 1, 2, 3으로 분리
    const sections = parseAnalysisReportSections(analysisText);
    console.log('[renderTrendAnalysisReport] Section 분리 결과:', {
        section1Length: sections.section1.length,
        section2Length: sections.section2.length,
        section3Length: sections.section3.length,
        section1Preview: sections.section1.substring(0, 200),
        section2Preview: sections.section2.substring(0, 200),
        section3Preview: sections.section3.substring(0, 200)
    });
    
    // Section 2와 Section 3 데이터는 렌더링 시점에 파싱 (조건부 처리)
    
    // HTML 구조 생성
    const container = document.createElement('div');
    container.className = 'trend-analysis-report-container';
    
    // Section 1 카드 레이아웃 추가
    // 자사몰 상품이 없어도 Section 1은 표시 (내용이 없을 수 있음)
    if (sections.section1) {
        const section1Container = renderSection1AsCard(sections.section1);
        if (section1Container) {
            container.appendChild(section1Container);
        } else {
            // Section 1 텍스트는 있지만 정리 후 비어있을 경우, 빈 MY BRAND 섹션 표시
            console.log('[renderTrendAnalysisReport] Section 1 컨테이너가 null이지만 Section 1 텍스트는 존재, 빈 MY BRAND 섹션 표시');
            const emptySection1Container = createEmptySection1Container();
            if (emptySection1Container) {
                container.appendChild(emptySection1Container);
            }
        }
    }
    
    // Section 2 카드 레이아웃 추가
    if (sections.section2 && sections.section2.trim().length > 0) {
        console.log('[renderTrendAnalysisReport] Section 2 파싱 시도, 길이:', sections.section2.length);
        const section2Data = parseSection2IntoMaterialAndTPO(sections.section2);
        console.log('[renderTrendAnalysisReport] Section 2 데이터:', {
            materialLength: section2Data.material.length,
            moodLength: section2Data.mood.length,
            material: section2Data.material.substring(0, 100),
            mood: section2Data.mood.substring(0, 100)
        });
        
        // material 또는 mood 중 하나라도 있으면 렌더링
        if (section2Data.material.trim() || section2Data.mood.trim()) {
            const section2Container = renderSection2AsCards(section2Data);
            if (section2Container) {
                // Section 2 컨테이너 스타일 강제 적용
                section2Container.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; margin-top: 32px !important; margin-bottom: 32px !important;';
                container.appendChild(section2Container);
                console.log('[renderTrendAnalysisReport] Section 2 컨테이너 추가 완료');
            } else {
                console.warn('[renderTrendAnalysisReport] Section 2 컨테이너가 null입니다');
            }
        } else {
            console.warn('[renderTrendAnalysisReport] Section 2 Material과 Mood가 모두 비어있음');
        }
    } else {
        console.warn('[renderTrendAnalysisReport] Section 2 텍스트가 비어있음');
    }
    
    // Section 3 탭 기반 UI 추가
    if (sections.section3 && sections.section3.trim().length > 0) {
        console.log('[renderTrendAnalysisReport] Section 3 파싱 시도, 길이:', sections.section3.length);
        const section3Data = parseSection3BySegment(sections.section3);
        console.log('[renderTrendAnalysisReport] Section 3 데이터:', {
            risingStarLength: section3Data.rising_star.length,
            newEntryLength: section3Data.new_entry.length,
            rankDropLength: section3Data.rank_drop.length
        });
        
        // 최소한 하나의 세그먼트라도 있으면 렌더링
        if (section3Data.rising_star.trim() || section3Data.new_entry.trim() || section3Data.rank_drop.trim()) {
            const section3Container = renderSection3WithTabs(section3Data);
            if (section3Container) {
                // Section 3 컨테이너 스타일 강제 적용
                section3Container.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; margin-top: 32px !important; margin-bottom: 24px !important;';
                container.appendChild(section3Container);
                console.log('[renderTrendAnalysisReport] Section 3 컨테이너 추가 완료');
            } else {
                console.warn('[renderTrendAnalysisReport] Section 3 컨테이너가 null입니다');
            }
        } else {
            console.warn('[renderTrendAnalysisReport] Section 3 세그먼트가 모두 비어있음');
        }
    } else {
        console.warn('[renderTrendAnalysisReport] Section 3 텍스트가 비어있음');
    }
    
    // 컨테이너 스타일 강제 적용
    container.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; width: 100% !important;';
    
    // 섹션이 없어도 페이지 표시 (빈 상태로라도)
    // 업체명이 없는 버킷만 안 보이게 했으므로, 여기서는 항상 표시
    contentElement.innerHTML = '';
    contentElement.appendChild(container);
    
    const sectionCount = container.children.length;
    console.log('[renderTrendAnalysisReport] 트렌드 분석 리포트 렌더링 완료, 섹션 수:', sectionCount);
    
    if (sectionCount === 0) {
        // 섹션이 없으면 안내 메시지 추가
        const emptyMessage = document.createElement('div');
        emptyMessage.className = 'trend-analysis-empty';
        emptyMessage.innerHTML = '<p>현재 주차의 분석 리포트가 아직 생성되지 않았거나 데이터가 없습니다.</p>';
        container.appendChild(emptyMessage);
    }
}

// 빈 Section 1 컨테이너 생성 (자사몰 상품이 없을 때)
function createEmptySection1Container() {
    const container = document.createElement('div');
    container.className = 'trend-section1-container';
    
    // Section 1 헤더
    const header = document.createElement('h2');
    header.className = 'trend-section1-header';
    header.textContent = 'MY BRAND';
    container.appendChild(header);
    
    // 카드 컨테이너
    const cardContainer = document.createElement('div');
    cardContainer.className = 'trend-section1-card';
    
    // 내용 영역
    const contentDiv = document.createElement('div');
    contentDiv.className = 'trend-section1-card-content';
    contentDiv.innerHTML = '<p>이번 주 베스트 랭킹에 자사몰 상품이 포함되지 않았습니다.</p>';
    
    cardContainer.appendChild(contentDiv);
    container.appendChild(cardContainer);
    
    return container;
}

// AI 리포트에서 상품명 제거하고 썸네일로 교체
function removeProductNamesAndReplaceWithThumbnails(containerElement) {
    if (!window.allTabsData) return;
    
    const markdownContent = containerElement.querySelector('.trend-analysis-text');
    if (!markdownContent) return;
    
    // 모든 상품 데이터 수집
    const allProducts = [];
    Object.keys(window.allTabsData).forEach(tabName => {
        const tabData = window.allTabsData[tabName];
        ['rising_star', 'new_entry', 'rank_drop'].forEach(segment => {
            const items = tabData[segment] || [];
            items.forEach(item => {
                const brand = item.Brand_Name || item.Brand || '';
                const product = item.Product_Name || item.Product || '';
                const thumbnail = item.thumbnail_url || '';
                const itemUrl = item.item_url || item.item_url || '';
                const rank = item.This_Week_Rank || item.Ranking || '';
                const price = item.price || item.Price || 0;
                
                if (brand && product && thumbnail) {
                    allProducts.push({
                        brand: brand.trim(),
                        product: product.trim(),
                        thumbnail: thumbnail,
                        itemUrl: itemUrl,
                        rank: rank,
                        price: price
                    });
                }
            });
        });
    });
    
    // Section 3 내에서 상품명 찾아서 썸네일로 교체
    const section3Headers = markdownContent.querySelectorAll('h2, h3');
    let section3Start = null;
    for (const header of section3Headers) {
        if (header.textContent && header.textContent.includes('Section 3')) {
            section3Start = header;
            break;
        }
    }
    
    if (!section3Start) return;
    
    // Section 3의 모든 텍스트 요소 순회
    const walker = document.createTreeWalker(
        markdownContent,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );
    
    const textNodes = [];
    let node;
    let inSection3 = false;
    let currentElement = section3Start;
    
    // Section 3 내의 모든 텍스트 노드 수집
    while (currentElement) {
        if (currentElement === section3Start) {
            inSection3 = true;
        }
        
        if (inSection3) {
            // Section 3 내의 모든 텍스트 노드에서 상품명 찾기
            const tempWalker = document.createTreeWalker(
                currentElement,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            let tempNode;
            while (tempNode = tempWalker.nextNode()) {
                if (tempNode.textContent.trim()) {
                    textNodes.push(tempNode);
                }
            }
        }
        
        // 다음 섹션으로 넘어가면 중단
        if (currentElement.tagName && (currentElement.tagName === 'H2' || currentElement.tagName === 'H3')) {
            if (currentElement !== section3Start && inSection3) {
                break;
            }
        }
        
        currentElement = currentElement.nextElementSibling;
    }
    
    // 각 텍스트 노드에서 상품명 찾아서 제거
    textNodes.forEach(textNode => {
        let text = textNode.textContent;
        let modified = false;
        
        // 각 상품에 대해 브랜드명+상품명 패턴 찾기
        allProducts.forEach(product => {
            // 다양한 패턴 매칭
            const patterns = [
                new RegExp(`\\*?\\*?${escapeRegex(product.brand)}\\s+${escapeRegex(product.product)}\\*?\\*?`, 'gi'),
                new RegExp(`\\*?\\*?${escapeRegex(product.product)}\\*?\\*?`, 'gi'),
                new RegExp(`'${escapeRegex(product.brand)}'의\\s+'${escapeRegex(product.product)}'`, 'gi'),
                new RegExp(`"${escapeRegex(product.brand)}"\\s+"${escapeRegex(product.product)}"`, 'gi'),
            ];
            
            patterns.forEach(pattern => {
                if (pattern.test(text)) {
                    // 상품명 제거 (썸네일은 이미 추가되어 있으므로 텍스트만 제거)
                    text = text.replace(pattern, '').trim();
                    modified = true;
                }
            });
        });
        
        if (modified && text.trim()) {
            textNode.textContent = text;
        } else if (modified) {
            // 텍스트가 모두 제거되면 부모 요소 제거 고려
            const parent = textNode.parentElement;
            if (parent && (parent.tagName === 'P' || parent.tagName === 'LI')) {
                const remainingText = parent.textContent.replace(textNode.textContent, '').trim();
                if (!remainingText) {
                    parent.style.display = 'none';
                }
            }
        }
    });
}

// 정규식 이스케이프
function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Section 3 썸네일 카드 그리드 렌더링 (데이터 중심 접근, 모든 세그먼트 처리)
function renderSection3Thumbnails(containerElement, analysisText) {
    // window.allTabsData가 없으면 종료
    if (!window.allTabsData || Object.keys(window.allTabsData).length === 0) {
        console.warn('[Section 3 썸네일] allTabsData가 없습니다.');
        return;
    }
    
    // DOM에서 Section 3 찾기
    const markdownContent = containerElement.querySelector('.trend-analysis-text');
    if (!markdownContent) {
        console.warn('[Section 3 썸네일] markdown-content를 찾을 수 없습니다.');
        return;
    }
    
    // 기존 썸네일 제거
    const existingThumbnails = markdownContent.querySelectorAll('.trend-category-thumbnails');
    existingThumbnails.forEach(thumb => thumb.remove());
    console.log(`[Section 3 썸네일] 기존 썸네일 ${existingThumbnails.length}개 제거 완료`);
    
    // Section 3 섹션 찾기
    const section3Headers = markdownContent.querySelectorAll('h2, h3');
    let section3Start = null;
    for (const header of section3Headers) {
        const headerText = header.textContent || '';
        if (headerText.includes('Section 3') || headerText.includes('Section3') || headerText.includes('세그먼트') || headerText.includes('Segment Deep Dive') || headerText.includes('Category Deep Dive')) {
            section3Start = header;
            break;
        }
    }
    
    if (!section3Start) {
        console.warn('[Section 3 썸네일] Section 3 헤더를 찾을 수 없습니다.');
        return;
    }
    
    // 모든 세그먼트 처리 (급상승, 신규 진입, 순위 하락)
    const segments = [
        { trendType: 'rising_star', patterns: ['급상승', 'Rising Star', '🔥'] },
        { trendType: 'new_entry', patterns: ['신규 진입', 'New Entry', '🚀'] },
        { trendType: 'rank_drop', patterns: ['순위 하락', 'Rank Drop', '📉'] }
    ];
    
    // 각 세그먼트에 대해 썸네일 추가
    segments.forEach(segment => {
        renderThumbnailsForSegment(section3Start, markdownContent, segment.trendType, segment.patterns);
    });
}

// 특정 세그먼트에 대한 썸네일 렌더링
function renderThumbnailsForSegment(section3Start, markdownContent, trendType, segmentPatterns) {
    
    // Section 3 내의 모든 요소를 배열로 변환
    let currentElement = section3Start.nextElementSibling;
    const allElements = [];
    while (currentElement) {
        // 다음 Section으로 넘어가면 중단
        if (currentElement.tagName && (currentElement.tagName === 'H2' || currentElement.tagName === 'H3')) {
            const headerText = currentElement.textContent || '';
            if (headerText.includes('Section') && !headerText.includes('Section 3')) {
                break;
            }
        }
        allElements.push(currentElement);
        currentElement = currentElement.nextElementSibling;
    }
    
    // 활성화된 세그먼트 헤더 찾기
    let segmentStartIndex = -1;
    for (let i = 0; i < allElements.length; i++) {
        const element = allElements[i];
        const textContent = (element.textContent || '').trim();
        const innerHTML = (element.innerHTML || '').trim();
        
        // 세그먼트 헤더 확인 (strong 태그 또는 h3/h4 헤더)
        const isSegmentHeader = 
            (element.tagName === 'STRONG' || element.tagName === 'H3' || element.tagName === 'H4' || 
             (element.tagName === 'P' && element.querySelector('strong'))) &&
            segmentPatterns.some(pattern => textContent.includes(pattern) || innerHTML.includes(pattern));
        
        if (isSegmentHeader) {
            segmentStartIndex = i;
            break;
        }
    }
    
    if (segmentStartIndex === -1) {
        console.warn(`[Section 3 썸네일] ${trendType} 세그먼트 헤더를 찾을 수 없습니다.`);
        return;
    }
    
    // 세그먼트 종료 지점 찾기 (다음 세그먼트 헤더 또는 Section 종료)
    let segmentEndIndex = allElements.length;
    for (let i = segmentStartIndex + 1; i < allElements.length; i++) {
        const element = allElements[i];
        const textContent = (element.textContent || '').trim();
        const innerHTML = (element.innerHTML || '').trim();
        
        // 다른 세그먼트 헤더 발견 시 종료
        const isOtherSegmentHeader = 
            (element.tagName === 'STRONG' || element.tagName === 'H3' || element.tagName === 'H4' || 
             (element.tagName === 'P' && element.querySelector('strong'))) &&
            (textContent.includes('급상승') || textContent.includes('신규 진입') || textContent.includes('순위 하락') ||
             textContent.includes('Rising Star') || textContent.includes('New Entry') || textContent.includes('Rank Drop') ||
             innerHTML.includes('🔥') || innerHTML.includes('🚀') || innerHTML.includes('📉'));
        
        if (isOtherSegmentHeader && !segmentPatterns.some(pattern => textContent.includes(pattern) || innerHTML.includes(pattern))) {
            segmentEndIndex = i;
            break;
        }
    }
    
    // 해당 세그먼트 내의 요소만 추출
    const segmentElements = allElements.slice(segmentStartIndex + 1, segmentEndIndex);
    
    // 카테고리 목록
    // Ably의 경우 allTabsData에서 실제 카테고리 목록을 가져오고, 29CM의 경우 기본 카테고리 사용
    let categories;
    if (IS_ABLY && window.allTabsData && Object.keys(window.allTabsData).length > 0) {
        categories = Object.keys(window.allTabsData).sort();
    } else {
        categories = ['상의', '바지', '스커트', '원피스', '니트웨어', '셋업'];
    }
    const processedCategories = new Set(); // 이미 처리한 카테고리 추적
    
    // 각 카테고리를 역순으로 처리 (뒤에서부터 삽입하면 인덱스가 안 꼬임)
    categories.reverse().forEach(categoryName => {
        if (processedCategories.has(categoryName)) return;
        
        // 먼저 데이터가 있는지 확인
        const categoryProducts = getProductsByCategory(categoryName, trendType);
        if (categoryProducts.length === 0) {
            console.log(`[Section 3 썸네일] ${categoryName} 카테고리 (${trendType}) 데이터 없음 - 건너뜀`);
            return;
        }
        
        // 카테고리 헤드라인 찾기 (세그먼트 내에서만)
        let foundHeader = false;
        for (let i = 0; i < segmentElements.length; i++) {
            const element = segmentElements[i];
            const textContent = (element.textContent || '').trim();
            const innerHTML = (element.innerHTML || '').trim();
            const tagName = element.tagName;
            
            // 카테고리 헤드라인 패턴 확인 (강화된 패턴 매칭)
            const isCategoryHeader = 
                // <strong>상의:</strong> 또는 **상의:**
                (textContent === `${categoryName}:` || textContent.startsWith(`${categoryName}:`)) ||
                (innerHTML.includes(`<strong>${categoryName}:</strong>`) || innerHTML.includes(`**${categoryName}:**`)) ||
                // <p> 내부의 **상의:**
                (element.tagName === 'P' && (
                    textContent.startsWith(`${categoryName}:`) ||
                    innerHTML.includes(`<strong>${categoryName}:</strong>`) ||
                    innerHTML.includes(`**${categoryName}:**`)
                )) ||
                // <strong> 태그 자체
                (element.tagName === 'STRONG' && (
                    textContent === `${categoryName}:` || 
                    textContent.endsWith(`${categoryName}:`) ||
                    textContent.startsWith(`${categoryName}:`)
                )) ||
                // <li> 내부의 강조 텍스트
                (element.tagName === 'LI' && (
                    textContent.includes(`${categoryName}:`) ||
                    innerHTML.includes(`<strong>${categoryName}:</strong>`)
                ));
            
            // 디버깅: 매칭 시도 로그 (처음 100자만)
            if (i < 10 && textContent.includes(categoryName)) {
                console.log(`[Section 3 썸네일 디버그] ${categoryName} 검색 중 - 태그: ${tagName}, 텍스트: "${textContent.substring(0, 50)}", 매칭: ${isCategoryHeader}`);
            }
            
            if (isCategoryHeader) {
                foundHeader = true;
                console.log(`[Section 3 썸네일] ${categoryName} 카테고리 헤드라인 찾음 (태그: ${tagName}, 텍스트: "${textContent.substring(0, 50)}")`);
                
                // 썸네일 카드 그리드 생성
                const thumbnailGrid = createThumbnailGridFromProducts(categoryProducts, trendType);
                console.log(`[Section 3 썸네일 디버그] ${categoryName} thumbnailGrid:`, thumbnailGrid ? `생성됨 (${thumbnailGrid.length}자)` : 'null');
                
                if (thumbnailGrid) {
                    // 헤드라인을 포함하는 문단(p 또는 li) 찾기
                    const parent = element.closest('p, li') || element.parentElement;
                    console.log(`[Section 3 썸네일 디버그] ${categoryName} parent:`, parent ? `찾음 (태그: ${parent.tagName})` : '없음');
                    
                    if (parent) {
                        // 이미 썸네일이 삽입되지 않았는지 확인 (현재 parent의 바로 다음 형제만 체크)
                        let hasThumbnail = false;
                        const nextSibling = parent.nextElementSibling;
                        if (nextSibling && nextSibling.classList && nextSibling.classList.contains('trend-category-thumbnails')) {
                            hasThumbnail = true;
                        }
                        
                        console.log(`[Section 3 썸네일 디버그] ${categoryName} hasThumbnail:`, hasThumbnail, nextSibling ? `(nextSibling: ${nextSibling.tagName}, class: ${nextSibling.className})` : '(nextSibling 없음)');
                        
                        if (!hasThumbnail) {
                            const gridContainer = document.createElement('div');
                            gridContainer.className = 'trend-category-thumbnails';
                            gridContainer.innerHTML = thumbnailGrid;
                            
                            // parent 다음에 삽입
                            if (parent.nextSibling) {
                                parent.parentNode.insertBefore(gridContainer, parent.nextSibling);
                            } else {
                                parent.parentNode.appendChild(gridContainer);
                            }
                            
                            processedCategories.add(categoryName);
                            console.log(`[Section 3 썸네일] ${categoryName} 카테고리 (${trendType})에 ${categoryProducts.length}개 썸네일 삽입 완료`);
                        } else {
                            console.log(`[Section 3 썸네일 디버그] ${categoryName} 이미 썸네일이 존재하여 삽입하지 않음`);
                        }
                    } else {
                        console.warn(`[Section 3 썸네일 디버그] ${categoryName} parent 요소를 찾을 수 없음`);
                    }
                    
                    break; // 한 카테고리는 한 번만 처리
                } else {
                    console.warn(`[Section 3 썸네일 디버그] ${categoryName} thumbnailGrid가 null입니다 (categoryProducts: ${categoryProducts.length}개)`);
                }
            }
        }
        
        if (!foundHeader) {
            console.warn(`[Section 3 썸네일] ${categoryName} 카테고리 헤드라인을 찾을 수 없음 (데이터는 ${categoryProducts.length}개 존재)`);
        }
    });
}

// 카테고리별 상품 데이터 추출 (데이터 중심)
function getProductsByCategory(categoryName, trendType) {
    console.log(`[DEBUG] [getProductsByCategory] 함수 호출 - categoryName: "${categoryName}", trendType: "${trendType}"`);
    
    if (!window.allTabsData) {
        console.warn(`[DEBUG] [getProductsByCategory] allTabsData 없음: ${categoryName}`);
        return [];
    }
    
    const products = [];
    const availableTabs = Object.keys(window.allTabsData);
    console.log(`[DEBUG] [getProductsByCategory] 사용 가능한 카테고리 목록:`, availableTabs);
    
    // 카테고리명 정규화 및 매칭 (유연한 매칭)
    let matchedTabName = null;
    
    // 정확한 매칭 시도
    if (window.allTabsData[categoryName]) {
        matchedTabName = categoryName;
        console.log(`[DEBUG] [getProductsByCategory] 정확한 매칭 성공: "${categoryName}"`);
    } else {
        console.log(`[DEBUG] [getProductsByCategory] 정확한 매칭 실패, 부분 매칭 시도 중...`);
        // 부분 매칭 시도 (예: "상의"와 "상의/하의" 등)
        const normalizedCategoryName = categoryName.trim();
        for (const tabName of availableTabs) {
            if (tabName.includes(normalizedCategoryName) || normalizedCategoryName.includes(tabName)) {
                matchedTabName = tabName;
                console.log(`[DEBUG] [getProductsByCategory] 부분 매칭 성공: "${categoryName}" → "${tabName}"`);
                break;
            }
        }
    }
    
    if (!matchedTabName) {
        console.warn(`[DEBUG] [getProductsByCategory] 매칭 실패 - "${categoryName}" 카테고리를 찾을 수 없음`);
        console.warn(`[DEBUG] [getProductsByCategory] 사용 가능한 카테고리:`, availableTabs);
        return [];
    }
    
    // 해당 카테고리의 탭 데이터 찾기
    const tabData = window.allTabsData[matchedTabName];
    if (!tabData) {
        console.warn(`[DEBUG] [getProductsByCategory] ${matchedTabName} 탭 데이터가 null 또는 undefined`);
        return [];
    }
    
    console.log(`[DEBUG] [getProductsByCategory] ${matchedTabName} 탭 데이터 발견, trendType 키 목록:`, Object.keys(tabData));
    
    // 현재 트렌드 타입에 해당하는 상품 추출
    const items = tabData[trendType] || [];
    console.log(`[DEBUG] [getProductsByCategory] ${categoryName} (${trendType}): 원본 아이템 ${items.length}개`);
    if (items.length > 0) {
        console.log(`[DEBUG] [getProductsByCategory] 첫 번째 원본 아이템 샘플:`, {
            Brand_Name: items[0].Brand_Name || items[0].Brand,
            Product_Name: items[0].Product_Name || items[0].Product,
            This_Week_Rank: items[0].This_Week_Rank || items[0].Ranking,
            Rank_Change: items[0].Rank_Change
        });
    }
    
    items.forEach((item, index) => {
        const brand = item.Brand_Name || item.Brand || '';
        const product = item.Product_Name || item.Product || '';
        const thumbnail = item.thumbnail_url || '';
        const itemUrl = item.item_url || '';
        const rank = item.This_Week_Rank || item.Ranking || '';
        const rankChange = item.Rank_Change;
        const price = item.price || item.Price || 0;
        
        if (brand && product && thumbnail) {
            products.push({
                brand: brand,
                product: product,
                thumbnail: thumbnail,
                itemUrl: itemUrl,
                rank: rank,
                rankChange: rankChange,
                price: price,
                trendType: trendType
            });
        } else {
            if (index < 3) { // 처음 3개만 로그
                console.log(`[DEBUG] [getProductsByCategory] ${categoryName} 아이템 ${index} 필터링됨 - brand: "${brand}", product: "${product}", thumbnail: "${thumbnail ? '있음' : '없음'}"`);
            }
        }
    });
    
    console.log(`[DEBUG] [getProductsByCategory] ${categoryName} (${trendType}): 필터링 후 ${products.length}개`);
    if (products.length > 0) {
        console.log(`[DEBUG] [getProductsByCategory] 필터링 후 첫 번째 상품:`, {
            brand: products[0].brand,
            product: products[0].product,
            rank: products[0].rank,
            rankChange: products[0].rankChange
        });
    }
    
    // 순위변화 기준으로 정렬 (급상승: 내림차순, 신규진입: 순위 오름차순, 순위하락: 오름차순)
    products.sort((a, b) => {
        if (trendType === 'rising_star') {
            // 급상승: 순위변화 큰 것부터
            const changeA = a.rankChange !== null && a.rankChange !== undefined ? a.rankChange : 0;
            const changeB = b.rankChange !== null && b.rankChange !== undefined ? b.rankChange : 0;
            return changeB - changeA;
        } else if (trendType === 'new_entry') {
            // 신규진입: 순위 낮은 것부터 (1위, 2위, 3위...)
            const rankA = a.rank !== null && a.rank !== undefined ? parseInt(a.rank) : 999;
            const rankB = b.rank !== null && b.rank !== undefined ? parseInt(b.rank) : 999;
            return rankA - rankB;
        } else if (trendType === 'rank_drop') {
            // 순위하락: 가장 많이 떨어진 것부터
            const changeA = a.rankChange !== null && a.rankChange !== undefined ? a.rankChange : 0;
            const changeB = b.rankChange !== null && b.rankChange !== undefined ? b.rankChange : 0;
            if (IS_ABLY) {
                // Ably: Rank_Change가 양수이므로 내림차순 (큰 수 = 가장 많이 하락)
                return changeB - changeA;
            } else {
                // 29CM: Rank_Change가 음수이므로 오름차순 (작은 수 = 가장 많이 하락, -50, -30, -10...)
                return changeA - changeB;
            }
        }
        return 0;
    });
    
    console.log(`[DEBUG] [getProductsByCategory] ${categoryName} - 정렬 완료, 전체 상품 개수: ${products.length}개`);
    if (products.length > 0) {
        console.log(`[DEBUG] [getProductsByCategory] 정렬 후 첫 번째 상품:`, {
            brand: products[0].brand,
            product: products[0].product,
            rank: products[0].rank,
            rankChange: products[0].rankChange
        });
    }
    
    // 상위 6개만 반환
    const result = products.slice(0, 6);
    console.log(`[DEBUG] [getProductsByCategory] ${categoryName} (${trendType}): 최종 반환 ${result.length}개 (상위 6개만)`);
    if (result.length > 0) {
        console.log(`[DEBUG] [getProductsByCategory] 최종 반환 첫 번째 상품:`, {
            brand: result[0].brand,
            product: result[0].product,
            rank: result[0].rank,
            rankChange: result[0].rankChange
        });
    }
    return result;
}

// (parseProductNamesFromAnalysis, findProductsInCategory 함수는 더 이상 사용하지 않음 - 데이터 중심 접근으로 대체)

// 상품 목록으로부터 썸네일 그리드 생성 (순위변화 정보 포함)
function createThumbnailGridFromProducts(products, trendType) {
    if (!products || products.length === 0) {
        return null;
    }
    
    const cardsHtml = products.map((product, index) => {
        const thumbnailUrl = product.thumbnail || '';
        const productName = product.product || '';
        const brandName = product.brand || '';
        const itemUrl = product.itemUrl || '#';
        const rank = product.rank || '';
        const rankChange = product.rankChange;
        const price = product.price || 0;
        const formattedPrice = price > 0 ? `${Math.round(price).toLocaleString()}원` : '';
        
        // 순위변화 텍스트 및 스타일 결정
        let rankChangeText = '';
        let rankChangeClass = '';
        if (trendType === 'rising_star' && rankChange !== null && rankChange !== undefined && rankChange > 0) {
            rankChangeText = `🔥 +${rankChange}위 급상승`;
            rankChangeClass = 'trend-rank-change-up';
        } else if (trendType === 'new_entry') {
            rankChangeText = `🚀 차트 신규 진입`;
            rankChangeClass = 'trend-rank-change-new';
        } else if (trendType === 'rank_drop' && rankChange !== null && rankChange !== undefined) {
            // 29CM: Rank_Change < 0 (음수) = 순위 하락
            // Ably: Rank_Change > 0 (양수) = 순위 하락
            const isRankDrop = IS_ABLY ? (rankChange > 0) : (rankChange < 0);
            if (isRankDrop) {
                rankChangeText = `📉 ${Math.abs(rankChange)}위 하락`;
                rankChangeClass = 'trend-rank-change-down';
            }
        }
        
        return `
            <div class="trend-thumbnail-card">
                <a href="${itemUrl}" target="_blank" rel="noopener noreferrer" class="trend-thumbnail-link">
                    <div class="trend-thumbnail-image-wrapper">
                        <img 
                            src="${thumbnailUrl}" 
                            alt="${productName}" 
                            class="trend-thumbnail-image"
                            loading="lazy"
                            onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'200\\' height=\\'200\\'%3E%3Crect fill=\\'%23f0f0f0\\' width=\\'200\\' height=\\'200\\'/%3E%3Ctext x=\\'50%25\\' y=\\'50%25\\' text-anchor=\\'middle\\' dy=\\'.3em\\' fill=\\'%23999\\'%3ENo Image%3C/text%3E%3C/svg%3E';"
                        >
                        ${rank ? `<div class="trend-thumbnail-rank">${rank}위</div>` : ''}
                    </div>
                    <div class="trend-thumbnail-info">
                        <div class="trend-thumbnail-brand">${brandName}</div>
                        <div class="trend-thumbnail-name" title="${productName}">${productName}</div>
                        ${rankChangeText ? `<div class="trend-thumbnail-rank-change ${rankChangeClass}">${rankChangeText}</div>` : ''}
                        ${formattedPrice ? `<div class="trend-thumbnail-price">${formattedPrice}</div>` : ''}
                    </div>
                </a>
            </div>
        `;
    }).join('');
    
    return `
        <div class="trend-thumbnails-grid">
            ${cardsHtml}
        </div>
    `;
}

// 현재 활성화된 트렌드 타입 확인
function getActiveTrendType() {
    // 전역 변수 currentTrendType를 사용하거나, DOM에서 확인
    if (currentTrendType) {
        // currentTrendType이 'risingStar', 'newEntry', 'rankDrop' 형식이므로 변환 필요
        if (currentTrendType === 'risingStar') return 'rising_star';
        if (currentTrendType === 'newEntry') return 'new_entry';
        if (currentTrendType === 'rankDrop') return 'rank_drop';
    }
    
    // 폴백: DOM에서 활성화된 탭 버튼 확인
    const activeTab = document.querySelector('.trend-type-tab-btn.active');
    if (activeTab) {
        const tabText = activeTab.textContent.trim();
        if (tabText.includes('급상승')) return 'rising_star';
        if (tabText.includes('신규 진입')) return 'new_entry';
        if (tabText.includes('순위 하락')) return 'rank_drop';
    }
    return 'rising_star'; // 기본값
}

// 썸네일 카드 그리드 생성 (사용되지 않음 - createThumbnailGridFromProducts 사용)
function createThumbnailGrid(tabName, trendType) {
    // 이 함수는 더 이상 사용되지 않지만 호환성을 위해 유지
    return null;
}

// 급상승 랭킹 테이블 렌더링
function renderRisingStarTable(data) {
    const container = document.getElementById('risingStarTable');
    if (!container) return;
    
    if (data.length === 0) {
        container.innerHTML = '<div class="trend-empty">급상승 상품이 없습니다.</div>';
        return;
    }
    
    const tableWrapper = createTableWithPagination(data, true, 'risingStar'); // true = rank_change 컬럼 표시
    container.innerHTML = '';
    container.appendChild(tableWrapper);
}

// 신규 진입 테이블 렌더링
function renderNewEntryTable(data) {
    const container = document.getElementById('newEntryTable');
    if (!container) return;
    
    if (data.length === 0) {
        container.innerHTML = '<div class="trend-empty">신규 진입 상품이 없습니다.</div>';
        return;
    }
    
    const tableWrapper = createTableWithPagination(data, false, 'newEntry'); // false = rank_change 컬럼 숨김
    container.innerHTML = '';
    container.appendChild(tableWrapper);
}

// 순위 하락 테이블 렌더링
function renderRankDropTable(data) {
    const container = document.getElementById('rankDropTable');
    if (!container) return;
    
    if (data.length === 0) {
        container.innerHTML = '<div class="trend-empty">순위 하락 상품이 없습니다.</div>';
        return;
    }
    
    const tableWrapper = createTableWithPagination(data, true, 'rankDrop'); // true = rank_change 컬럼 표시
    container.innerHTML = '';
    container.appendChild(tableWrapper);
}

// 테이블과 페이지네이션을 포함한 래퍼 생성
function createTableWithPagination(data, showRankChange, tableId) {
    const wrapper = document.createElement('div');
    wrapper.className = 'trend-table-wrapper';
    
    // 정렬 상태 관리
    let sortColumn = null;
    let sortDirection = null; // 'asc' or 'desc'
    let sortedData = [...data]; // 정렬된 데이터
    
    const table = document.createElement('table');
    table.className = 'trend-table';
    table.id = `${tableId}Table`;
    
    // 테이블 헤더
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    
    const headers = [
        { text: '랭킹', key: 'ranking', sortable: false },
        { text: '썸네일', key: 'thumbnail', sortable: false },
        { text: '브랜드', key: 'brand', sortable: true },
        { text: '상품명', key: 'product', sortable: false },
        ...(showRankChange ? [{ text: '순위변화', key: 'rank_change', sortable: true }] : []),
        { text: '이번주 순위', key: 'current_rank', sortable: true },
        { text: '지난주 순위', key: 'previous_rank', sortable: true, hideMobile: true }
    ];
    
    headers.forEach(header => {
        const th = document.createElement('th');
        
        if (header.sortable) {
            th.className = 'sortable';
            th.innerHTML = `${header.text} <span class="sort-icon">⇅</span>`;
            
            th.addEventListener('click', function() {
                // 정렬 방향 토글
                if (sortColumn === header.key) {
                    sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
                } else {
                    sortColumn = header.key;
                    sortDirection = 'asc';
                }
                
                // 데이터 정렬 (원본 데이터 기준)
                sortedData = [...data].sort((a, b) => {
                    let valueA, valueB;
                    
                    switch(header.key) {
                        case 'brand':
                            valueA = (a.Brand_Name || '').toLowerCase();
                            valueB = (b.Brand_Name || '').toLowerCase();
                            break;
                        case 'rank_change':
                            valueA = a.Rank_Change !== null ? a.Rank_Change : 0;
                            valueB = b.Rank_Change !== null ? b.Rank_Change : 0;
                            break;
                        case 'current_rank':
                            valueA = a.This_Week_Rank !== null ? a.This_Week_Rank : 999;
                            valueB = b.This_Week_Rank !== null ? b.This_Week_Rank : 999;
                            break;
                        case 'previous_rank':
                            valueA = a.Last_Week_Rank !== null ? a.Last_Week_Rank : 999;
                            valueB = b.Last_Week_Rank !== null ? b.Last_Week_Rank : 999;
                            break;
                        default:
                            return 0;
                    }
                    
                    if (valueA < valueB) return sortDirection === 'asc' ? -1 : 1;
                    if (valueA > valueB) return sortDirection === 'asc' ? 1 : -1;
                    return 0;
                });
                
                // 정렬 아이콘 업데이트
                document.querySelectorAll('.trend-table th .sort-icon').forEach(icon => {
                    icon.textContent = '⇅';
                });
                th.querySelector('.sort-icon').textContent = sortDirection === 'asc' ? '↑' : '↓';
                
                // 테이블 재렌더링
                reRenderTable();
            });
        } else {
            th.textContent = header.text;
        }
        
        if (header.hideMobile) {
            th.classList.add('hide-mobile');
        }
        headerRow.appendChild(th);
    });
    
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // 테이블 바디
    const tbody = document.createElement('tbody');
    tbody.id = `${tableId}Tbody`;
    table.appendChild(tbody);
    
    // 일반 테이블 컨테이너 (더보기 클릭 시 스크롤 활성화)
    const tableContainer = document.createElement('div');
    tableContainer.className = 'trend-table-scroll-container';
    tableContainer.style.overflowX = 'auto';
    tableContainer.style.overflowY = 'visible';
    tableContainer.style.maxHeight = 'none';
    tableContainer.appendChild(table);
    wrapper.appendChild(tableContainer);
    
    // 페이지네이션 컨테이너
    const paginationDiv = document.createElement('div');
    paginationDiv.className = 'trend-pagination-container';
    paginationDiv.id = `${tableId}Pagination`;
    wrapper.appendChild(paginationDiv);
    
    // 초기 데이터 렌더링 (4개만)
    const INITIAL_ITEMS = 4;
    let isExpanded = false;
    
    // 더보기/접기 버튼 생성 (정렬 함수에서 사용하기 위해 먼저 생성)
    let showMoreBtn = null;
    let collapseBtn = null;
    
    // 정렬 후 재렌더링 함수
    function reRenderTable() {
        tbody.innerHTML = '';
        const dataToShow = isExpanded ? sortedData : sortedData.slice(0, INITIAL_ITEMS);
        renderTableRows(dataToShow, tbody, showRankChange, tableId);
        
        // 버튼 상태 업데이트
        if (sortedData.length > INITIAL_ITEMS && showMoreBtn && collapseBtn) {
            if (isExpanded) {
                showMoreBtn.style.display = 'none';
                collapseBtn.style.display = 'inline-block';
            } else {
                showMoreBtn.style.display = 'inline-block';
                collapseBtn.style.display = 'none';
                showMoreBtn.textContent = '더보기';
            }
        }
    }
    
    if (data.length > INITIAL_ITEMS) {
        showMoreBtn = document.createElement('button');
        showMoreBtn.className = 'trend-show-more-btn';
        showMoreBtn.textContent = `더보기 (${data.length - INITIAL_ITEMS}개 더)`;
        
        collapseBtn = document.createElement('button');
        collapseBtn.className = 'trend-collapse-btn';
        collapseBtn.textContent = '접기';
        collapseBtn.style.display = 'none';
        
        showMoreBtn.addEventListener('click', function() {
            isExpanded = true;
            
            // 스크롤 컨테이너 활성화 (테이블 헤더 고정)
            tableContainer.style.overflowY = 'auto';
            tableContainer.style.maxHeight = '600px';
            tableContainer.classList.add('scroll-enabled');
            
            reRenderTable();
        });
        
        collapseBtn.addEventListener('click', function() {
            isExpanded = false;
            
            // 스크롤 컨테이너 비활성화
            tableContainer.style.overflowY = 'visible';
            tableContainer.style.maxHeight = 'none';
            tableContainer.classList.remove('scroll-enabled');
            tableContainer.scrollTop = 0;
            
            reRenderTable();
            
            // 테이블 맨 위로 스크롤
            tableContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
        
        paginationDiv.appendChild(showMoreBtn);
        paginationDiv.appendChild(collapseBtn);
    }
    
    // 초기 렌더링
    renderTableRows(sortedData.slice(0, INITIAL_ITEMS), tbody, showRankChange, tableId);
    
    return wrapper;
}

// 테이블 행 렌더링
function renderTableRows(items, tbody, showRankChange, tableId) {
    const isNewEntry = tableId === 'newEntry'; // 신규진입 테이블인지 확인
    
    items.forEach((item, index) => {
        const row = document.createElement('tr');
        
        // Ranking
        const tdRanking = document.createElement('td');
        tdRanking.textContent = item.Ranking || `${index + 1}위`;
        row.appendChild(tdRanking);
        
        // Thumbnail (클릭 가능, 여백 없음)
        const tdThumbnail = document.createElement('td');
        tdThumbnail.className = 'trend-thumbnail-cell';
        if (item.thumbnail_url) {
            const imgLink = document.createElement('a');
            imgLink.href = item.item_url || '#';
            imgLink.target = '_blank';
            imgLink.rel = 'noopener noreferrer';
            
            const img = document.createElement('img');
            img.src = item.thumbnail_url;
            img.alt = item.Product_Name || '';
            img.className = 'trend-thumbnail';
            img.style.display = 'block';
            img.style.margin = '0';
            img.style.padding = '0';
            img.onerror = function() {
                this.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIwIiBoZWlnaHQ9IjEyMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48L3N2Zz4=';
            };
            
            imgLink.appendChild(img);
            tdThumbnail.appendChild(imgLink);
        } else {
            tdThumbnail.textContent = '-';
        }
        row.appendChild(tdThumbnail);
        
        // Brand
        const tdBrand = document.createElement('td');
        tdBrand.textContent = item.Brand_Name || '-';
        row.appendChild(tdBrand);
        
        // Product (줄바꿈 허용)
        const tdProduct = document.createElement('td');
        let productName = item.Product_Name || '-';
        // Ably의 경우 상품명이 길면 일정 길이로 제한하고 "..." 추가
        if (IS_ABLY && productName !== '-') {
            const MAX_PRODUCT_NAME_LENGTH = 50; // 최대 길이
            if (productName.length > MAX_PRODUCT_NAME_LENGTH) {
                productName = productName.substring(0, MAX_PRODUCT_NAME_LENGTH) + '...';
            }
        }
        tdProduct.textContent = productName;
        if (item.Product_Name && item.Product_Name.length > 50) {
            tdProduct.setAttribute('title', item.Product_Name); // 전체 상품명을 툴팁으로 표시
        }
        row.appendChild(tdProduct);
        
        // Rank Change (조건부)
        if (showRankChange) {
            const tdRankChange = document.createElement('td');
            tdRankChange.className = 'trend-rank-number';
            if (item.Rank_Change !== null && item.Rank_Change !== undefined) {
                const changeValue = item.Rank_Change;
                // 29CM: Rank_Change > 0 = 순위 상승, Rank_Change < 0 = 순위 하락
                // Ably: Rank_Change > 0 = 순위 하락 (양수값), Rank_Change < 0 = 순위 상승 (음수값)
                // 하지만 Ably의 경우 rankDrop 탭에서는 항상 양수값이므로 하락으로 표시
                let isRising;
                if (tableId === 'rankDrop') {
                    // 순위 하락 탭: 항상 하락으로 표시
                    isRising = false;
                } else if (tableId === 'risingStar') {
                    // 급상승 탭: 항상 상승으로 표시
                    isRising = true;
                } else {
                    // 기타: 29CM 방식 (양수=상승, 음수=하락)
                    isRising = changeValue > 0;
                }
                const changeDiv = document.createElement('div');
                changeDiv.className = `trend-rank-change ${isRising ? 'up' : 'down'}`;
                
                const icon = document.createElement('span');
                icon.className = 'trend-rank-change-icon';
                icon.textContent = isRising ? '▲' : '▼';
                
                const value = document.createElement('span');
                value.textContent = Math.abs(changeValue);
                value.style.fontSize = '22px';
                value.style.fontWeight = '700';
                
                changeDiv.appendChild(icon);
                changeDiv.appendChild(value);
                tdRankChange.appendChild(changeDiv);
            } else {
                tdRankChange.textContent = '-';
            }
            row.appendChild(tdRankChange);
        }
        
        // Current Rank (숫자 크게)
        const tdCurrentRank = document.createElement('td');
        tdCurrentRank.className = 'trend-rank-number';
        tdCurrentRank.style.fontSize = '22px';
        tdCurrentRank.style.fontWeight = '700';
        tdCurrentRank.textContent = item.This_Week_Rank !== null && item.This_Week_Rank !== undefined ? item.This_Week_Rank : '-';
        row.appendChild(tdCurrentRank);
        
        // Previous Rank (숫자 크게, 신규진입은 항상 '순위없음')
        const tdPreviousRank = document.createElement('td');
        tdPreviousRank.className = 'trend-rank-number hide-mobile';
        tdPreviousRank.style.fontSize = '22px';
        tdPreviousRank.style.fontWeight = '700';
        if (isNewEntry || item.Last_Week_Rank === null || item.Last_Week_Rank === undefined) {
            tdPreviousRank.textContent = '순위없음';
        } else {
            tdPreviousRank.textContent = item.Last_Week_Rank;
        }
        row.appendChild(tdPreviousRank);
        
        tbody.appendChild(row);
    });
}

// 로딩 상태 표시
function showLoading() {
    ['risingStarTable', 'newEntryTable', 'rankDropTable'].forEach(id => {
        const container = document.getElementById(id);
        if (container) {
            container.innerHTML = '<div class="trend-loading">데이터를 불러오는 중...</div>';
        }
    });
}

// 에러 표시
function showError(message) {
    ['risingStarTable', 'newEntryTable', 'rankDropTable'].forEach(id => {
        const container = document.getElementById(id);
        if (container) {
            container.innerHTML = `<div class="trend-error">${message}</div>`;
        }
    });
}

// ============================================
// Section 3 탭 기반 UI (옵션 2)
// ============================================

// AI 리포트 텍스트를 Section 1, 2, 3으로 분리
function parseAnalysisReportSections(analysisText) {
    if (!analysisText || !analysisText.trim()) {
        return { section1: '', section2: '', section3: '' };
    }
    
    // Section 헤더 패턴 찾기
    const section1Pattern = /(?:^|\n)##\s*Section\s*1[\.\s]|(?:^|\n)##\s*섹션\s*1[\.\s]/i;
    const section2Pattern = /(?:^|\n)##\s*Section\s*2[\.\s]|(?:^|\n)##\s*섹션\s*2[\.\s]/i;
    const section3Pattern = /(?:^|\n)##\s*Section\s*3[\.\s]|(?:^|\n)##\s*섹션\s*3[\.\s]|(?:^|\n)##\s*Section\s*3[\.\s]*Segment/i;
    
    let section1 = '';
    let section2 = '';
    let section3 = '';
    
    const section1Match = analysisText.search(section1Pattern);
    const section2Match = analysisText.search(section2Pattern);
    const section3Match = analysisText.search(section3Pattern);
    
    if (section1Match >= 0 && section2Match >= 0) {
        section1 = analysisText.substring(section1Match, section2Match).replace(/^[\s\S]*?##\s*Section\s*\d[\.\s]*/i, '').trim();
    } else if (section1Match >= 0) {
        section1 = analysisText.substring(section1Match).replace(/^[\s\S]*?##\s*Section\s*\d[\.\s]*/i, '').trim();
    }
    
    if (section2Match >= 0 && section3Match >= 0) {
        section2 = analysisText.substring(section2Match, section3Match).replace(/^[\s\S]*?##\s*Section\s*\d[\.\s]*/i, '').trim();
    } else if (section2Match >= 0 && section1Match >= 0) {
        section2 = analysisText.substring(section2Match).replace(/^[\s\S]*?##\s*Section\s*\d[\.\s]*/i, '').trim();
    }
    
    if (section3Match >= 0) {
        section3 = analysisText.substring(section3Match).replace(/^[\s\S]*?##\s*Section\s*\d[\.\s]*/i, '').trim();
    }
    
    return { section1, section2, section3 };
}

// Section 2 텍스트를 Material과 TPO로 파싱
function parseSection2IntoMaterialAndTPO(section2Text) {
    if (!section2Text || !section2Text.trim()) {
        return { material: '', tpo: '' };
    }
    
    // Material과 Mood (무드 & 스타일) 헤더 찾기
    const materialPattern = /\*\*Material\s*\(소재\):\*\*|\*\*Material:\*\*/i;
    const moodPattern = /\*\*Mood\s*\(무드\s*&\s*스타일\):\*\*|\*\*Mood\s*\(무드\s*&amp;\s*스타일\):\*\*|\*\*Mood:\*\*/i;
    const pricePattern = /\*\*Price\s*\(가격\):\*\*/i;
    
    const materialMatch = section2Text.search(materialPattern);
    const moodMatch = section2Text.search(moodPattern);
    const priceMatch = section2Text.search(pricePattern);
    
    let material = '';
    let mood = '';
    
    // Material 추출
    if (materialMatch >= 0) {
        const endIndex = moodMatch >= 0 ? moodMatch : (priceMatch >= 0 ? priceMatch : section2Text.length);
        material = section2Text.substring(materialMatch, endIndex)
            .replace(/^\*\*Material\s*\(소재\):\*\*/i, '')
            .replace(/^\*\*Material:\*\*/i, '')
            .trim();
    }
    
    // Mood 추출
    if (moodMatch >= 0) {
        const endIndex = priceMatch >= 0 ? priceMatch : section2Text.length;
        mood = section2Text.substring(moodMatch, endIndex)
            .replace(/^\*\*Mood\s*\(무드\s*&\s*스타일\):\*\*/i, '')
            .replace(/^\*\*Mood\s*\(무드\s*&amp;\s*스타일\):\*\*/i, '')
            .replace(/^\*\*Mood:\*\*/i, '')
            .trim();
    }
    
    return { material, mood };
}

// Section 1을 카드 레이아웃으로 렌더링 (Section 2 스타일 참고)
function renderSection1AsCard(section1Text) {
    if (!section1Text || !section1Text.trim()) {
        return null;
    }
    
    // 불필요한 텍스트 제거 (제목, 서두 등)
    let cleanedText = section1Text
        .replace(/^[\s\S]*?##\s*Section\s*1[^#]*/i, '')
        .replace(/제공된 데이터 전체를 스캔하여[^가-힣]*브랜드의 상품이[^가-힣]*포함되어 있는지 확인하세요[.\s]*/gi, '')
        .replace(/\*\*데이터에 자사몰 상품이 있는 경우:\*\*[\s\n]*/gi, '')
        .replace(/\*\*데이터에 자사몰 상품이 없는 경우:\*\*[\s\n]*/gi, '')
        .replace(/금주 랭킹 데이터에 자사몰 상품이 포함되지 않았습니다[.\s]*/gi, '')
        .replace(/이번 주 데이터에 자사몰 상품이 포함되지 않았습니다[.\s]*/gi, '')
        .trim();
    
    // 텍스트가 비어있어도 기본 메시지와 함께 표시
    // (자사몰 상품이 없어도 MY BRAND 섹션은 표시되도록)
    if (!cleanedText || cleanedText.length === 0) {
        // 빈 텍스트일 때는 기본 메시지만 표시하되 null을 반환하지 않음
        cleanedText = '이번 주 베스트 랭킹에 자사몰 상품이 포함되지 않았습니다.';
    }
    
    const container = document.createElement('div');
    container.className = 'trend-section1-container';
    
    // Section 1 헤더
    const header = document.createElement('h2');
    header.className = 'trend-section1-header';
    header.textContent = 'MY BRAND';
    container.appendChild(header);
    
    // 카드 컨테이너
    const cardContainer = document.createElement('div');
    cardContainer.className = 'trend-section1-card';
    
    // 내용 영역
    const contentDiv = document.createElement('div');
    contentDiv.className = 'trend-section1-card-content';
    
    // 마크다운을 HTML로 변환
    if (typeof marked !== 'undefined') {
        try {
            marked.setOptions({
                breaks: true,
                gfm: false
            });
            
            const markdownHtml = marked.parse(cleanedText);
            
            if (typeof DOMPurify !== 'undefined') {
                contentDiv.innerHTML = DOMPurify.sanitize(markdownHtml, {
                    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li'],
                    ALLOWED_ATTR: []
                });
            } else {
                contentDiv.innerHTML = markdownHtml;
            }
        } catch (e) {
            console.warn("[Section 1] 마크다운 변환 실패:", e);
            contentDiv.innerHTML = cleanedText.replace(/\n/g, '<br>');
        }
    } else {
        contentDiv.innerHTML = cleanedText.replace(/\n/g, '<br>');
    }
    
    // 썸네일 그리드 컨테이너 (자사몰 상품용)
    const thumbnailContainer = document.createElement('div');
    thumbnailContainer.className = 'trend-section1-thumbnails';
    
    // 자사몰 상품 찾아서 썸네일 추가
    const addCompanyThumbnails = () => {
        if (window.allTabsData && Object.keys(window.allTabsData).length > 0) {
            const companyProducts = getCompanyProducts();
            if (companyProducts.length > 0) {
                // 급상승 상품이 있으면 우선 표시, 없으면 첫 번째 상품
                const risingProducts = companyProducts.filter(p => p.trendType === 'rising_star');
                const productsToShow = risingProducts.length > 0 ? risingProducts : companyProducts.slice(0, 1);
                
                const thumbnailGrid = createThumbnailGridFromProducts(productsToShow, productsToShow[0]?.trendType || 'rising_star');
                if (thumbnailGrid) {
                    thumbnailContainer.innerHTML = thumbnailGrid;
                }
            }
        } else {
            // allTabsData가 없으면 재시도
            const retryCount = (addCompanyThumbnails.retryCount || 0) + 1;
            addCompanyThumbnails.retryCount = retryCount;
            
            if (retryCount < 50) {
                setTimeout(addCompanyThumbnails, 100);
            }
        }
    };
    
    // 썸네일 추가 시도
    setTimeout(addCompanyThumbnails, 100);
    
    // 카드에 내용과 썸네일 추가
    cardContainer.appendChild(contentDiv);
    cardContainer.appendChild(thumbnailContainer);
    container.appendChild(cardContainer);
    
    return container;
}

// 자사몰 상품 찾기 (allTabsData에서 브랜드명으로 필터링)
// ⚠️ 보안 중요: company_name을 정확히 확인하고, 해당 업체의 브랜드만 필터링해야 함
function getCompanyProducts() {
    if (!window.allTabsData || Object.keys(window.allTabsData).length === 0) {
        return [];
    }
    
    // company_name 가져오기 (URL 파라미터 또는 템플릿 변수)
    const urlParams = new URLSearchParams(window.location.search);
    const companyName = urlParams.get('company_name') || (typeof window.selectedCompany !== 'undefined' ? window.selectedCompany : '');
    
    // ⚠️ 보안: company_name이 없거나 비어있으면 빈 배열 반환 (잘못된 업체 정보 사용 방지)
    if (!companyName || companyName.trim() === '') {
        console.warn('[getCompanyProducts] ⚠️ company_name이 없습니다. 자사몰 상품을 표시하지 않습니다.');
        return [];
    }
    
    const companyNameLower = companyName.toLowerCase().trim();
    
    // 데모 계정인 경우 자사몰 상품 반환하지 않음 (보안)
    if (companyNameLower === 'demo') {
        return [];
    }
    
    // ⚠️ 보안 중요: 하드코딩된 매핑 사용 (백엔드 API에서 가져오는 것이 이상적이지만, 
    // 프론트엔드에서 보안상 안전한 방법으로 처리)
    // 매핑에 없는 업체는 빈 배열 반환 (다른 업체 브랜드가 표시되는 것을 방지)
    const brandMapping = {
        'piscess': ['파이시스', 'PISCESS', 'piscess', 'Piscess'],
        'somewherebutter': ['썸웨어버터', 'Somewhere Butter', 'SOMEWHERE BUTTER', 'somewherebutter', 'SomewhereButter'],
        'demo': [] // 데모는 이미 위에서 처리됨
    };
    
    // ⚠️ 보안: 매핑에 없는 업체는 반드시 빈 배열 반환
    // 다른 업체의 브랜드(예: 파이시스)가 잘못 표시되는 것을 방지
    if (!brandMapping.hasOwnProperty(companyNameLower)) {
        console.warn(`[getCompanyProducts] ⚠️ 브랜드 매핑에 없는 업체입니다: "${companyName}". 자사몰 상품을 표시하지 않습니다.`);
        return [];
    }
    
    const targetBrands = brandMapping[companyNameLower];
    
    // ⚠️ 보안: targetBrands가 빈 배열이면 빈 배열 반환
    if (!targetBrands || targetBrands.length === 0) {
        console.warn(`[getCompanyProducts] ⚠️ 브랜드 목록이 비어있습니다: "${companyName}"`);
        return [];
    }
    
    const products = [];
    
    try {
        // allTabsData가 존재하는지 확인
        if (!window.allTabsData || typeof window.allTabsData !== 'object') {
            console.warn('[getCompanyProducts] window.allTabsData가 없거나 유효하지 않습니다.');
            return [];
        }
        
        // 모든 카테고리와 세그먼트를 순회 (변수명을 catName으로 명확히 지정)
        const allCategoryNames = Object.keys(window.allTabsData);
        console.log(`[DEBUG] [getCompanyProducts] 처리할 카테고리 개수: ${allCategoryNames.length}개`, allCategoryNames);
        
        allCategoryNames.forEach((catName) => {
            try {
                const tabData = window.allTabsData[catName];
                if (!tabData || typeof tabData !== 'object') {
                    return; // tabData가 없거나 유효하지 않으면 스킵
                }
                
                ['rising_star', 'new_entry', 'rank_drop'].forEach((trendType) => {
                    try {
                        const items = tabData[trendType] || [];
                        if (!Array.isArray(items)) {
                            return; // items가 배열이 아니면 스킵
                        }
                        
                        items.forEach((item) => {
                            try {
                                const brand = item.Brand_Name || item.Brand || '';
                                const product = item.Product_Name || item.Product || '';
                                const thumbnail = item.thumbnail_url || '';
                                const itemUrl = item.item_url || '';
                                const rank = item.This_Week_Rank || item.Ranking || '';
                                const rankChange = item.Rank_Change;
                                const price = item.price || item.Price || 0;
                                
                                // 브랜드명 매칭 (대소문자 무시, 공백 무시)
                                const brandMatch = targetBrands.some((targetBrand) => 
                                    brand.trim().toLowerCase().includes(targetBrand.toLowerCase().trim()) ||
                                    targetBrand.toLowerCase().trim().includes(brand.trim().toLowerCase())
                                );
                                
                                if (brandMatch && brand && product && thumbnail) {
                                    products.push({
                                        brand: brand,
                                        product: product,
                                        thumbnail: thumbnail,
                                        itemUrl: itemUrl,
                                        rank: rank,
                                        rankChange: rankChange,
                                        price: price,
                                        trendType: trendType,
                                        category: catName  // catName 사용
                                    });
                                }
                            } catch (itemError) {
                                console.warn(`[getCompanyProducts] 아이템 처리 중 에러 (무시하고 계속):`, itemError);
                            }
                        });
                    } catch (trendTypeError) {
                        console.warn(`[getCompanyProducts] trendType 처리 중 에러 (무시하고 계속):`, trendTypeError);
                    }
                });
            } catch (categoryError) {
                console.warn(`[getCompanyProducts] 카테고리 "${catName}" 처리 중 에러 (무시하고 계속):`, categoryError);
            }
        });
        
        // 순위변화 기준으로 정렬 (급상승 우선)
        products.sort((a, b) => {
            if (a.trendType === 'rising_star' && b.trendType !== 'rising_star') return -1;
            if (a.trendType !== 'rising_star' && b.trendType === 'rising_star') return 1;
            
            if (a.rankChange !== null && b.rankChange !== null) {
                return Math.abs(b.rankChange) - Math.abs(a.rankChange);
            }
            
            return 0;
        });
        
        console.log(`[DEBUG] [getCompanyProducts] ${companyName} - 최종 반환 상품 개수: ${products.length}개`);
        if (products.length > 0) {
            console.log(`[DEBUG] [getCompanyProducts] 정렬 후 첫 번째 상품:`, {
                brand: products[0].brand,
                product: products[0].product,
                rank: products[0].rank,
                rankChange: products[0].rankChange,
                category: products[0].category
            });
        }
        
        return products;
    } catch (e) {
        console.error('[getCompanyProducts] 에러 발생 (빈 배열 반환):', e);
        console.error('[getCompanyProducts] 에러 스택:', e.stack);
        return [];
    }
}

// Section 2를 2열 카드 레이아웃으로 렌더링
function renderSection2AsCards(section2Data) {
    const container = document.createElement('div');
    container.className = 'trend-section2-container';
    container.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; margin-top: 32px !important; margin-bottom: 32px !important;';
    
    // Section 2 헤더
    const header = document.createElement('h2');
    header.className = 'trend-section2-header';
    header.textContent = 'KEYWORD';
    header.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important;';
    container.appendChild(header);
    
    // 2열 그리드 컨테이너
    const gridContainer = document.createElement('div');
    gridContainer.className = 'trend-section2-grid';
    gridContainer.style.cssText = 'display: grid !important; visibility: visible !important; opacity: 1 !important; grid-template-columns: repeat(2, 1fr) !important; gap: 24px !important; margin-bottom: 32px !important;';
    
    // Material 카드
    const materialCard = createSection2Card('🧶', 'Material Trend', '소재 트렌드', section2Data.material);
    if (materialCard) {
        materialCard.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important;';
        gridContainer.appendChild(materialCard);
    }
    
    // Mood 카드
    const moodCard = createSection2Card('✨', 'Mood & Style', '무드 & 스타일', section2Data.mood);
    if (moodCard) {
        moodCard.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important;';
        gridContainer.appendChild(moodCard);
    }
    
    container.appendChild(gridContainer);
    
    return container;
}

// Section 2 카드 생성
function createSection2Card(icon, titleEn, titleKo, content) {
    const card = document.createElement('div');
    card.className = 'trend-section2-card';
    
    // 아이콘 + 제목 헤더
    const header = document.createElement('div');
    header.className = 'trend-section2-card-header';
    
    const iconSpan = document.createElement('span');
    iconSpan.className = 'trend-section2-card-icon';
    iconSpan.textContent = icon;
    
    const title = document.createElement('h3');
    title.className = 'trend-section2-card-title';
    title.innerHTML = `<span class="title-en">${titleEn}</span> <span class="title-ko">${titleKo}</span>`;
    
    header.appendChild(iconSpan);
    header.appendChild(title);
    card.appendChild(header);
    
    // 내용 영역
    const contentDiv = document.createElement('div');
    contentDiv.className = 'trend-section2-card-content';
    
    if (content && content.trim()) {
        // 텍스트 전처리: \n을 실제 줄바꿈으로 변환, 리터럴 \n 제거
        let processedContent = content
            .replace(/\\n/g, '\n')  // 리터럴 \n을 실제 줄바꿈으로
            .replace(/\r\n/g, '\n')  // Windows 줄바꿈 정규화
            .replace(/\r/g, '\n')    // Mac 줄바꿈 정규화
            .trim();
        
        // 텍스트 요약 로직 적용 (가독성 향상)
        let summarizedContent = processedContent;
        
        // 불릿 포인트(- 또는 * 로 시작하는 줄) 추출 (개선된 패턴)
        // \n* 또는 줄 시작의 * 패턴도 포함
        const bulletPattern = /(?:^|\n)[\s]*[-*•]\s+(.+?)(?=\n(?:[\s]*[-*•]|$)|\n\s*\n|$)/gs;
        const bullets = [];
        let match;
        
        while ((match = bulletPattern.exec(processedContent)) !== null) {
            const bulletText = match[1].trim();
            if (bulletText.length > 0) {
                bullets.push(bulletText);
            }
        }
        
        // 불렛 포인트 패턴이 매칭되지 않았을 때, 수동으로 * 또는 - 로 시작하는 줄 찾기
        if (bullets.length === 0) {
            const lines = processedContent.split('\n');
            for (const line of lines) {
                const trimmedLine = line.trim();
                // * 또는 - 로 시작하고, 그 다음에 공백이 오는 경우
                if ((trimmedLine.startsWith('*') || trimmedLine.startsWith('-')) && trimmedLine.length > 2) {
                    const bulletText = trimmedLine.substring(1).trim();
                    if (bulletText.length > 0 && !bulletText.startsWith('*') && !bulletText.startsWith('**')) {
                        bullets.push(bulletText);
                    }
                }
            }
        }
        
        // 불릿 포인트가 있으면 요약 처리
        if (bullets.length > 0) {
            console.log(`[Section 2] 발견된 불릿 포인트 수: ${bullets.length}개`);
            
            // 최대 3-4개로 제한 (KEYWORD 섹션은 조금 더 자세하게)
            const maxBullets = Math.min(4, bullets.length);
            const selectedBullets = bullets.slice(0, maxBullets);
            
            // 각 불릿 포인트를 간결하게 요약 (최대 200자)
            const summarizedBullets = selectedBullets.map(bullet => {
                let summarized = bullet.trim();
                
                // 너무 길면 핵심만 추출
                if (summarized.length > 200) {
                    // 첫 문장 또는 핵심 키워드 포함 부분 추출
                    const firstSentence = summarized.split(/[.!?]/)[0];
                    if (firstSentence && firstSentence.length <= 200) {
                        summarized = firstSentence;
                    } else {
                        // 핵심 키워드가 포함된 부분 찾기
                        const keywords = ['급상승', '인기', '증가', '부상', '상승', '사랑받', '수요', '증대', '트렌드', '강세', '활발'];
                        for (const keyword of keywords) {
                            const keywordIndex = summarized.indexOf(keyword);
                            if (keywordIndex >= 0) {
                                const start = Math.max(0, keywordIndex - 60);
                                const end = Math.min(summarized.length, keywordIndex + 140);
                                summarized = summarized.substring(start, end).trim();
                                
                                // 앞뒤로 문장 경계 찾기
                                const beforeMatch = summarized.match(/^[^.!?]*[.!?]\s*(.+)$/);
                                if (beforeMatch) {
                                    summarized = beforeMatch[1];
                                }
                                const afterMatch = summarized.match(/^(.+?)[.!?]/);
                                if (afterMatch) {
                                    summarized = afterMatch[1] + '.';
                                }
                                
                                if (summarized.length <= 200) break;
                            }
                        }
                        
                        // 그래도 길면 단순히 앞부분만 자르기
                        if (summarized.length > 200) {
                            summarized = summarized.substring(0, 197) + '...';
                        }
                    }
                }
                
                return summarized;
            });
            
            // 요약된 불릿 포인트로 재구성
            summarizedContent = summarizedBullets.map(bullet => `- ${bullet}`).join('\n');
            
            console.log(`[Section 2] 요약 완료: ${bullets.length}개 → ${summarizedBullets.length}개`);
        } else {
            // 불릿 포인트가 없으면 일반 텍스트 요약 (최대 400자)
            if (summarizedContent.length > 400) {
                summarizedContent = summarizedContent.substring(0, 397) + '...';
            }
        }
        
        // 마크다운을 HTML로 변환 (개선된 로직)
        if (typeof marked !== 'undefined') {
            try {
                // marked 옵션 설정
                marked.setOptions({
                    breaks: true,
                    gfm: false,
                    headerIds: false,
                    mangle: false
                });
                
                // 마크다운 파싱 전 추가 정리
                // 리터럴 \n 제거, 연속된 ** 정리
                let cleanedMarkdown = summarizedContent
                    .replace(/\\n/g, '\n')  // 리터럴 \n을 실제 줄바꿈으로
                    .replace(/\*\*\*\*/g, '')  // 연속된 **** 제거
                    .replace(/\n\s*\*\*\s*\n/g, '\n')  // 빈 줄의 ** 제거
                    .replace(/\n\s*\*\s*\n/g, '\n');   // 빈 줄의 * 제거
                
                // 마크다운 파싱
                const markdownHtml = marked.parse(cleanedMarkdown);
                
                console.log(`[Section 2] 마크다운 변환 완료, 원본 길이: ${content.length}자, 요약 길이: ${summarizedContent.length}자`);
                
                if (typeof DOMPurify !== 'undefined') {
                    // DOMPurify로 안전하게 정제
                    contentDiv.innerHTML = DOMPurify.sanitize(markdownHtml, {
                        ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'span', 'mark'],
                        ALLOWED_ATTR: ['class', 'style']
                    });
                } else {
                    contentDiv.innerHTML = markdownHtml;
                }
            } catch (e) {
                console.error("[Section 2] 마크다운 변환 실패:", e);
                console.error("[Section 2] 원본 텍스트:", summarizedContent.substring(0, 200));
                // 폴백: 개선된 마크다운 처리
                let fallbackHtml = summarizedContent
                    .replace(/\\n/g, '\n')  // 리터럴 \n을 실제 줄바꿈으로
                    .replace(/\*\*\*\*/g, '')  // 연속된 **** 제거
                    .replace(/\n\s*\*\*\s*\n/g, '\n')  // 빈 줄의 ** 제거
                    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')  // **텍스트** → <strong>텍스트</strong>
                    .replace(/\*\*([^*]+)$/g, '<strong>$1</strong>')  // 끝에 남은 ** 처리
                    .replace(/^\*\*([^*]+)\*\*/gm, '<strong>$1</strong>')  // 줄 시작의 ** 처리
                    .replace(/\n/g, '<br>');  // 줄바꿈 처리
                contentDiv.innerHTML = fallbackHtml;
            }
        } else {
            console.warn("[Section 2] marked 라이브러리가 로드되지 않음");
            // 폴백: 개선된 마크다운 처리
            let fallbackHtml = summarizedContent
                .replace(/\\n/g, '\n')  // 리터럴 \n을 실제 줄바꿈으로
                .replace(/\*\*\*\*/g, '')  // 연속된 **** 제거
                .replace(/\n\s*\*\*\s*\n/g, '\n')  // 빈 줄의 ** 제거
                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')  // **텍스트** → <strong>텍스트</strong>
                .replace(/\*\*([^*]+)$/g, '<strong>$1</strong>')  // 끝에 남은 ** 처리
                .replace(/^\*\*([^*]+)\*\*/gm, '<strong>$1</strong>')  // 줄 시작의 ** 처리
                .replace(/\*(.+?)\*/g, '<em>$1</em>')  // *텍스트* → <em>텍스트</em> (strong이 아닌 경우만)
                .replace(/\n/g, '<br>');  // 줄바꿈 처리
            contentDiv.innerHTML = fallbackHtml;
        }
    } else {
        contentDiv.textContent = '분석 데이터가 없습니다.';
    }
    
    card.appendChild(contentDiv);
    
    return card;
}

// Section 3 텍스트를 세그먼트별로 파싱
function parseSection3BySegment(section3Text) {
    if (!section3Text || !section3Text.trim()) {
        console.warn('[parseSection3BySegment] Section 3 텍스트가 비어있음');
        return {
            rising_star: '',
            new_entry: '',
            rank_drop: ''
        };
    }
    
    console.log('[parseSection3BySegment] Section 3 텍스트 길이:', section3Text.length);
    console.log('[parseSection3BySegment] Section 3 텍스트 첫 200자:', section3Text.substring(0, 200));
    
    const segments = {
        rising_star: { patterns: ['급상승', 'Rising Star', '🔥'], text: '' },
        new_entry: { patterns: ['신규 진입', 'New Entry', '🚀'], text: '' },
        rank_drop: { patterns: ['순위 하락', 'Rank Drop', '📉'], text: '' }
    };
    
    // 세그먼트 헤더 찾기 (더 엄격한 패턴 매칭 - 각 세그먼트당 하나만 찾기)
    const lines = section3Text.split('\n');
    
    // 각 세그먼트의 시작 인덱스 찾기
    let risingStarIndex = -1;
    let newEntryIndex = -1;
    let rankDropIndex = -1;
    
    lines.forEach((line, index) => {
        const lineText = line.trim();
        const lineLower = lineText.toLowerCase();
        
        // 급상승 패턴 (이모지와 함께 시작하는 라인만)
        if (risingStarIndex === -1 && (lineText.startsWith('🔥') || lineText.includes('🔥 급상승') || 
            (lineText.includes('급상승') && lineText.includes('Rising Star')) || 
            (lineLower.includes('**🔥') && lineLower.includes('급상승')))) {
            risingStarIndex = index;
        }
        // 신규 진입 패턴
        else if (newEntryIndex === -1 && (lineText.startsWith('🚀') || lineText.includes('🚀 신규 진입') ||
            (lineText.includes('신규 진입') && lineText.includes('New Entry')) ||
            (lineLower.includes('**🚀') && lineLower.includes('신규 진입')))) {
            newEntryIndex = index;
        }
        // 순위 하락 패턴
        else if (rankDropIndex === -1 && (lineText.startsWith('📉') || lineText.includes('📉 순위 하락') ||
            (lineText.includes('순위 하락') && lineText.includes('Rank Drop')) ||
            (lineLower.includes('**📉') && lineLower.includes('순위 하락')))) {
            rankDropIndex = index;
        }
    });
    
    console.log('[parseSection3BySegment] 찾은 세그먼트 헤더 인덱스:', {
        risingStarIndex,
        newEntryIndex,
        rankDropIndex
    });
    
    // 각 세그먼트 텍스트 추출 (가장 먼저 나오는 헤더만 사용)
    const segmentIndices = [
        { type: 'rising_star', index: risingStarIndex },
        { type: 'new_entry', index: newEntryIndex },
        { type: 'rank_drop', index: rankDropIndex }
    ].filter(seg => seg.index >= 0).sort((a, b) => a.index - b.index); // 인덱스 순서대로 정렬
    
    segmentIndices.forEach((segment, segIndex) => {
        const startIndex = segment.index;
        const endIndex = segIndex < segmentIndices.length - 1 
            ? segmentIndices[segIndex + 1].index 
            : lines.length;
        
        const segmentLines = lines.slice(startIndex, endIndex); // 헤더 라인 포함
        const segmentText = segmentLines.join('\n').trim();
        
        segments[segment.type].text = segmentText;
        console.log(`[parseSection3BySegment] ${segment.type} 텍스트 길이:`, segmentText.length);
        console.log(`[parseSection3BySegment] ${segment.type} 텍스트 첫 200자:`, segmentText.substring(0, 200));
    });
    
    return {
        rising_star: segments.rising_star.text,
        new_entry: segments.new_entry.text,
        rank_drop: segments.rank_drop.text
    };
}

// Section 3를 탭 기반 UI로 렌더링
function renderSection3WithTabs(section3Data) {
    // Section 3 컨테이너 생성
    const section3Container = document.createElement('div');
    section3Container.className = 'trend-section3-container';
    section3Container.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; margin-top: 32px !important; margin-bottom: 24px !important;';
    
    // Section 3 헤더 추가
    const sectionHeader = document.createElement('h2');
    sectionHeader.className = 'trend-section3-header';
    sectionHeader.textContent = 'TRENDS';
    sectionHeader.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important;';
    section3Container.appendChild(sectionHeader);
    
    // 탭 UI 생성 (월간 리포트 Section 5 스타일)
    const tabsWrapper = document.createElement('div');
    tabsWrapper.className = 'market-trend-tabs-wrapper';
    tabsWrapper.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important;';
    
    const tabs = document.createElement('div');
    tabs.className = 'market-trend-tabs';
    tabs.id = 'section3Tabs';
    tabs.style.cssText = 'display: flex !important; visibility: visible !important; opacity: 1 !important;';
    
    const segmentTabs = [
        { type: 'rising_star', label: '급상승' },
        { type: 'new_entry', label: '신규 진입' },
        { type: 'rank_drop', label: '순위 하락' }
    ];
    
    segmentTabs.forEach((tab, index) => {
        const button = document.createElement('button');
        button.className = 'market-trend-tab-btn';
        if (index === 0) button.classList.add('active');
        button.setAttribute('data-segment', tab.type);
        button.textContent = tab.label;
        button.style.cssText = 'display: flex !important; visibility: visible !important; opacity: 1 !important;';
        tabs.appendChild(button);
    });
    
    tabsWrapper.appendChild(tabs);
    section3Container.appendChild(tabsWrapper);
    
    // 콘텐츠 영역 생성
    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'trend-section3-content-wrapper';
    contentWrapper.id = 'section3Content';
    contentWrapper.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; margin-top: 24px !important;';
    
    section3Container.appendChild(contentWrapper);
    
    // 첫 번째 탭(급상승) 콘텐츠 렌더링
    renderSection3SegmentContent('rising_star', section3Data.rising_star, contentWrapper);
    
    // 탭 이벤트 핸들러 설정
    tabs.querySelectorAll('.market-trend-tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const segmentType = this.getAttribute('data-segment');
            
            // 활성화 상태 업데이트
            tabs.querySelectorAll('.market-trend-tab-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // 콘텐츠 렌더링
            renderSection3SegmentContent(segmentType, section3Data[segmentType], contentWrapper);
        });
    });
    
    return section3Container;
}

// Section 3 세그먼트 콘텐츠 렌더링 (카테고리별 Card UI)
function renderSection3SegmentContent(segmentType, segmentText, container) {
    console.log('[renderSection3SegmentContent] 호출됨:', segmentType, '텍스트 길이:', segmentText ? segmentText.length : 0);
    
    if (!segmentText || !segmentText.trim()) {
        console.warn('[renderSection3SegmentContent] 세그먼트 텍스트 없음');
        container.innerHTML = '<div class="trend-analysis-empty">분석 데이터가 없습니다.</div>';
        return;
    }
    
    // 세그먼트 헤더 제거
    let cleanedText = segmentText;
    cleanedText = cleanedText.replace(/^\*\*?[🔥🚀📉]\s*(급상승|신규 진입|순위 하락)\s*\([^\)]+\)\*\*?\s*\n*/m, '');
    cleanedText = cleanedText.replace(/^\*\*?(Rising Star|New Entry|Rank Drop)\*\*?\s*\n*/m, '');
    cleanedText = cleanedText.trim();
    
    // 카테고리별 텍스트 파싱
    const lines = cleanedText.split('\n');
    
    // 1. AI 리포트에서 실제로 사용된 카테고리 헤더를 동적으로 찾기
    const foundCategoriesInText = [];
    const categoryHeaderRegex = /^\*\*([^:]+):\*\*/;
    
    lines.forEach((line, lineIndex) => {
        const match = line.trim().match(categoryHeaderRegex);
        if (match && match[1]) {
            const categoryName = match[1].trim();
            if (categoryName && !foundCategoriesInText.some(c => c.name === categoryName)) {
                foundCategoriesInText.push({ name: categoryName, index: lineIndex });
            }
        }
    });
    
    console.log('[renderSection3SegmentContent] AI 리포트에서 발견된 카테고리:', foundCategoriesInText.map(c => c.name));
    
    // 2. allTabsData의 키와 AI 리포트에서 찾은 카테고리를 병합
    let categoriesFromData = [];
    if (window.allTabsData && Object.keys(window.allTabsData).length > 0) {
        categoriesFromData = Object.keys(window.allTabsData);
        console.log('[renderSection3SegmentContent] allTabsData의 카테고리:', categoriesFromData);
    }
    
    // 3. 기본 카테고리 목록 (하드코딩)
    const defaultCategories = ['상의', '바지', '스커트', '원피스', '니트웨어', '셋업', '아우터', '언더웨어', '점프수트', '파티복/행사복', '해외브랜드', '홈웨어'];
    
    // 4. 병합: AI 리포트에서 찾은 카테고리를 우선 사용하고, allTabsData와 기본 목록과 합치기
    const allPossibleCategories = new Set();
    
    // AI 리포트에서 찾은 카테고리 추가 (우선순위 1)
    foundCategoriesInText.forEach(cat => allPossibleCategories.add(cat.name));
    
    // allTabsData의 카테고리 추가 (우선순위 2)
    categoriesFromData.forEach(cat => allPossibleCategories.add(cat));
    
    // 기본 카테고리 추가 (우선순위 3)
    defaultCategories.forEach(cat => allPossibleCategories.add(cat));
    
    const mergedCategories = Array.from(allPossibleCategories).sort();
    console.log('[renderSection3SegmentContent] 병합된 카테고리 목록:', mergedCategories);
    
    // 5. 실제로 AI 리포트에 존재하는 카테고리만 필터링하여 인덱스 리스트 생성
    const categoryIndexList = [];
    foundCategoriesInText.forEach(categoryInfo => {
        categoryIndexList.push({ name: categoryInfo.name, index: categoryInfo.index });
    });
    
    // 2. 인덱스 오름차순(등장 순서)으로 정렬
    categoryIndexList.sort((a, b) => a.index - b.index);
    
    console.log('[renderSection3SegmentContent] 카테고리 등장 순서:', categoryIndexList.map(c => `${c.name} (${c.index})`));
    
    // 3. 정렬된 순서대로 텍스트 추출 및 HTML 변환
    const categoryData = {};
    categoryIndexList.forEach((categoryInfo, catIndex) => {
        const categoryName = categoryInfo.name;
        const startIndex = categoryInfo.index;
        
        console.log(`[DEBUG] 카테고리 처리 시작: ${categoryName} (인덱스: ${startIndex})`);
        
        // 다음 카테고리 헤더의 위치 찾기 (정렬된 배열에서 다음 항목)
        let endIndex = lines.length;
        if (catIndex < categoryIndexList.length - 1) {
            endIndex = categoryIndexList[catIndex + 1].index;
        }
        
        console.log(`[DEBUG] ${categoryName} - 텍스트 추출 범위: 라인 ${startIndex + 1} ~ ${endIndex - 1}`);
        
        // 카테고리 텍스트 추출 (헤더 다음 줄부터 다음 카테고리 헤더 전까지)
        const categoryLines = lines.slice(startIndex + 1, endIndex);
        let categoryText = categoryLines.join('\n').trim();
        
        // 텍스트 전처리: 리터럴 \n을 실제 줄바꿈으로 변환
        categoryText = categoryText
            .replace(/\\n/g, '\n')  // 리터럴 \n을 실제 줄바꿈으로
            .replace(/\r\n/g, '\n')  // Windows 줄바꿈 정규화
            .replace(/\r/g, '\n');    // Mac 줄바꿈 정규화
        
        console.log(`[DEBUG] ${categoryName} - 추출된 원본 텍스트 길이: ${categoryText.length}자`);
        if (categoryText.length > 0) {
            console.log(`[DEBUG] ${categoryName} - 추출된 텍스트 앞부분 (200자):`, categoryText.substring(0, 200));
        }
        
        if (!categoryText || categoryText.length === 0) {
            console.warn(`[DEBUG] ${categoryName} - 빈 텍스트, 스킵`);
            return; // 빈 텍스트면 스킵
        }
        
        // 텍스트 요약 로직: 불릿 포인트를 2-3개로 제한하고 각각의 길이 제한
        let summarizedText = categoryText;
        
        // 불릿 포인트(- 또는 * 로 시작하는 줄) 추출 (개선된 패턴)
        // *   또는 * 로 시작하는 패턴 처리
        const bullets = [];
        
        // 먼저 줄 단위로 분리해서 처리
        const textLines = categoryText.split('\n');
        console.log(`[DEBUG] ${categoryName} - 총 ${textLines.length}줄 분석 시작`);
        
        for (let i = 0; i < textLines.length; i++) {
            const line = textLines[i];
            const trimmedLine = line.trim();
            
            // * 또는 - 로 시작하는 줄 찾기 (공백 포함 패턴도 처리)
            // 예: "*   **텍스트**" 또는 "* **텍스트**" 또는 "* 텍스트"
            if (trimmedLine.match(/^[\s]*[-*•]\s+/)) {
                // 불렛 기호와 공백 제거
                let bulletText = trimmedLine.replace(/^[\s]*[-*•]\s+/, '').trim();
                
                if (bulletText.length > 0) {
                    bullets.push(bulletText);
                    console.log(`[DEBUG] ${categoryName} - 불렛 포인트 ${bullets.length} 발견: "${bulletText.substring(0, 50)}..."`);
                }
            }
        }
        
        console.log(`[DEBUG] ${categoryName} - 총 ${bullets.length}개 불렛 포인트 추출 완료`);
        
        // 불릿 포인트가 있으면 요약 처리
        if (bullets.length > 0) {
            console.log(`[DEBUG] ${categoryName} - 발견된 불릿 포인트 수: ${bullets.length}개`);
            
            // 최대 2-3개로 제한 (중요한 내용 우선)
            const maxBullets = Math.min(3, bullets.length);
            const selectedBullets = bullets.slice(0, maxBullets);
            
            // 각 불릿 포인트를 간결하게 요약 (최대 150자)
            const summarizedBullets = selectedBullets.map(bullet => {
                let summarized = bullet.trim();
                
                // 너무 길면 핵심만 추출
                if (summarized.length > 150) {
                    // 첫 문장 또는 핵심 키워드 포함 부분 추출
                    const firstSentence = summarized.split(/[.!?]/)[0];
                    if (firstSentence && firstSentence.length <= 150) {
                        summarized = firstSentence;
                    } else {
                        // 핵심 키워드가 포함된 부분 찾기
                        const keywords = ['급상승', '인기', '증가', '부상', '상승', '사랑받', '수요', '증대', '트렌드'];
                        for (const keyword of keywords) {
                            const keywordIndex = summarized.indexOf(keyword);
                            if (keywordIndex >= 0) {
                                const start = Math.max(0, keywordIndex - 50);
                                const end = Math.min(summarized.length, keywordIndex + 100);
                                summarized = summarized.substring(start, end).trim();
                                
                                // 앞뒤로 문장 경계 찾기
                                const beforeMatch = summarized.match(/^[^.!?]*[.!?]\s*(.+)$/);
                                if (beforeMatch) {
                                    summarized = beforeMatch[1];
                                }
                                const afterMatch = summarized.match(/^(.+?)[.!?]/);
                                if (afterMatch) {
                                    summarized = afterMatch[1] + '.';
                                }
                                
                                if (summarized.length <= 150) break;
                            }
                        }
                        
                        // 그래도 길면 단순히 앞부분만 자르기
                        if (summarized.length > 150) {
                            summarized = summarized.substring(0, 147) + '...';
                        }
                    }
                }
                
                return summarized;
            });
            
            // 요약된 불릿 포인트로 재구성
            summarizedText = summarizedBullets.map(bullet => `- ${bullet}`).join('\n');
            
            console.log(`[DEBUG] ${categoryName} - 요약 완료: ${bullets.length}개 → ${summarizedBullets.length}개`);
        } else {
            // 불릿 포인트가 없으면 일반 텍스트 요약 (최대 300자)
            if (summarizedText.length > 300) {
                summarizedText = summarizedText.substring(0, 297) + '...';
            }
        }
        
        // 마크다운을 HTML로 변환
        if (typeof marked !== 'undefined') {
            try {
                marked.setOptions({ breaks: true, gfm: false });
                
                // 마크다운 파싱 전 추가 정리
                let cleanedMarkdown = summarizedText
                    .replace(/\\n/g, '\n')  // 리터럴 \n을 실제 줄바꿈으로
                    .replace(/\*\*\*\*/g, '')  // 연속된 **** 제거
                    .replace(/\n\s*\*\*\s*\n/g, '\n')  // 빈 줄의 ** 제거
                    .replace(/\n\s*\*\s*\n/g, '\n')   // 빈 줄의 * 제거
                    .replace(/([^*])\*\*([^*])/g, '$1**$2');  // ** 앞뒤 공백 확인용
                
                console.log(`[DEBUG] ${categoryName} - 마크다운 파싱 전 텍스트 (200자):`, cleanedMarkdown.substring(0, 200));
                
                const markdownHtml = marked.parse(cleanedMarkdown);
                
                console.log(`[DEBUG] ${categoryName} - 마크다운 파싱 후 HTML (200자):`, markdownHtml.substring(0, 200));
                
                if (typeof DOMPurify !== 'undefined') {
                    categoryText = DOMPurify.sanitize(markdownHtml, {
                        ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'blockquote'],
                        ALLOWED_ATTR: []
                    });
                } else {
                    categoryText = markdownHtml;
                }
                
                console.log(`[DEBUG] ${categoryName} - 마크다운 변환 완료, HTML 길이: ${categoryText.length}자 (원본: ${categoryText.length}자 → 요약: ${summarizedText.length}자)`);
            } catch (e) {
                console.warn(`[DEBUG] ${categoryName} - 마크다운 변환 실패:`, e);
                // 폴백: 개선된 마크다운 처리
                let fallbackHtml = summarizedText
                    .replace(/\\n/g, '\n')  // 리터럴 \n을 실제 줄바꿈으로
                    .replace(/\*\*\*\*/g, '')  // 연속된 **** 제거
                    .replace(/\n\s*\*\*\s*\n/g, '\n')  // 빈 줄의 ** 제거
                    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')  // **텍스트** → <strong>텍스트</strong>
                    .replace(/\*\*([^*]+)$/g, '<strong>$1</strong>')  // 끝에 남은 ** 처리
                    .replace(/^\*\*([^*]+)\*\*/gm, '<strong>$1</strong>')  // 줄 시작의 ** 처리
                    .replace(/\n/g, '<br>');  // 줄바꿈 처리
                categoryText = fallbackHtml;
            }
        } else {
            // 폴백: 개선된 마크다운 처리
            let fallbackHtml = summarizedText
                .replace(/\\n/g, '\n')  // 리터럴 \n을 실제 줄바꿈으로
                .replace(/\*\*\*\*/g, '')  // 연속된 **** 제거
                .replace(/\n\s*\*\*\s*\n/g, '\n')  // 빈 줄의 ** 제거
                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')  // **텍스트** → <strong>텍스트</strong>
                .replace(/\*\*([^*]+)$/g, '<strong>$1</strong>')  // 끝에 남은 ** 처리
                .replace(/^\*\*([^*]+)\*\*/gm, '<strong>$1</strong>')  // 줄 시작의 ** 처리
                .replace(/\*(.+?)\*/g, '<em>$1</em>')  // *텍스트* → <em>텍스트</em> (strong이 아닌 경우만)
                .replace(/\n/g, '<br>');  // 줄바꿈 처리
            categoryText = fallbackHtml;
        }
        
        categoryData[categoryName] = categoryText;
        console.log(`[DEBUG] ${categoryName} - 최종 파싱된 텍스트 길이: ${categoryText.length}자`);
    });
    
    // 컨테이너 초기화
    container.innerHTML = '';
    
    // 4. 루프 실행: 정렬된 순서대로 카테고리를 순회하면서 Card UI 생성
    categoryIndexList.forEach((categoryInfo, index) => {
        const categoryName = categoryInfo.name;
        const categoryText = categoryData[categoryName];
        
        console.log(`[DEBUG] 카테고리 UI 생성 시작 [${index + 1}/${categoryIndexList.length}]: ${categoryName}`);
        console.log(`[DEBUG] ${categoryName} - 파싱된 텍스트 존재:`, !!categoryText);
        console.log(`[DEBUG] ${categoryName} - 파싱된 텍스트 길이:`, categoryText ? categoryText.length : 0);
        if (categoryText && categoryText.length > 0) {
            // HTML 태그 제거한 순수 텍스트로 앞부분 출력
            const textPreview = categoryText.replace(/<[^>]*>/g, '').substring(0, 150);
            console.log(`[DEBUG] ${categoryName} - 텍스트 미리보기:`, textPreview + '...');
        }
        
        // 예외 처리: 텍스트가 없으면 카드 생성하지 않고 건너뜀
        if (!categoryText) {
            console.log(`[DEBUG] ${categoryName} - 텍스트 없음, 카드 생성 스킵`);
            return;
        }
        
        // B. 카드 요소 생성
        const cardContainer = document.createElement('div');
        cardContainer.className = 'trend-category-card';
        
        // C. 헤더 영역 생성
        const headerSection = document.createElement('div');
        headerSection.className = 'trend-category-header';
        
        // 뱃지 생성
        const categoryBadge = document.createElement('span');
        categoryBadge.className = 'trend-category-badge';
        categoryBadge.textContent = categoryName;
        headerSection.appendChild(categoryBadge);
        
        // 분석 텍스트 영역 생성
        const analysisSection = document.createElement('div');
        analysisSection.className = 'trend-category-analysis';
        
        const insight = document.createElement('div');
        insight.className = 'trend-category-insight';
        insight.innerHTML = categoryText;
        analysisSection.appendChild(insight);
        
        headerSection.appendChild(analysisSection);
        
        // 헤더를 카드에 추가
        cardContainer.appendChild(headerSection);
        
        // D. 썸네일 그리드 생성 및 추가 (명시적 DOM 조립)
        // 썸네일 wrapper를 명시적으로 생성
        const thumbnailsWrapper = document.createElement('div');
        thumbnailsWrapper.className = 'trend-category-thumbnails';
        
        // 반드시 헤더 다음에 썸네일 wrapper를 추가 (DOM 구조 보장)
        cardContainer.appendChild(thumbnailsWrapper);
        
        // DOM 구조 확인 로그
        console.log(`[DEBUG] ${categoryName} - 카드 DOM 구조 생성 완료:`, {
            hasHeader: !!cardContainer.querySelector('.trend-category-header'),
            hasThumbnailsWrapper: !!cardContainer.querySelector('.trend-category-thumbnails'),
            cardChildrenCount: cardContainer.children.length
        });
        
        // 썸네일 추가 함수 (allTabsData 준비 대기)
        const addThumbnails = () => {
            // thumbnailsWrapper가 DOM에 제대로 연결되어 있는지 확인
            if (!thumbnailsWrapper.parentElement || !cardContainer.contains(thumbnailsWrapper)) {
                console.warn(`[DEBUG] ${categoryName} - thumbnailsWrapper가 카드에 연결되지 않음, 재연결 시도`);
                cardContainer.appendChild(thumbnailsWrapper);
            }
            
            if (window.allTabsData && Object.keys(window.allTabsData).length > 0) {
                console.log(`[DEBUG] ${categoryName} - 상품 데이터 요청 시작`);
                console.log(`[DEBUG] ${categoryName} - 요청 파라미터: categoryName="${categoryName}", segmentType="${segmentType}"`);
                console.log(`[DEBUG] ${categoryName} - allTabsData 사용 가능한 카테고리:`, Object.keys(window.allTabsData));
                
                // 카테고리명으로 상품 조회 시도
                let categoryProducts = getProductsByCategory(categoryName, segmentType);
                
                // 상품이 없으면 카테고리명 변형을 시도
                if (categoryProducts.length === 0) {
                    console.log(`[DEBUG] ${categoryName} - 기본 카테고리명으로 상품 없음, 변형 시도 중...`);
                    
                    // 슬래시가 있으면 분리 시도 (예: "파티복/행사복" -> "파티복", "행사복")
                    if (categoryName.includes('/')) {
                        const parts = categoryName.split('/').map(p => p.trim());
                        for (const part of parts) {
                            categoryProducts = getProductsByCategory(part, segmentType);
                            if (categoryProducts.length > 0) {
                                console.log(`[DEBUG] ${categoryName} - 변형 성공: "${part}"에서 ${categoryProducts.length}개 상품 발견`);
                                break;
                            }
                        }
                    }
                    
                    // 여전히 없으면 부분 매칭 시도
                    if (categoryProducts.length === 0 && window.allTabsData) {
                        const availableTabs = Object.keys(window.allTabsData);
                        for (const tabName of availableTabs) {
                            if (tabName.includes(categoryName) || categoryName.includes(tabName)) {
                                categoryProducts = getProductsByCategory(tabName, segmentType);
                                if (categoryProducts.length > 0) {
                                    console.log(`[DEBUG] ${categoryName} - 부분 매칭 성공: "${tabName}"에서 ${categoryProducts.length}개 상품 발견`);
                                    break;
                                }
                            }
                        }
                    }
                }
                
                console.log(`[DEBUG] ${categoryName} - 최종 가져온 상품 개수: ${categoryProducts.length}개`);
                if (categoryProducts.length > 0) {
                    console.log(`[DEBUG] ${categoryName} - 첫 번째 상품 샘플:`, {
                        product: categoryProducts[0].product || categoryProducts[0].product_name,
                        brand: categoryProducts[0].brand || categoryProducts[0].brand_name,
                        category: categoryProducts[0].category,
                        rank: categoryProducts[0].rank,
                        rankChange: categoryProducts[0].rankChange
                    });
                    if (categoryProducts.length > 1) {
                        console.log(`[DEBUG] ${categoryName} - 두 번째 상품 샘플:`, {
                            product: categoryProducts[1].product || categoryProducts[1].product_name,
                            brand: categoryProducts[1].brand || categoryProducts[1].brand_name
                        });
                    }
                } else {
                    console.warn(`[DEBUG] ${categoryName} - 상품 데이터가 없습니다`);
                }
                
                // 상품이 있으면 반드시 썸네일 그리드를 생성하고 주입
                if (categoryProducts.length > 0) {
                    const thumbnailGrid = createThumbnailGridFromProducts(categoryProducts, segmentType);
                    if (thumbnailGrid && thumbnailGrid.trim().length > 0) {
                        console.log(`[DEBUG] ${categoryName} - 썸네일 그리드 HTML 생성 완료, 길이: ${thumbnailGrid.length}자`);
                        
                        // thumbnailsWrapper가 여전히 카드에 연결되어 있는지 재확인
                        if (!cardContainer.contains(thumbnailsWrapper)) {
                            console.warn(`[DEBUG] ${categoryName} - thumbnailsWrapper가 카드에서 분리됨, 재추가`);
                            cardContainer.appendChild(thumbnailsWrapper);
                        }
                        
                        // HTML만 주입, 스타일은 CSS에 맡김
                        thumbnailsWrapper.innerHTML = thumbnailGrid;
                        
                        // DOM에 제대로 추가되었는지 확인 및 검증
                        const insertedGrid = thumbnailsWrapper.querySelector('.trend-thumbnails-grid');
                        if (insertedGrid) {
                            const cardCount = insertedGrid.querySelectorAll('.trend-thumbnail-card').length;
                            console.log(`[DEBUG] ${categoryName} - 썸네일 그리드 DOM 삽입 완료, 카드 수: ${cardCount}개`);
                            
                            // 최종 DOM 구조 확인
                            if (cardCount === 0) {
                                console.error(`[DEBUG] ${categoryName} - 썸네일 그리드는 삽입되었지만 카드가 없음!`);
                            }
                        } else {
                            console.error(`[DEBUG] ${categoryName} - 썸네일 그리드가 DOM에 제대로 삽입되지 않음!`);
                            console.error(`[DEBUG] ${categoryName} - thumbnailsWrapper.innerHTML 길이:`, thumbnailsWrapper.innerHTML.length);
                        }
                    } else {
                        console.warn(`[DEBUG] ${categoryName} - 썸네일 그리드 HTML 생성 실패 또는 빈 문자열`);
                    }
                } else {
                    // 상품이 없어도 빈 wrapper는 유지 (레이아웃 안정성)
                    console.log(`[DEBUG] ${categoryName} - 상품 데이터 없음 (${categoryProducts.length}개), 빈 썸네일 wrapper 유지`);
                }
            } else {
                // 재시도
                const retryCount = (addThumbnails.retryCount || 0) + 1;
                addThumbnails.retryCount = retryCount;
                
                if (retryCount < 50) {
                    if (retryCount % 10 === 0) {
                        console.log(`[DEBUG] ${categoryName} - allTabsData 대기 중... (재시도 ${retryCount}/50)`);
                    }
                    setTimeout(addThumbnails, 100);
                } else {
                    console.warn(`[DEBUG] ${categoryName} - allTabsData를 찾을 수 없습니다 (최대 재시도 횟수 초과)`);
                }
            }
        };
        
        // 5. DOM 추가: 완성된 카드를 메인 컨테이너에 추가 (썸네일 wrapper 포함)
        container.appendChild(cardContainer);
        
        // 썸네일 추가 시도 시작 (카드가 DOM에 추가된 후 실행)
        setTimeout(addThumbnails, 100);
    });
}

// Section 3 세그먼트에 대한 썸네일 렌더링 (기존 함수 활용)
function renderSection3ThumbnailsForSegment(textContainer, segmentType) {
    if (!window.allTabsData || Object.keys(window.allTabsData).length === 0) {
        console.warn('[Section 3 썸네일] allTabsData가 없습니다.');
        return;
    }
    
    // 기존 썸네일 제거
    const existingThumbnails = textContainer.querySelectorAll('.trend-category-thumbnails');
    existingThumbnails.forEach(thumb => thumb.remove());
    
    // 카테고리 목록
    // Ably의 경우 allTabsData에서 실제 카테고리 목록을 가져오고, 29CM의 경우 기본 카테고리 사용
    let categories;
    if (IS_ABLY && window.allTabsData && Object.keys(window.allTabsData).length > 0) {
        categories = Object.keys(window.allTabsData).sort();
    } else {
        categories = ['상의', '바지', '스커트', '원피스', '니트웨어', '셋업'];
    }
    
    categories.forEach(categoryName => {
        const categoryProducts = getProductsByCategory(categoryName, segmentType);
        if (categoryProducts.length === 0) {
            return;
        }
        
        // 카테고리 헤드라인 찾기 (h3.section5-title-box 또는 strong)
        const categoryHeaders = textContainer.querySelectorAll('h3.section5-title-box, strong, p, li');
        let categoryHeaderElement = null;
        
        for (const element of categoryHeaders) {
            const textContent = (element.textContent || '').trim();
            const innerHTML = (element.innerHTML || '').trim();
            
            const isCategoryHeader = 
                textContent === `${categoryName}:` || 
                textContent.startsWith(`${categoryName}:`) ||
                innerHTML.includes(`<strong>${categoryName}:</strong>`) ||
                innerHTML.includes(`**${categoryName}:**`) ||
                (element.tagName === 'H3' && element.classList.contains('section5-title-box') && textContent.includes(categoryName));
            
            if (isCategoryHeader) {
                // h3.section5-title-box인 경우 그대로 사용, 아니면 부모 요소 찾기
                if (element.tagName === 'H3' && element.classList.contains('section5-title-box')) {
                    categoryHeaderElement = element;
                } else {
                    categoryHeaderElement = element.closest('p, li') || element.parentElement || element;
                }
                break;
            }
        }
        
        if (categoryHeaderElement) {
            // 썸네일 그리드 생성
            const thumbnailGrid = createThumbnailGridFromProducts(categoryProducts, segmentType);
            
            if (thumbnailGrid) {
                // 이미 썸네일이 있는지 확인
                const nextSibling = categoryHeaderElement.nextElementSibling;
                if (nextSibling && nextSibling.classList.contains('trend-category-thumbnails')) {
                    return; // 이미 있으면 스킵
                }
                
                const gridContainer = document.createElement('div');
                gridContainer.className = 'trend-category-thumbnails';
                gridContainer.innerHTML = thumbnailGrid;
                
                if (categoryHeaderElement.nextSibling) {
                    categoryHeaderElement.parentNode.insertBefore(gridContainer, categoryHeaderElement.nextSibling);
                } else {
                    categoryHeaderElement.parentNode.appendChild(gridContainer);
                }
            }
        }
    });
}
