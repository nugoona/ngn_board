// File: ngn_wep/dashboard/static/js/mobile_dashboard.js
// 모바일 대시보드 JavaScript - 웹버전의 축소버전

// ─────────────────────────────────────────────
// 1) 전역 변수 (웹버전과 동일)
// ─────────────────────────────────────────────
let mobileData = null;
let isLoading = false;
let selectedMetaAccount = null;

// ─────────────────────────────────────────────
// 2) 유틸리티 함수 (웹버전과 동일)
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
// 3) API 호출 함수 (웹버전과 동일한 구조)
// ─────────────────────────────────────────────
async function fetchMobileData() {
    if (isLoading) return;
    
    isLoading = true;
    console.log('🔄 모바일 데이터 로딩 시작...');
    
    try {
        // 현재 필터 값들 가져오기 (웹버전과 동일)
        const companySelect = document.getElementById('company-select');
        const startDate = document.getElementById('start-date');
        const periodSelect = document.getElementById('period-filter');
        
        const companyName = companySelect ? companySelect.value : 'all';
        const period = periodSelect ? periodSelect.value : 'today';
        const startDateValue = startDate ? startDate.value : '';
        
        // 직접 선택 모드일 때는 시작일과 종료일을 동일하게 설정
        let endDateValue = startDateValue;
        if (period === 'custom' && startDateValue) {
            endDateValue = startDateValue;
        }
        
        // 웹버전과 동일한 API 호출
        const response = await fetch('/m/get_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                company_name: companyName,
                period: period,
                start_date: startDateValue,
                end_date: endDateValue,
                data_type: 'all'
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ 모바일 데이터 로딩 성공:', data);
        
        mobileData = data;
        
        // 웹버전과 동일한 업데이트 시간 표시
        const lastUpdated = document.getElementById('last-updated');
        if (lastUpdated && data.latest_update) {
            const date = new Date(data.latest_update.replace(/-/g, ':').replace('T', ' '));
            const timeString = date.toLocaleTimeString('ko-KR', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: true
            });
            lastUpdated.textContent = `업데이트: ${timeString}`;
        }
        
        // 웹버전과 동일한 데이터 렌더링
        renderMobileData(data);
        
    } catch (error) {
        console.error('❌ 모바일 데이터 로딩 실패:', error);
        showError('데이터 로드 실패');
    } finally {
        isLoading = false;
    }
}

// ─────────────────────────────────────────────
// 4) 메타 광고 계정 목록 조회
// ─────────────────────────────────────────────
async function fetchMetaAccounts() {
    try {
        const companySelect = document.getElementById('company-select');
        const companyName = companySelect ? companySelect.value : 'all';
        
        const response = await fetch('/m/get_meta_accounts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                company_name: companyName
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ 메타 광고 계정 목록 로딩 성공:', data);
        
        if (data.status === 'success' && data.meta_accounts) {
            renderMetaAccountFilter(data.meta_accounts);
        }
        
    } catch (error) {
        console.error('❌ 메타 광고 계정 목록 로딩 실패:', error);
    }
}

// ─────────────────────────────────────────────
// 5) 메타 광고별 성과 조회
// ─────────────────────────────────────────────
async function fetchMetaAdsByAccount(accountId) {
    if (!accountId) return;
    
    try {
        const periodSelect = document.getElementById('period-filter');
        const startDate = document.getElementById('start-date');
        
        const period = periodSelect ? periodSelect.value : 'today';
        const startDateValue = startDate ? startDate.value : '';
        
        let endDateValue = startDateValue;
        if (period === 'custom' && startDateValue) {
            endDateValue = startDateValue;
        }
        
        const response = await fetch('/m/get_meta_ads_by_account', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                account_id: accountId,
                period: period,
                start_date: startDateValue,
                end_date: endDateValue
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ 메타 광고별 성과 로딩 성공:', data);
        
        if (data.status === 'success' && data.meta_ads_by_account) {
            renderMetaAdsByAccount(data.meta_ads_by_account);
        }
        
    } catch (error) {
        console.error('❌ 메타 광고별 성과 로딩 실패:', error);
    }
}

// ─────────────────────────────────────────────
// 6) LIVE 광고 미리보기 조회
// ─────────────────────────────────────────────
async function fetchLiveAds(accountId) {
    if (!accountId) return;
    
    try {
        const response = await fetch('/m/get_live_ads', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                account_id: accountId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ LIVE 광고 미리보기 로딩 성공:', data);
        
        if (data.status === 'success' && data.live_ads) {
            renderLiveAds(data.live_ads);
        }
        
    } catch (error) {
        console.error('❌ LIVE 광고 미리보기 로딩 실패:', error);
    }
}

// ─────────────────────────────────────────────
// 7) 에러 처리 함수
// ─────────────────────────────────────────────
function showError(message) {
    console.error('🚨 에러:', message);
}

// ─────────────────────────────────────────────
// 8) 필터 이벤트 핸들러 (웹버전과 동일)
// ─────────────────────────────────────────────
function setupFilters() {
    const companySelect = document.getElementById('company-select');
    const startDate = document.getElementById('start-date');
    const periodSelect = document.getElementById('period-filter');
    const metaAccountSelect = document.getElementById('meta-account-select');
    
    // 기간 필터 변경 시
    if (periodSelect) {
        periodSelect.addEventListener('change', () => {
            console.log('📅 기간 변경:', periodSelect.value);
            
            // 직접 선택 모드일 때 날짜 입력 필드 표시/숨김
            if (startDate) {
                if (periodSelect.value === 'custom') {
                    startDate.style.display = 'block';
                } else {
                    startDate.style.display = 'none';
                }
            }
            
            fetchMobileData(); // API 재호출
            
            // 메타 광고 계정이 선택되어 있으면 광고별 성과도 업데이트
            if (selectedMetaAccount) {
                fetchMetaAdsByAccount(selectedMetaAccount);
            }
        });
    }
    
    // 업체 변경 시
    if (companySelect) {
        companySelect.addEventListener('change', () => {
            console.log('🏢 업체 변경:', companySelect.value);
            fetchMobileData(); // API 재호출
            fetchMetaAccounts(); // 메타 광고 계정 목록 업데이트
        });
    }
    
    // 날짜 변경 시
    if (startDate) {
        startDate.addEventListener('change', () => {
            console.log('📅 날짜 변경:', startDate.value);
            fetchMobileData(); // API 재호출
            
            // 메타 광고 계정이 선택되어 있으면 광고별 성과도 업데이트
            if (selectedMetaAccount) {
                fetchMetaAdsByAccount(selectedMetaAccount);
            }
        });
    }
    
    // 메타 광고 계정 선택 시
    if (metaAccountSelect) {
        metaAccountSelect.addEventListener('change', () => {
            const accountId = metaAccountSelect.value;
            console.log('📊 메타 광고 계정 변경:', accountId);
            
            selectedMetaAccount = accountId;
            
            if (accountId) {
                fetchMetaAdsByAccount(accountId);
                fetchLiveAds(accountId);
                showLiveAdsSection();
            } else {
                hideLiveAdsSection();
            }
        });
    }
}

// ─────────────────────────────────────────────
// 9) 초기화 함수
// ─────────────────────────────────────────────
function initMobileDashboard() {
    console.log('🚀 모바일 대시보드 초기화 시작...');
    
    setupFilters();
    fetchMobileData();
    fetchMetaAccounts(); // 메타 광고 계정 목록 로드
    
    console.log('✅ 모바일 대시보드 초기화 완료');
}

// ─────────────────────────────────────────────
// 10) DOM 로드 시 초기화
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', initMobileDashboard);

// ─────────────────────────────────────────────
// 11) 데이터 렌더링 함수 (웹버전과 동일한 구조)
// ─────────────────────────────────────────────
function renderMobileData(data) {
    console.log('🎨 모바일 데이터 렌더링 시작...');
    
    // 웹버전과 동일한 데이터 구조로 렌더링
    if (data.performance_summary && data.performance_summary.length > 0) {
        renderPerformanceSummary(data.performance_summary[0]);
    }
    
    if (data.cafe24_product_sales) {
        renderCafe24ProductSales(data.cafe24_product_sales);
    }
    
    if (data.ga4_source_summary) {
        renderGa4SourceSummary(data.ga4_source_summary);
    }
    
    if (data.meta_ads) {
        renderMetaAds(data.meta_ads);
    }
    
    console.log('✅ 모바일 데이터 렌더링 완료');
}

// Performance Summary 렌더링 (웹버전과 동일)
function renderPerformanceSummary(performanceData) {
    // KPI 카드 렌더링
    const kpiCards = document.querySelectorAll('#m-kpi-cards .kpi-card');
    if (!kpiCards.length) return;
    
    const kpiLabels = ['매출', '방문자', '광고비', '구매수', 'ROAS'];
    const kpiValues = [
        performanceData.site_revenue,
        performanceData.total_visitors,
        performanceData.ad_spend,
        performanceData.total_purchases,
        performanceData.roas_percentage
    ];
    
    kpiCards.forEach((card, index) => {
        if (index < kpiLabels.length) {
            card.innerHTML = '';
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
    
    // 사이트 성과 렌더링
    const sitePerf = document.getElementById('m-site-perf');
    if (sitePerf) {
        sitePerf.innerHTML = `
            <div class="flex justify-between p-3 bg-gray-50 rounded-xl">
                <div class="flex-1">
                    <div class="text-sm text-gray-600 mb-1">주문수</div>
                    <div class="text-lg font-bold text-gray-900">${formatNumber(performanceData.total_purchases)}</div>
                </div>
                <div class="flex-1 text-right">
                    <div class="text-sm text-gray-600 mb-1">상품매출</div>
                    <div class="text-lg font-bold text-gray-900">${formatCurrency(performanceData.site_revenue)}</div>
                </div>
            </div>
        `;
    }
}

// Cafe24 Product Sales 렌더링 (웹버전과 동일)
function renderCafe24ProductSales(products) {
    const productsContainer = document.getElementById('m-top-products');
    if (!productsContainer) return;
    
    const productsList = productsContainer.querySelector('.bg-white');
    if (!productsList) return;
    
    productsList.innerHTML = '';
    
    if (products.length === 0) {
        productsList.innerHTML = '<div class="p-4 text-center text-gray-500">데이터가 없습니다</div>';
        return;
    }
    
    products.forEach(product => {
        const productItem = document.createElement('div');
        productItem.className = 'flex justify-between items-center p-3 border-b border-gray-100';
        productItem.innerHTML = `
            <div class="flex-1 text-sm text-gray-900">${product.item_product_name}</div>
            <div class="text-sm font-semibold text-gray-700">${formatNumber(product.item_qty)}</div>
        `;
        productsList.appendChild(productItem);
    });
}

// GA4 Source Summary 렌더링 (웹버전과 동일)
function renderGa4SourceSummary(sources) {
    const sourcesContainer = document.getElementById('m-top-sources');
    if (!sourcesContainer) return;
    
    const sourcesList = sourcesContainer.querySelector('.bg-white');
    if (!sourcesList) return;
    
    sourcesList.innerHTML = '';
    
    if (sources.length === 0) {
        sourcesList.innerHTML = '<div class="p-4 text-center text-gray-500">데이터가 없습니다</div>';
        return;
    }
    
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

// Meta Ads 렌더링 (웹버전과 동일)
function renderMetaAds(metaAds) {
    const metaContainer = document.getElementById('m-meta-ads');
    if (!metaContainer) return;
    
    const tableBody = metaContainer.querySelector('tbody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    if (metaAds.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-gray-500">데이터가 없습니다</td></tr>';
        return;
    }
    
    metaAds.forEach(row => {
        const tableRow = document.createElement('tr');
        tableRow.className = 'border-b border-gray-100';
        tableRow.innerHTML = `
            <td class="p-2 text-sm text-gray-900 text-truncate">${row.company_name}</td>
            <td class="p-2 text-sm text-gray-900 text-truncate">-</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatCurrency(row.total_spend)}</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatCurrency(row.cpc)}</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatNumber(row.total_purchases)}</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatPercentage(row.roas)}</td>
        `;
        tableBody.appendChild(tableRow);
    });
}

// 메타 광고 계정 필터 렌더링
function renderMetaAccountFilter(accounts) {
    const metaAccountFilter = document.getElementById('meta-account-filter');
    const metaAccountSelect = document.getElementById('meta-account-select');
    
    if (!metaAccountFilter || !metaAccountSelect) return;
    
    // 계정이 있으면 필터 표시
    if (accounts && accounts.length > 0) {
        metaAccountFilter.style.display = 'flex';
        
        // 기존 옵션 제거 (기본 옵션 제외)
        metaAccountSelect.innerHTML = '<option value="">메타 광고 계정 선택</option>';
        
        // 계정 옵션 추가
        accounts.forEach(account => {
            const option = document.createElement('option');
            option.value = account.account_id;
            option.textContent = account.account_name;
            metaAccountSelect.appendChild(option);
        });
    } else {
        metaAccountFilter.style.display = 'none';
    }
}

// 메타 광고별 성과 렌더링
function renderMetaAdsByAccount(adsData) {
    const metaContainer = document.getElementById('m-meta-ads');
    if (!metaContainer) return;
    
    const tableBody = metaContainer.querySelector('tbody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    if (adsData.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-gray-500">데이터가 없습니다</td></tr>';
        return;
    }
    
    // 광고별 성과 데이터 렌더링
    adsData.forEach(row => {
        const tableRow = document.createElement('tr');
        tableRow.className = 'border-b border-gray-100';
        tableRow.innerHTML = `
            <td class="p-2 text-sm text-gray-900 text-truncate">${row.campaign_name || '-'}</td>
            <td class="p-2 text-sm text-gray-900 text-truncate">${row.ad_name || '-'}</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatCurrency(row.spend || 0)}</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatCurrency(row.cpc || 0)}</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatNumber(row.purchases || 0)}</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatPercentage(row.roas || 0)}</td>
        `;
        tableBody.appendChild(tableRow);
    });
    
    // 총합 로우 추가
    if (adsData.length > 0) {
        const totalSpend = adsData.reduce((sum, row) => sum + (row.spend || 0), 0);
        const totalPurchases = adsData.reduce((sum, row) => sum + (row.purchases || 0), 0);
        const totalCpc = adsData.reduce((sum, row) => sum + (row.cpc || 0), 0);
        const avgRoas = adsData.reduce((sum, row) => sum + (row.roas || 0), 0) / adsData.length;
        
        const totalRow = document.createElement('tr');
        totalRow.className = 'border-b border-gray-200 bg-gray-50 font-semibold';
        totalRow.innerHTML = `
            <td class="p-2 text-sm text-gray-900" colspan="2">총합</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatCurrency(totalSpend)}</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatCurrency(totalCpc)}</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatNumber(totalPurchases)}</td>
            <td class="p-2 text-sm text-right text-gray-700">${formatPercentage(avgRoas)}</td>
        `;
        tableBody.appendChild(totalRow);
    }
}

// LIVE 광고 미리보기 렌더링
function renderLiveAds(liveAds) {
    const liveContainer = document.getElementById('m-live-ads');
    if (!liveContainer) return;
    
    const liveList = liveContainer.querySelector('.flex.overflow-x-scroll');
    if (!liveList) return;
    
    liveList.innerHTML = '';
    
    if (liveAds.length === 0) {
        liveList.innerHTML = '<div class="p-4 text-center text-gray-500">데이터가 없습니다</div>';
        return;
    }
    
    liveAds.forEach(ad => {
        const adCard = document.createElement('div');
        adCard.className = 'w-64 h-48 bg-white rounded-xl shadow-sm flex-shrink-0 border border-gray-200';
        adCard.innerHTML = `
            <div class="h-32 bg-gray-200 rounded-t-xl flex items-center justify-center">
                <img src="${ad.image_url || ''}" alt="광고" class="w-full h-full object-cover rounded-t-xl" onerror="this.style.display='none'">
            </div>
            <div class="p-3">
                <div class="text-sm font-semibold text-gray-900 text-truncate">${ad.headline || '광고 제목'}</div>
            </div>
        `;
        liveList.appendChild(adCard);
    });
}

// LIVE 광고 섹션 표시/숨김
function showLiveAdsSection() {
    const liveContainer = document.getElementById('m-live-ads');
    if (liveContainer) {
        liveContainer.style.display = 'block';
    }
}

function hideLiveAdsSection() {
    const liveContainer = document.getElementById('m-live-ads');
    if (liveContainer) {
        liveContainer.style.display = 'none';
    }
}

// ─────────────────────────────────────────────
// 12) 디버깅용 전역 함수 (개발용)
// ─────────────────────────────────────────────
window.mobileDashboard = {
    fetchData: fetchMobileData,
    getData: () => mobileData,
    isLoading: () => isLoading,
    renderData: renderMobileData,
    fetchMetaAccounts: fetchMetaAccounts,
    fetchMetaAdsByAccount: fetchMetaAdsByAccount,
    fetchLiveAds: fetchLiveAds
}; 