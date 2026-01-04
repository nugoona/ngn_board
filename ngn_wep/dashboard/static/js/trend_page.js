/**
 * 29CM 트렌드 페이지 JavaScript
 */

let currentTab = "전체";
let availableTabs = ["전체"];

// 페이지 로드 시 초기화
$(document).ready(function() {
    loadTabs();
    loadTrendData();
    setupHamburgerMenu();
});

// 햄버거 메뉴 설정
function setupHamburgerMenu() {
    const hamburgerIcon = document.getElementById('hamburgerIcon');
    const hamburgerDropdown = document.getElementById('hamburgerDropdown');
    
    if (hamburgerIcon && hamburgerDropdown) {
        hamburgerIcon.addEventListener('click', function(e) {
            e.stopPropagation();
            const isVisible = hamburgerDropdown.style.display === 'flex';
            hamburgerDropdown.style.display = isVisible ? 'none' : 'flex';
        });
        
        document.addEventListener('click', function() {
            hamburgerDropdown.style.display = 'none';
        });
        
        hamburgerDropdown.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }
}

// 사용 가능한 탭 목록 로드
async function loadTabs() {
    try {
        const response = await fetch('/dashboard/trend/tabs');
        const data = await response.json();
        
        if (data.status === 'success' && data.tabs) {
            availableTabs = data.tabs;
            renderTabs();
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

// 탭 전환
function switchTab(tabName) {
    if (currentTab === tabName) return;
    
    currentTab = tabName;
    
    // 탭 버튼 활성화 상태 업데이트
    document.querySelectorAll('.trend-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // 데이터 다시 로드
    loadTrendData();
}

// 트렌드 데이터 로드
async function loadTrendData() {
    // 로딩 상태 표시
    showLoading();
    
    try {
        const response = await fetch('/dashboard/trend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tab_name: currentTab,
                trend_type: 'all'
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // 페이지 제목 업데이트
            updatePageTitle(data.current_week);
            
            // 각 테이블 렌더링
            renderRisingStarTable(data.rising_star || []);
            renderNewEntryTable(data.new_entry || []);
            renderRankDropTable(data.rank_drop || []);
        } else {
            showError(data.message || '데이터를 불러오는데 실패했습니다.');
        }
    } catch (error) {
        console.error('[ERROR] 트렌드 데이터 로드 실패:', error);
        showError('데이터를 불러오는데 실패했습니다.');
    }
}

// 페이지 제목 업데이트
function updatePageTitle(currentWeek) {
    const titleElement = document.getElementById('trendPageTitle');
    if (titleElement && currentWeek) {
        // run_id를 주차 정보로 변환 (예: "2025W03_WEEKLY_POPULARITY_F_THIRTIES" -> "2025년 3주차")
        const weekMatch = currentWeek.match(/(\d{4})W(\d{2})/);
        if (weekMatch) {
            const year = weekMatch[1];
            const week = parseInt(weekMatch[2]);
            titleElement.textContent = `29CM ${year}년 ${week}주차 트렌드`;
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
    
    const table = createTable(data, true); // true = rank_change 컬럼 표시
    container.innerHTML = '';
    container.appendChild(table);
}

// 신규 진입 테이블 렌더링
function renderNewEntryTable(data) {
    const container = document.getElementById('newEntryTable');
    if (!container) return;
    
    if (data.length === 0) {
        container.innerHTML = '<div class="trend-empty">신규 진입 상품이 없습니다.</div>';
        return;
    }
    
    const table = createTable(data, false); // false = rank_change 컬럼 숨김
    container.innerHTML = '';
    container.appendChild(table);
}

// 순위 하락 테이블 렌더링
function renderRankDropTable(data) {
    const container = document.getElementById('rankDropTable');
    if (!container) return;
    
    if (data.length === 0) {
        container.innerHTML = '<div class="trend-empty">순위 하락 상품이 없습니다.</div>';
        return;
    }
    
    const table = createTable(data, true); // true = rank_change 컬럼 표시
    container.innerHTML = '';
    container.appendChild(table);
}

// 테이블 생성
function createTable(data, showRankChange) {
    const table = document.createElement('table');
    table.className = 'trend-table';
    
    // 테이블 헤더
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    
    const headers = [
        'Ranking',
        'Thumbnail',
        'Brand',
        'Product',
        ...(showRankChange ? ['Rank Change'] : []),
        'Current Rank',
        'Previous Rank'
    ];
    
    headers.forEach(header => {
        const th = document.createElement('th');
        th.textContent = header;
        if (header === 'Previous Rank' || (header === 'Rank Change' && !showRankChange)) {
            th.className = 'hide-mobile';
        }
        headerRow.appendChild(th);
    });
    
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // 테이블 바디
    const tbody = document.createElement('tbody');
    
    data.forEach((item, index) => {
        const row = document.createElement('tr');
        
        // Ranking
        const tdRanking = document.createElement('td');
        tdRanking.textContent = item.Ranking || `${index + 1}위`;
        row.appendChild(tdRanking);
        
        // Thumbnail
        const tdThumbnail = document.createElement('td');
        if (item.thumbnail_url) {
            const img = document.createElement('img');
            img.src = item.thumbnail_url;
            img.alt = item.Product_Name || '';
            img.className = 'trend-thumbnail';
            img.onerror = function() {
                this.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PCEtLSBJbWFnZSBub3QgZm91bmQgLS0+PC9zdmc+';
            };
            tdThumbnail.appendChild(img);
        } else {
            tdThumbnail.textContent = '-';
        }
        row.appendChild(tdThumbnail);
        
        // Brand
        const tdBrand = document.createElement('td');
        tdBrand.textContent = item.Brand_Name || '-';
        row.appendChild(tdBrand);
        
        // Product
        const tdProduct = document.createElement('td');
        tdProduct.textContent = item.Product_Name || '-';
        row.appendChild(tdProduct);
        
        // Rank Change (조건부)
        if (showRankChange) {
            const tdRankChange = document.createElement('td');
            if (item.Rank_Change !== null && item.Rank_Change !== undefined) {
                const changeValue = item.Rank_Change;
                // changeValue > 0: 순위 상승 (prev.rank - curr.rank > 0, 즉 prev > curr, 숫자는 작아짐)
                // changeValue < 0: 순위 하락 (prev.rank - curr.rank < 0, 즉 prev < curr, 숫자는 커짐)
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
        
        // Current Rank
        const tdCurrentRank = document.createElement('td');
        tdCurrentRank.textContent = item.This_Week_Rank !== null && item.This_Week_Rank !== undefined ? item.This_Week_Rank : '-';
        row.appendChild(tdCurrentRank);
        
        // Previous Rank
        const tdPreviousRank = document.createElement('td');
        tdPreviousRank.className = 'hide-mobile';
        tdPreviousRank.textContent = item.Last_Week_Rank !== null && item.Last_Week_Rank !== undefined ? item.Last_Week_Rank : '-';
        row.appendChild(tdPreviousRank);
        
        tbody.appendChild(row);
    });
    
    table.appendChild(tbody);
    return table;
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

