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
        if (weekInfo) {
            const platformName = IS_ABLY ? 'Ably' : '29CM';
            titleElement.textContent = `${platformName} ${weekInfo.year}년 ${weekInfo.month}월 ${weekInfo.week}주차 트렌드`;
        } else {
            const platformName = IS_ABLY ? 'Ably' : '29CM';
            titleElement.textContent = `${platformName} ${currentWeek} 트렌드`;
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
        if (weekInfo) {
            analysisTitleElement.textContent = `${platformName} ${weekInfo.month}월 ${weekInfo.week}주차 트렌드 분석`;
        } else {
            analysisTitleElement.textContent = `${platformName} ${currentWeek} 트렌드 분석`;
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
    
    // API 호출로 분석 리포트 가져오기
    fetch(API_ENDPOINT, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            tab_names: Object.keys(allTabsData || {}),
            trend_type: 'all'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // insights 데이터 저장
            if (data.insights) {
                window.trendInsights = data.insights;
            }
            
            renderTrendAnalysisReport(data.insights || {}, createdAtElement);
        } else {
            contentElement.innerHTML = '<div class="trend-analysis-error">분석 리포트를 불러올 수 없습니다.</div>';
        }
    })
    .catch(error => {
        console.error('분석 리포트 로드 실패:', error);
        contentElement.innerHTML = '<div class="trend-analysis-error">분석 리포트를 불러오는 중 오류가 발생했습니다.</div>';
    });
}

// 트렌드 분석 리포트 렌더링 (마크다운 지원 + Section 3 탭 기반 UI)
function renderTrendAnalysisReport(insights, createdAtElement) {
    const contentElement = document.getElementById('trendAnalysisContent');
    if (!contentElement) return;
    
    const analysisText = insights.analysis_report;
    
    // 생성일 업데이트
    if (insights && insights.generated_at && createdAtElement) {
        try {
            const date = new Date(insights.generated_at);
            createdAtElement.textContent = `생성일: ${date.toLocaleDateString('ko-KR')} ${date.toLocaleTimeString('ko-KR', {hour: '2-digit', minute: '2-digit'})}`;
        } catch (e) {
            console.warn('생성일 파싱 실패:', e);
        }
    }
    
    if (!analysisText || !analysisText.trim()) {
        contentElement.innerHTML = '<div class="trend-analysis-empty">분석 리포트가 아직 생성되지 않았습니다.</div>';
        return;
    }
    
    // Section 1, 2, 3으로 분리
    const sections = parseAnalysisReportSections(analysisText);
    console.log('[renderTrendAnalysisReport] Section 분리 결과:', {
        section1Length: sections.section1.length,
        section2Length: sections.section2.length,
        section3Length: sections.section3.length
    });
    
    // Section 2 파싱 (Material과 TPO 추출)
    const section2Data = parseSection2IntoMaterialAndTPO(sections.section2);
    
    // Section 3 세그먼트별로 파싱
    const section3Data = parseSection3BySegment(sections.section3);
    
    // HTML 구조 생성
    const container = document.createElement('div');
    container.className = 'trend-analysis-report-container';
    
    // Section 1 카드 레이아웃 추가
    if (sections.section1) {
        const section1Container = renderSection1AsCard(sections.section1);
        if (section1Container) {
            container.appendChild(section1Container);
        }
    }
    
    // Section 2 카드 레이아웃 추가
    if (sections.section2) {
        const section2Container = renderSection2AsCards(section2Data);
        container.appendChild(section2Container);
    }
    
    // Section 3 탭 기반 UI 추가
    if (sections.section3) {
        const section3Container = renderSection3WithTabs(section3Data);
        container.appendChild(section3Container);
    }
    
    contentElement.innerHTML = '';
    contentElement.appendChild(container);
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
    const categories = ['상의', '바지', '스커트', '원피스', '니트웨어', '셋업'];
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
    if (!window.allTabsData) {
        console.warn(`[getProductsByCategory] allTabsData 없음: ${categoryName}`);
        return [];
    }
    
    const products = [];
    
    // 해당 카테고리의 탭 데이터 찾기
    const tabData = window.allTabsData[categoryName];
    if (!tabData) {
        console.warn(`[getProductsByCategory] ${categoryName} 카테고리 데이터 없음. 사용 가능한 카테고리:`, Object.keys(window.allTabsData));
        return [];
    }
    
    // 현재 트렌드 타입에 해당하는 상품 추출
    const items = tabData[trendType] || [];
    console.log(`[getProductsByCategory] ${categoryName} (${trendType}): 원본 아이템 ${items.length}개`);
    
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
                console.log(`[getProductsByCategory] ${categoryName} 아이템 ${index} 필터링됨 - brand: "${brand}", product: "${product}", thumbnail: "${thumbnail ? '있음' : '없음'}"`);
            }
        }
    });
    
    console.log(`[getProductsByCategory] ${categoryName} (${trendType}): 필터링 후 ${products.length}개`);
    
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
            // 순위하락: 순위변화 작은 것부터 (음수, -50, -30, -10...)
            const changeA = a.rankChange !== null && a.rankChange !== undefined ? a.rankChange : 0;
            const changeB = b.rankChange !== null && b.rankChange !== undefined ? b.rankChange : 0;
            return changeA - changeB; // 오름차순 (더 작은 음수부터)
        }
        return 0;
    });
    
    // 상위 6개만 반환
    const result = products.slice(0, 6);
    console.log(`[getProductsByCategory] ${categoryName} (${trendType}): 최종 반환 ${result.length}개`);
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
        } else if (trendType === 'rank_drop' && rankChange !== null && rankChange !== undefined && rankChange < 0) {
            rankChangeText = `📉 ${rankChange}위 하락`;
            rankChangeClass = 'trend-rank-change-down';
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
    
    // 텍스트가 비어있으면 null 반환
    if (!cleanedText || cleanedText.length === 0) {
        return null;
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
function getCompanyProducts() {
    if (!window.allTabsData || Object.keys(window.allTabsData).length === 0) {
        return [];
    }
    
    // company_name으로 한글명 추정 (간단한 매핑)
    const urlParams = new URLSearchParams(window.location.search);
    const companyName = urlParams.get('company_name') || (typeof window.selectedCompany !== 'undefined' ? window.selectedCompany : '');
    
    // 브랜드명 매핑 (일반적인 케이스)
    const brandMapping = {
        'piscess': ['파이시스', 'PISCESS'],
        'somewherebutter': ['썸웨어버터', 'Somewhere Butter', 'SOMEWHERE BUTTER'],
        'demo': []
    };
    
    const targetBrands = brandMapping[companyName?.toLowerCase()] || [];
    if (targetBrands.length === 0) {
        console.warn('[getCompanyProducts] 브랜드 매핑 없음:', companyName);
        return [];
    }
    
    const products = [];
    
    // 모든 카테고리와 세그먼트를 순회
    Object.keys(window.allTabsData).forEach(categoryName => {
        const tabData = window.allTabsData[categoryName];
        ['rising_star', 'new_entry', 'rank_drop'].forEach(trendType => {
            const items = tabData[trendType] || [];
            items.forEach(item => {
                const brand = item.Brand_Name || item.Brand || '';
                const product = item.Product_Name || item.Product || '';
                const thumbnail = item.thumbnail_url || '';
                const itemUrl = item.item_url || '';
                const rank = item.This_Week_Rank || item.Ranking || '';
                const rankChange = item.Rank_Change;
                const price = item.price || item.Price || 0;
                
                // 브랜드명 매칭 (대소문자 무시, 공백 무시)
                const brandMatch = targetBrands.some(targetBrand => 
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
                        category: categoryName
                    });
                }
            });
        });
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
    
    return products;
}

// Section 2를 2열 카드 레이아웃으로 렌더링
function renderSection2AsCards(section2Data) {
    const container = document.createElement('div');
    container.className = 'trend-section2-container';
    
    // Section 2 헤더
    const header = document.createElement('h2');
    header.className = 'trend-section2-header';
    header.textContent = 'KEYWORD';
    container.appendChild(header);
    
    // 2열 그리드 컨테이너
    const gridContainer = document.createElement('div');
    gridContainer.className = 'trend-section2-grid';
    
    // Material 카드
    const materialCard = createSection2Card('🧶', 'Material Trend', '소재 트렌드', section2Data.material);
    gridContainer.appendChild(materialCard);
    
    // Mood 카드
    const moodCard = createSection2Card('✨', 'Mood & Style', '무드 & 스타일', section2Data.mood);
    gridContainer.appendChild(moodCard);
    
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
        // 마크다운을 HTML로 변환
        if (typeof marked !== 'undefined') {
            try {
                marked.setOptions({
                    breaks: true,
                    gfm: false
                });
                
                const markdownHtml = marked.parse(content);
                
                if (typeof DOMPurify !== 'undefined') {
                    contentDiv.innerHTML = DOMPurify.sanitize(markdownHtml, {
                        ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li'],
                        ALLOWED_ATTR: []
                    });
                } else {
                    contentDiv.innerHTML = markdownHtml;
                }
            } catch (e) {
                console.warn("[Section 2] 마크다운 변환 실패:", e);
                contentDiv.innerHTML = content.replace(/\n/g, '<br>');
            }
        } else {
            contentDiv.innerHTML = content.replace(/\n/g, '<br>');
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
    
    // Section 3 헤더 추가
    const sectionHeader = document.createElement('h2');
    sectionHeader.className = 'trend-section3-header';
    sectionHeader.textContent = 'TRENDS';
    section3Container.appendChild(sectionHeader);
    
    // 탭 UI 생성 (월간 리포트 Section 5 스타일)
    const tabsWrapper = document.createElement('div');
    tabsWrapper.className = 'market-trend-tabs-wrapper';
    
    const tabs = document.createElement('div');
    tabs.className = 'market-trend-tabs';
    tabs.id = 'section3Tabs';
    
    const segmentTabs = [
        { type: 'rising_star', label: '🔥 급상승', displayLabel: '급상승' },
        { type: 'new_entry', label: '🚀 신규 진입', displayLabel: '신규 진입' },
        { type: 'rank_drop', label: '📉 순위 하락', displayLabel: '순위 하락' }
    ];
    
    segmentTabs.forEach((tab, index) => {
        const button = document.createElement('button');
        button.className = 'market-trend-tab-btn';
        if (index === 0) button.classList.add('active');
        button.setAttribute('data-segment', tab.type);
        button.textContent = tab.displayLabel;
        tabs.appendChild(button);
    });
    
    tabsWrapper.appendChild(tabs);
    section3Container.appendChild(tabsWrapper);
    
    // 콘텐츠 영역 생성
    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'trend-section3-content-wrapper';
    contentWrapper.id = 'section3Content';
    
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

// Section 3 세그먼트 콘텐츠 렌더링 (카테고리별 Card UI + 통합 헤더)
function renderSection3SegmentContent(segmentType, segmentText, container) {
    console.log('[renderSection3SegmentContent] 호출됨:', segmentType, '텍스트 길이:', segmentText ? segmentText.length : 0);
    
    if (!segmentText || !segmentText.trim()) {
        console.warn('[renderSection3SegmentContent] 세그먼트 텍스트 없음');
        container.innerHTML = '<div class="trend-analysis-empty">분석 데이터가 없습니다.</div>';
        return;
    }
    
    // 세그먼트 헤더 제거 (🔥 급상승 (Rising Star) 등)
    let cleanedText = segmentText;
    cleanedText = cleanedText.replace(/^\*\*?[🔥🚀📉]\s*(급상승|신규 진입|순위 하락)\s*\([^\)]+\)\*\*?\s*\n*/m, '');
    cleanedText = cleanedText.replace(/^\*\*?(Rising Star|New Entry|Rank Drop)\*\*?\s*\n*/m, '');
    cleanedText = cleanedText.trim();
    
    console.log('[renderSection3SegmentContent] cleanedText 길이:', cleanedText.length);
    console.log('[renderSection3SegmentContent] cleanedText 첫 500자:', cleanedText.substring(0, 500));
    
    // 카테고리별로 텍스트 파싱
    const categories = ['상의', '바지', '스커트', '원피스', '니트웨어', '셋업'];
    const categoryData = {};
    
    // 각 카테고리별로 텍스트 추출 (인덱스 기반으로 변경하여 모든 bullet point 포함)
    const lines = cleanedText.split('\n');
    const categoryIndices = {};
    
    // 각 카테고리 헤더 위치 찾기
    categories.forEach(categoryName => {
        const headerPattern = `**${categoryName}:**`;
        const index = lines.findIndex(line => line.trim() === headerPattern || line.trim().includes(headerPattern));
        if (index >= 0) {
            categoryIndices[categoryName] = index;
        }
    });
    
    // 각 카테고리별로 텍스트 추출
    categories.forEach((categoryName, catIndex) => {
        const startIndex = categoryIndices[categoryName];
        
        if (startIndex === undefined || startIndex < 0) {
            console.warn(`[Section 3] ${categoryName} 카테고리 헤더를 찾을 수 없습니다.`);
            return;
        }
        
        // 다음 카테고리 헤더의 위치 찾기 (또는 텍스트 끝)
        let endIndex = lines.length;
        if (catIndex < categories.length - 1) {
            for (let i = catIndex + 1; i < categories.length; i++) {
                const nextCategoryStart = categoryIndices[categories[i]];
                if (nextCategoryStart !== undefined && nextCategoryStart >= 0) {
                    endIndex = nextCategoryStart;
                    break;
                }
            }
        }
        
        // 카테고리 텍스트 추출 (헤더 다음 줄부터 다음 카테고리 헤더 전까지)
        const categoryLines = lines.slice(startIndex + 1, endIndex);
        let categoryText = categoryLines.join('\n').trim();
        
        console.log(`[renderSection3SegmentContent] ${categoryName} 추출된 텍스트 길이:`, categoryText.length);
        console.log(`[renderSection3SegmentContent] ${categoryName} 추출된 텍스트 첫 200자:`, categoryText.substring(0, 200));
        
        // 빈 텍스트 체크
        if (!categoryText || categoryText.length === 0) {
            console.warn(`[Section 3] ${categoryName} 카테고리 텍스트가 비어있습니다.`);
            return;
        }
        
        // 마크다운을 HTML로 변환
        if (typeof marked !== 'undefined') {
            try {
                marked.setOptions({
                    breaks: true,
                    gfm: false
                });
                
                const markdownHtml = marked.parse(categoryText);
                
                if (typeof DOMPurify !== 'undefined') {
                    categoryText = DOMPurify.sanitize(markdownHtml, {
                        ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'blockquote'],
                        ALLOWED_ATTR: []
                    });
                } else {
                    categoryText = markdownHtml;
                }
                
                console.log(`[renderSection3SegmentContent] ${categoryName} 마크다운 변환 후 길이:`, categoryText.length);
            } catch (e) {
                console.warn(`[Section 3] ${categoryName} 마크다운 변환 실패:`, e);
                categoryText = categoryText.replace(/\n/g, '<br>');
            }
        } else {
            categoryText = categoryText.replace(/\n/g, '<br>');
        }
        
        categoryData[categoryName] = categoryText;
    });
    
    // 디버깅: 파싱된 카테고리 데이터 확인
    console.log('[renderSection3SegmentContent] 파싱된 카테고리 데이터:', Object.keys(categoryData));
    console.log('[renderSection3SegmentContent] 카테고리 데이터 상세:', categoryData);
    
    // 컨테이너 초기화
    container.innerHTML = '';
    
    // 각 카테고리에 대해 Card UI 생성
    categories.forEach(categoryName => {
        const categoryText = categoryData[categoryName];
        
        console.log(`[renderSection3SegmentContent] ${categoryName} 카테고리 렌더링 시작, categoryText 존재:`, !!categoryText);
        
        // 카테고리 데이터가 없으면 스킵
        if (!categoryText) {
            console.log(`[renderSection3SegmentContent] ${categoryName} 카테고리 데이터 없음, 스킵`);
            return;
        }
        
        // Card 컨테이너 생성
        const cardContainer = document.createElement('div');
        cardContainer.className = 'trend-category-card';
        
        // 통합 헤더 영역 생성
        const headerSection = document.createElement('div');
        headerSection.className = 'trend-category-header';
        
        // 카테고리 뱃지 (콜론 제거)
        const categoryBadge = document.createElement('span');
        categoryBadge.className = 'trend-category-badge';
        categoryBadge.textContent = categoryName; // 콜론 없이
        
        // AI 분석 텍스트 영역
        const analysisSection = document.createElement('div');
        analysisSection.className = 'trend-category-analysis';
        
        // categoryText가 HTML로 변환된 상태이므로 그대로 삽입
        const insight = document.createElement('div');
        insight.className = 'trend-category-insight';
        insight.innerHTML = categoryText;
        analysisSection.appendChild(insight);
        
        // 헤더 섹션 구성
        headerSection.appendChild(categoryBadge);
        headerSection.appendChild(analysisSection);
        
        // Card에 헤더 먼저 추가
        cardContainer.appendChild(headerSection);
        
        // 썸네일 그리드 컨테이너 미리 생성 (레이아웃 시프트 방지)
        const gridContainer = document.createElement('div');
        gridContainer.className = 'trend-category-thumbnails';
        cardContainer.appendChild(gridContainer);
        
        // 썸네일 그리드 생성 (allTabsData 준비될 때까지 대기)
        const addThumbnails = () => {
            if (window.allTabsData && Object.keys(window.allTabsData).length > 0) {
                const categoryProducts = getProductsByCategory(categoryName, segmentType);
                if (categoryProducts.length > 0) {
                    const thumbnailGrid = createThumbnailGridFromProducts(categoryProducts, segmentType);
                    if (thumbnailGrid) {
                        gridContainer.innerHTML = thumbnailGrid;
                    }
                }
            } else {
                // allTabsData가 없으면 재시도
                const retryCount = (addThumbnails.retryCount || 0) + 1;
                addThumbnails.retryCount = retryCount;
                
                if (retryCount < 50) {
                    setTimeout(addThumbnails, 100);
                }
            }
        };
        
        // 썸네일 추가 시도
        setTimeout(addThumbnails, 100);
        
        container.appendChild(cardContainer);
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
    const categories = ['상의', '바지', '스커트', '원피스', '니트웨어', '셋업'];
    
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
