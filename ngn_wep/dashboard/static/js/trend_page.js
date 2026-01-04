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
    setupHamburgerMenu();
    setupTrendTypeTabs();
});

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
                showMoreBtn.textContent = `더보기 (${sortedData.length - INITIAL_ITEMS}개 더)`;
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
