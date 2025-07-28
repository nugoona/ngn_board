// File: ngn_wep/dashboard/static/js/mobile_dashboard.js
// 모바일 대시보드 JavaScript 엔트리포인트

// ─────────────────────────────────────────────
// 1) 전역 변수
// ─────────────────────────────────────────────
let mobileData = null;
let isLoading = false;

// ─────────────────────────────────────────────
// 2) 유틸리티 함수
// ─────────────────────────────────────────────
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toLocaleString();
}

function formatCurrency(num) {
    return '₩' + num.toLocaleString();
}

function formatPercentage(num) {
    return num.toFixed(1) + '%';
}

// ─────────────────────────────────────────────
// 3) API 호출 함수
// ─────────────────────────────────────────────
async function fetchMobileData() {
    if (isLoading) return;
    
    isLoading = true;
    console.log('🔄 모바일 데이터 로딩 시작...');
    
    try {
        // POST 요청으로 변경 (기존 웹과 동일한 방식)
        const response = await fetch('/m/get_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                company_name: 'all',  // 기본값
                period: 'last7days',  // 모바일 기본값: 최근 7일
                data_type: 'all'
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ 모바일 데이터 로딩 성공:', data);
        
        // 2단계: 실제 데이터 렌더링
        mobileData = data;
        
        // 마지막 업데이트 시간 표시
        const lastUpdated = document.getElementById('last-updated');
        if (lastUpdated && data.last_updated) {
            const date = new Date(data.last_updated);
            lastUpdated.textContent = `업데이트: ${date.toLocaleTimeString()}`;
        }
        
        // 실제 데이터 렌더링
        renderMobileData(data);
        
    } catch (error) {
        console.error('❌ 모바일 데이터 로딩 실패:', error);
        showError('데이터 로드 실패');
    } finally {
        isLoading = false;
    }
}

// ─────────────────────────────────────────────
// 4) 에러 처리 함수
// ─────────────────────────────────────────────
function showError(message) {
    console.error('🚨 에러:', message);
    // 1단계: 콘솔에만 표시
    // 2단계에서 toast 메시지 구현 예정
}

// ─────────────────────────────────────────────
// 5) 필터 이벤트 핸들러
// ─────────────────────────────────────────────
function setupFilters() {
    const companySelect = document.getElementById('company-select');
    const startDate = document.getElementById('start-date');
    
    if (companySelect) {
        companySelect.addEventListener('change', () => {
            console.log('🏢 업체 변경:', companySelect.value);
            // 2단계에서 API 재호출 구현 예정
        });
    }
    
    if (startDate) {
        startDate.addEventListener('change', () => {
            console.log('📅 날짜 변경:', startDate.value);
            // 2단계에서 API 재호출 구현 예정
        });
    }
}

// ─────────────────────────────────────────────
// 6) 초기화 함수
// ─────────────────────────────────────────────
function initMobileDashboard() {
    console.log('🚀 모바일 대시보드 초기화 시작...');
    
    // 필터 설정
    setupFilters();
    
    // 초기 데이터 로드
    fetchMobileData();
    
    console.log('✅ 모바일 대시보드 초기화 완료');
}

// ─────────────────────────────────────────────
// 7) DOM 로드 시 초기화
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', initMobileDashboard);

// ─────────────────────────────────────────────
// 7) 데이터 렌더링 함수
// ─────────────────────────────────────────────
function renderMobileData(data) {
    console.log('🎨 모바일 데이터 렌더링 시작...');
    
    // 1. KPI 카드 렌더링
    renderKPICards(data.kpi);
    
    // 2. 사이트 성과 렌더링
    renderSitePerformance(data.site_perf);
    
    // 3. 상위 상품 렌더링
    renderTopProducts(data.top_products);
    
    // 4. 상위 소스 렌더링
    renderTopSources(data.top_sources);
    
    // 5. 메타 광고 렌더링
    renderMetaAds(data.meta_ads);
    
    // 6. LIVE 광고 렌더링
    renderLiveAds(data.live_ads);
    
    console.log('✅ 모바일 데이터 렌더링 완료');
}

function renderKPICards(kpiData) {
    const kpiCards = document.querySelectorAll('#m-kpi-cards .kpi-card');
    if (!kpiCards.length) return;
    
    // KPI 카드 순서: 매출, 방문자, 광고비, 구매수, ROAS
    const kpiLabels = ['매출', '방문자', '광고비', '구매수', 'ROAS'];
    const kpiValues = [
        kpiData.revenue,
        kpiData.visitors,
        kpiData.ad_spend,
        kpiData.purchases,
        kpiData.roas
    ];
    
    kpiCards.forEach((card, index) => {
        if (index < kpiLabels.length) {
            // 스켈레톤 제거
            card.innerHTML = '';
            
            // 실제 데이터 표시
            card.innerHTML = `
                <div class="text-sm text-gray-600 mb-1">${kpiLabels[index]}</div>
                <div class="text-lg font-bold text-gray-900">
                    ${index === 0 || index === 2 ? formatCurrency(kpiValues[index]) : 
                      index === 4 ? formatPercentage(kpiValues[index]) : 
                      formatNumber(kpiValues[index])}
                </div>
            `;
        }
    });
}

function renderSitePerformance(siteData) {
    const sitePerf = document.getElementById('m-site-perf');
    if (!sitePerf) return;
    
    // 스켈레톤 제거
    sitePerf.innerHTML = `
        <div class="flex justify-between p-3 bg-gray-50 rounded-xl">
            <div class="flex-1">
                <div class="text-sm text-gray-600 mb-1">주문수</div>
                <div class="text-lg font-bold text-gray-900">${formatNumber(siteData.orders)}</div>
            </div>
            <div class="flex-1 text-right">
                <div class="text-sm text-gray-600 mb-1">상품매출</div>
                <div class="text-lg font-bold text-gray-900">${formatCurrency(siteData.product_sales)}</div>
            </div>
        </div>
    `;
}

function renderTopProducts(products) {
    const productsContainer = document.getElementById('m-top-products');
    if (!productsContainer) return;
    
    const productsList = productsContainer.querySelector('.bg-white');
    if (!productsList) return;
    
    // 스켈레톤 제거
    productsList.innerHTML = '';
    
    if (products.length === 0) {
        productsList.innerHTML = '<div class="p-4 text-center text-gray-500">데이터가 없습니다</div>';
        return;
    }
    
    // 실제 데이터 표시
    products.forEach(product => {
        const productItem = document.createElement('div');
        productItem.className = 'flex justify-between items-center p-3 border-b border-gray-100';
        productItem.innerHTML = `
            <div class="flex-1 text-sm text-gray-900">${product.name}</div>
            <div class="text-sm font-semibold text-gray-700">${formatNumber(product.qty)}</div>
        `;
        productsList.appendChild(productItem);
    });
}

function renderTopSources(sources) {
    const sourcesContainer = document.getElementById('m-top-sources');
    if (!sourcesContainer) return;
    
    const sourcesList = sourcesContainer.querySelector('.bg-white');
    if (!sourcesList) return;
    
    // 스켈레톤 제거
    sourcesList.innerHTML = '';
    
    if (sources.length === 0) {
        sourcesList.innerHTML = '<div class="p-4 text-center text-gray-500">데이터가 없습니다</div>';
        return;
    }
    
    // 실제 데이터 표시
    sources.forEach(source => {
        const sourceItem = document.createElement('div');
        sourceItem.className = 'flex justify-between items-center p-3 border-b border-gray-100';
        sourceItem.innerHTML = `
            <div class="flex-1 text-sm text-gray-900">${source.source}</div>
            <div class="text-sm font-semibold text-gray-700">${formatNumber(source.visits)}</div>
        `;
        sourcesList.appendChild(sourceItem);
    });
}

function renderMetaAds(metaData) {
    const metaContainer = document.getElementById('m-meta-ads');
    if (!metaContainer) return;
    
    const tableBody = metaContainer.querySelector('tbody');
    if (!tableBody) return;
    
    // 스켈레톤 제거
    tableBody.innerHTML = '';
    
    if (!metaData.rows || metaData.rows.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" class="p-4 text-center text-gray-500">데이터가 없습니다</td></tr>';
        return;
    }
    
    // 실제 데이터 표시
    metaData.rows.forEach(row => {
        const tableRow = document.createElement('tr');
        tableRow.className = 'border-b border-gray-100';
        tableRow.innerHTML = `
            <td class="p-2 text-sm text-gray-900">${row.campaign}</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatCurrency(row.spend)}</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatCurrency(row.cpc)}</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatNumber(row.purchases)}</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatPercentage(row.roas)}</td>
        `;
        tableBody.appendChild(tableRow);
    });
}

function renderLiveAds(liveAds) {
    const liveContainer = document.getElementById('m-live-ads');
    if (!liveContainer) return;
    
    const liveList = liveContainer.querySelector('.flex.overflow-x-scroll');
    if (!liveList) return;
    
    // 스켈레톤 제거
    liveList.innerHTML = '';
    
    if (liveAds.length === 0) {
        liveList.innerHTML = '<div class="p-4 text-center text-gray-500">데이터가 없습니다</div>';
        return;
    }
    
    // 실제 데이터 표시
    liveAds.forEach(ad => {
        const adCard = document.createElement('div');
        adCard.className = 'w-64 h-48 bg-white rounded-xl shadow-sm flex-shrink-0 border border-gray-200';
        adCard.innerHTML = `
            <div class="h-32 bg-gray-200 rounded-t-xl flex items-center justify-center">
                <img src="${ad.image_url}" alt="광고" class="w-full h-full object-cover rounded-t-xl" onerror="this.style.display='none'">
            </div>
            <div class="p-3">
                <div class="text-sm font-semibold text-gray-900">${ad.headline}</div>
            </div>
        `;
        liveList.appendChild(adCard);
    });
}

// ─────────────────────────────────────────────
// 8) 디버깅용 전역 함수 (개발용)
// ─────────────────────────────────────────────
window.mobileDashboard = {
    fetchData: fetchMobileData,
    getData: () => mobileData,
    isLoading: () => isLoading,
    renderData: renderMobileData
}; 