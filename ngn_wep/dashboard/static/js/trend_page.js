/**
 * 29CM 트렌드 페이지 JavaScript
 */

let currentTab = "전체";
let availableTabs = ["전체"];
let allTabsData = {}; // 모든 탭 데이터를 메모리에 저장 (비용 효율화)
let currentWeek = "";

// 페이지 로드 시 초기화
$(document).ready(function() {
    loadTabs().then(() => {
        // 탭 목록을 받은 후 모든 탭 데이터를 한 번에 로드
        loadAllTabsData();
    });
    setupHamburgerMenu();
});

// 햄버거 메뉴 설정 (common.js와 충돌 방지)
function setupHamburgerMenu() {
    // jQuery를 사용하여 common.js와 동일한 방식으로 처리
    $(document).ready(function() {
        $('#hamburgerIcon').off('click'); // 기존 이벤트 제거
        $('#hamburgerIcon').on('click', function(e) {
            e.stopPropagation();
            e.preventDefault();
            const $dropdown = $('#hamburgerDropdown');
            $dropdown.toggle();
        });
        
        // 외부 클릭 시 닫기
        $(document).on('click', function(e) {
            if (!$(e.target).closest('.hamburger-menu-wrapper').length) {
                $('#hamburgerDropdown').hide();
            }
        });
        
        // 드롭다운 내부 클릭 시 이벤트 전파 중지
        $('#hamburgerDropdown').on('click', function(e) {
            e.stopPropagation();
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

// 모든 탭 데이터를 한 번에 로드 (비용 효율화)
async function loadAllTabsData() {
    showLoading();
    
    try {
        const response = await fetch('/dashboard/trend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tab_names: availableTabs, // 모든 탭을 한 번에 요청
                trend_type: 'all'
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            currentWeek = data.current_week || "";
            updatePageTitle(currentWeek);
            
            // 모든 탭 데이터를 메모리에 저장
            if (data.tabs_data) {
                allTabsData = data.tabs_data;
            } else {
                // 단일 탭 응답인 경우 (하위 호환)
                allTabsData[currentTab] = {
                    rising_star: data.rising_star || [],
                    new_entry: data.new_entry || [],
                    rank_drop: data.rank_drop || []
                };
            }
            
            // 현재 탭 데이터 표시
            displayCurrentTabData();
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

// 현재 탭 데이터 표시
function displayCurrentTabData() {
    const tabData = allTabsData[currentTab];
    
    if (!tabData) {
        showError('데이터를 불러오는 중입니다...');
        return;
    }
    
    renderRisingStarTable(tabData.rising_star || []);
    renderNewEntryTable(tabData.new_entry || []);
    renderRankDropTable(tabData.rank_drop || []);
}

// 페이지 제목 업데이트
function updatePageTitle(currentWeek) {
    const titleElement = document.getElementById('trendPageTitle');
    if (titleElement && currentWeek) {
        const weekMatch = currentWeek.match(/(\d{4})W(\d{2})/);
        if (weekMatch) {
            const year = parseInt(weekMatch[1]);
            const week = parseInt(weekMatch[2]);
            
            // ISO 주차를 사용하여 월 계산
            // 첫 번째 주 목요일을 기준으로 주차 시작일 계산
            const jan4 = new Date(year, 0, 4);
            const jan4Day = jan4.getDay() || 7; // 일요일을 7로 변환
            const daysToThursday = 4 - jan4Day;
            const firstThursday = new Date(year, 0, 4 + daysToThursday);
            
            // 주차 시작일 (목요일 기준 월요일)
            const weekStartDate = new Date(firstThursday);
            weekStartDate.setDate(firstThursday.getDate() - 3 + (week - 1) * 7);
            const month = weekStartDate.getMonth() + 1;
            
            titleElement.textContent = `29CM ${year}년 ${month}월 ${week}주차 트렌드`;
        } else {
            titleElement.textContent = `29CM ${currentWeek} 트렌드`;
        }
    }
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
    
    // 스크롤 가능한 테이블 컨테이너 (초기에는 일반, 더보기 클릭 시 스크롤 활성화)
    const scrollWrapper = document.createElement('div');
    scrollWrapper.className = 'trend-table-scroll-wrapper';
    scrollWrapper.style.overflowY = 'visible'; // 초기에는 스크롤 없음
    scrollWrapper.style.maxHeight = 'none'; // 초기에는 높이 제한 없음
    
    const table = document.createElement('table');
    table.className = 'trend-table';
    table.id = `${tableId}Table`;
    
    // 테이블 헤더
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    
    const headers = [
        { text: '랭킹', key: 'ranking' },
        { text: '썸네일', key: 'thumbnail' },
        { text: '브랜드', key: 'brand' },
        { text: '상품명', key: 'product' },
        ...(showRankChange ? [{ text: '순위변화', key: 'rank_change' }] : []),
        { text: '이번주 순위', key: 'current_rank' },
        { text: '지난주 순위', key: 'previous_rank', hideMobile: true }
    ];
    
    headers.forEach(header => {
        const th = document.createElement('th');
        th.textContent = header.text;
        if (header.hideMobile) {
            th.className = 'hide-mobile';
        }
        headerRow.appendChild(th);
    });
    
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // 테이블 바디 (초기 5개만 표시)
    const tbody = document.createElement('tbody');
    tbody.id = `${tableId}Tbody`;
    table.appendChild(tbody);
    
    scrollWrapper.appendChild(table);
    wrapper.appendChild(scrollWrapper);
    
    // 페이지네이션 컨테이너
    const paginationDiv = document.createElement('div');
    paginationDiv.className = 'trend-pagination-container';
    paginationDiv.id = `${tableId}Pagination`;
    wrapper.appendChild(paginationDiv);
    
    // 초기 데이터 렌더링 (5개만)
    const INITIAL_ITEMS = 5;
    let currentShown = INITIAL_ITEMS;
    renderTableRows(data.slice(0, INITIAL_ITEMS), tbody, showRankChange, tableId);
    
    // 더보기/접기 버튼 생성
    if (data.length > INITIAL_ITEMS) {
        const showMoreBtn = document.createElement('button');
        showMoreBtn.className = 'trend-show-more-btn';
        showMoreBtn.textContent = `더보기 (${data.length - INITIAL_ITEMS}개 더)`;
        
        const collapseBtn = document.createElement('button');
        collapseBtn.className = 'trend-collapse-btn';
        collapseBtn.textContent = '접기';
        collapseBtn.style.display = 'none'; // 초기에는 숨김
        
        showMoreBtn.addEventListener('click', function() {
            const startIdx = currentShown;
            const endIdx = data.length; // 나머지 모두 표시
            const moreData = data.slice(startIdx, endIdx);
            
            renderTableRows(moreData, tbody, showRankChange, tableId);
            currentShown = endIdx;
            
            // 스크롤 활성화 및 헤더 고정
            scrollWrapper.style.overflowY = 'auto';
            scrollWrapper.style.maxHeight = '600px';
            
            // 버튼 상태 변경
            showMoreBtn.style.display = 'none';
            collapseBtn.style.display = 'inline-block';
        });
        
        collapseBtn.addEventListener('click', function() {
            // 초기 5개만 남기고 나머지 제거
            while (tbody.children.length > INITIAL_ITEMS) {
                tbody.removeChild(tbody.lastChild);
            }
            currentShown = INITIAL_ITEMS;
            
            // 스크롤 비활성화
            scrollWrapper.style.overflowY = 'visible';
            scrollWrapper.style.maxHeight = 'none';
            scrollWrapper.scrollTop = 0;
            
            // 버튼 상태 변경
            showMoreBtn.style.display = 'inline-block';
            collapseBtn.style.display = 'none';
            showMoreBtn.textContent = `더보기 (${data.length - INITIAL_ITEMS}개 더)`;
        });
        
        paginationDiv.appendChild(showMoreBtn);
        paginationDiv.appendChild(collapseBtn);
    }
    
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
        tdCurrentRank.textContent = item.This_Week_Rank !== null && item.This_Week_Rank !== undefined ? item.This_Week_Rank : '-';
        row.appendChild(tdCurrentRank);
        
        // Previous Rank (숫자 크게, 신규진입은 항상 '순위없음')
        const tdPreviousRank = document.createElement('td');
        tdPreviousRank.className = 'trend-rank-number hide-mobile';
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
