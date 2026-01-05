/**
 * 29CM 트렌드 페이지 JavaScript
 */

let currentTab = "전체";
let availableTabs = ["전체"];
let allTabsData = {}; // 모든 탭 데이터를 메모리에 저장 (비용 효율화)
let currentWeek = "";
let currentTrendType = "risingStar"; // 현재 선택된 트렌드 타입 (risingStar, newEntry, rankDrop)

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
    document.querySelectorAll('.trend-type-tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const trendType = this.dataset.type;
            
            // 활성화 상태 업데이트
            document.querySelectorAll('.trend-type-tab-btn').forEach(b => {
                b.classList.remove('active');
            });
            this.classList.add('active');
            
            // 트렌드 타입 변경
            currentTrendType = trendType;
            
            // 현재 탭 데이터 재표시
            displayCurrentTabData();
        });
    });
}

// 사용 가능한 탭 목록 로드
async function loadTabs() {
    try {
        const response = await fetch('/dashboard/trend/tabs');
        const data = await response.json();
        
        if (data.status === 'success' && data.tabs) {
            availableTabs = data.tabs;
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
        
        const response = await fetch('/dashboard/trend', {
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
            
            // 이미 AI 리포트가 렌더링되어 있으면 썸네일 업데이트 (방법 3)
            if (window.trendInsights && window.trendInsights.analysis_report) {
                const contentElement = document.getElementById('trendAnalysisContent');
                if (contentElement) {
                    const markdownContent = contentElement.querySelector('.trend-analysis-text');
                    if (markdownContent) {
                        // 이미 마크다운이 렌더링된 상태이므로 썸네일만 추가
                        renderSection3Thumbnails(contentElement, window.trendInsights.analysis_report);
                    }
                }
            }
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
        // 순위하락: 순위변화 오름차순 (음수, 작은 수 먼저)
        data = [...data].sort((a, b) => {
            const changeA = a.Rank_Change !== null ? a.Rank_Change : 0;
            const changeB = b.Rank_Change !== null ? b.Rank_Change : 0;
            return changeA - changeB;
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
            titleElement.textContent = `29CM ${weekInfo.year}년 ${weekInfo.month}월 ${weekInfo.week}주차 트렌드`;
        } else {
            titleElement.textContent = `29CM ${currentWeek} 트렌드`;
        }
    }
    
    // 사이드바 제목도 함께 업데이트
    updateTrendAnalysisTitle(currentWeek);
}

function updateTrendAnalysisTitle(currentWeek) {
    const analysisTitleElement = document.getElementById('trendAnalysisTitle');
    if (analysisTitleElement && currentWeek) {
        const weekInfo = parseWeekInfo(currentWeek);
        if (weekInfo) {
            analysisTitleElement.textContent = `29CM ${weekInfo.month}월 ${weekInfo.week}주차 트렌드 분석`;
        } else {
            analysisTitleElement.textContent = `29CM ${currentWeek} 트렌드 분석`;
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
    fetch('/dashboard/trend', {
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

// 트렌드 분석 리포트 렌더링 (마크다운 지원 + Section 3 썸네일 카드)
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
    
    // 마크다운을 HTML로 변환 (월간 리포트와 동일한 방식)
    let htmlContent = "";
    
    if (typeof marked !== 'undefined') {
        try {
            // 마크다운 설정
            marked.setOptions({
                breaks: true,  // 줄바꿈 지원
                gfm: false     // GitHub Flavored Markdown 비활성화 (표 제외)
            });
            
            // 마크다운을 HTML로 변환
            const markdownHtml = marked.parse(analysisText);
            
            // XSS 방지를 위해 DOMPurify로 정제
            if (typeof DOMPurify !== 'undefined') {
                htmlContent = DOMPurify.sanitize(markdownHtml, {
                    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote'],
                    ALLOWED_ATTR: []
                });
            } else {
                htmlContent = markdownHtml;
            }
        } catch (e) {
            console.warn("[트렌드 분석] 마크다운 변환 실패, 일반 텍스트로 표시:", e);
            htmlContent = analysisText.replace(/\n/g, '<br>');
        }
    } else {
        // marked 라이브러리가 없는 경우 줄바꿈만 처리
        htmlContent = analysisText.replace(/\n/g, '<br>');
    }
    
    contentElement.innerHTML = `<div class="trend-analysis-text markdown-content">${htmlContent}</div>`;
    
    // Section 3 썸네일 카드 그리드 추가 (방법 2: allTabsData 준비될 때까지 대기)
    const renderThumbnails = () => {
        if (window.allTabsData && Object.keys(window.allTabsData).length > 0) {
            renderSection3Thumbnails(contentElement, analysisText);
        } else {
            // allTabsData가 아직 준비되지 않았으면 재시도
            const retryCount = (renderThumbnails.retryCount || 0) + 1;
            renderThumbnails.retryCount = retryCount;
            
            if (retryCount < 50) { // 최대 5초 대기 (50 * 100ms)
                setTimeout(renderThumbnails, 100);
            } else {
                console.warn('[Section 3 썸네일] allTabsData 대기 시간 초과');
            }
        }
    };
    setTimeout(renderThumbnails, 100); // DOM 렌더링 후 실행
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

// Section 3 썸네일 카드 그리드 렌더링 (데이터 중심 접근, 세그먼트별 처리)
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
    
    // 현재 선택된 트렌드 타입 확인
    const activeTrendType = getActiveTrendType(); // 'rising_star', 'new_entry', 'rank_drop'
    
    // 세그먼트 헤더 매핑 (트렌드 타입 -> 세그먼트 헤더 텍스트 패턴)
    const segmentPatterns = {
        'rising_star': ['급상승', 'Rising Star', '🔥'],
        'new_entry': ['신규 진입', 'New Entry', '🚀'],
        'rank_drop': ['순위 하락', 'Rank Drop', '📉']
    };
    
    const activeSegmentPatterns = segmentPatterns[activeTrendType] || [];
    if (activeSegmentPatterns.length === 0) {
        console.warn('[Section 3 썸네일] 알 수 없는 트렌드 타입:', activeTrendType);
        return;
    }
    
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
            activeSegmentPatterns.some(pattern => textContent.includes(pattern) || innerHTML.includes(pattern));
        
        if (isSegmentHeader) {
            segmentStartIndex = i;
            break;
        }
    }
    
    if (segmentStartIndex === -1) {
        console.warn('[Section 3 썸네일] 활성화된 세그먼트 헤더를 찾을 수 없습니다:', activeTrendType);
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
        
        if (isOtherSegmentHeader && !activeSegmentPatterns.some(pattern => textContent.includes(pattern) || innerHTML.includes(pattern))) {
            segmentEndIndex = i;
            break;
        }
    }
    
    // 활성화된 세그먼트 내의 요소만 추출
    const segmentElements = allElements.slice(segmentStartIndex + 1, segmentEndIndex);
    
    // 카테고리 목록
    const categories = ['상의', '바지', '스커트', '원피스', '니트웨어', '셋업'];
    const processedCategories = new Set(); // 이미 처리한 카테고리 추적
    
    // 각 카테고리를 역순으로 처리 (뒤에서부터 삽입하면 인덱스가 안 꼬임)
    categories.reverse().forEach(categoryName => {
        if (processedCategories.has(categoryName)) return;
        
        // 카테고리 헤드라인 찾기 (세그먼트 내에서만)
        for (let i = 0; i < segmentElements.length; i++) {
            const element = segmentElements[i];
            const textContent = (element.textContent || '').trim();
            const innerHTML = (element.innerHTML || '').trim();
            
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
            
            if (isCategoryHeader) {
                // 해당 카테고리의 상품 데이터 추출 (데이터 중심)
                const categoryProducts = getProductsByCategory(categoryName, activeTrendType);
                
                if (categoryProducts.length > 0) {
                    // 썸네일 카드 그리드 생성
                    const thumbnailGrid = createThumbnailGridFromProducts(categoryProducts, activeTrendType);
                    
                    if (thumbnailGrid) {
                        // 헤드라인을 포함하는 문단(p 또는 li) 찾기
                        const parent = element.closest('p, li') || element.parentElement;
                        
                        if (parent) {
                            // 이미 썸네일이 삽입되지 않았는지 확인
                            let hasThumbnail = false;
                            let nextSibling = parent.nextElementSibling;
                            let checkCount = 0;
                            while (nextSibling && checkCount < 5) {
                                if (nextSibling.classList && nextSibling.classList.contains('trend-category-thumbnails')) {
                                    hasThumbnail = true;
                                    break;
                                }
                                nextSibling = nextSibling.nextElementSibling;
                                checkCount++;
                            }
                            
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
                                console.log(`[Section 3 썸네일] ${categoryName} 카테고리 (${activeTrendType})에 ${categoryProducts.length}개 썸네일 삽입 완료`);
                            }
                        }
                        
                        break; // 한 카테고리는 한 번만 처리
                    }
                }
            }
        }
    });
}

// 카테고리별 상품 데이터 추출 (데이터 중심)
function getProductsByCategory(categoryName, trendType) {
    if (!window.allTabsData) return [];
    
    const products = [];
    
    // 해당 카테고리의 탭 데이터 찾기
    const tabData = window.allTabsData[categoryName];
    if (!tabData) return [];
    
    // 현재 트렌드 타입에 해당하는 상품 추출
    const items = tabData[trendType] || [];
    
    items.forEach(item => {
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
        }
    });
    
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
    return products.slice(0, 6);
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
    // 탭 버튼에서 활성화된 버튼 확인
    const activeTab = document.querySelector('.trend-type-tab.active');
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
        tdProduct.textContent = item.Product_Name || '-';
        row.appendChild(tdProduct);
        
        // Rank Change (조건부)
        if (showRankChange) {
            const tdRankChange = document.createElement('td');
            tdRankChange.className = 'trend-rank-number';
            if (item.Rank_Change !== null && item.Rank_Change !== undefined) {
                const changeValue = item.Rank_Change;
                const isRising = changeValue > 0;
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
