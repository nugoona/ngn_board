// File: ngn_wep/dashboard/static/js/mobile_dashboard.js
// 모바일 대시보드 JavaScript - 웹버전과 동일한 구조, 데이터만 축소

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
    if (num === null || num === undefined) return '--';
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toLocaleString();
}

function formatCurrency(num) {
    if (num === null || num === undefined) return '--';
    return '₩' + num.toLocaleString();
}

function formatPercentage(num) {
    if (num === null || num === undefined) return '--';
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
        const endDate = document.getElementById('end-date');
        const periodSelect = document.getElementById('period-filter');
        
        const companyName = companySelect ? companySelect.value : 'all';
        const period = periodSelect ? periodSelect.value : 'today';
        const startDateValue = startDate ? startDate.value : '';
        const endDateValue = endDate ? endDate.value : '';
        
        console.log('📊 필터 값:', { companyName, period, startDateValue, endDateValue });
        
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
        const endDate = document.getElementById('end-date');
        
        const period = periodSelect ? periodSelect.value : 'today';
        const startDateValue = startDate ? startDate.value : '';
        const endDateValue = endDate ? endDate.value : '';
        
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
    const endDate = document.getElementById('end-date');
    const periodSelect = document.getElementById('period-filter');
    const metaAccountSelect = document.getElementById('meta-account-select');
    
    // 기간 필터 변경 시
    if (periodSelect) {
        periodSelect.addEventListener('change', () => {
            console.log('📅 기간 변경:', periodSelect.value);
            
            // 직접 선택 모드일 때 날짜 입력 필드 표시/숨김
            const dateRangeRow = document.getElementById('date-range-row');
            if (dateRangeRow) {
                if (periodSelect.value === 'custom') {
                    dateRangeRow.style.display = 'flex';
                } else {
                    dateRangeRow.style.display = 'none';
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
            console.log('📅 시작일 변경:', startDate.value);
            fetchMobileData(); // API 재호출
            
            // 메타 광고 계정이 선택되어 있으면 광고별 성과도 업데이트
            if (selectedMetaAccount) {
                fetchMetaAdsByAccount(selectedMetaAccount);
            }
        });
    }
    
    if (endDate) {
        endDate.addEventListener('change', () => {
            console.log('📅 종료일 변경:', endDate.value);
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
// 11) 데이터 렌더링 함수 (요구사항에 맞게 구현)
// ─────────────────────────────────────────────
function renderMobileData(data) {
    console.log('🎨 모바일 데이터 렌더링 시작...');
    
    // 1. 사이트 성과 요약 (핵심 KPI)
    if (data.performance_summary && data.performance_summary.length > 0) {
        renderPerformanceSummary(data.performance_summary[0]);
    }
    
    // 2. 카페24 상품판매
    if (data.cafe24_product_sales) {
        renderCafe24ProductSales(data.cafe24_product_sales);
    }
    
    // 3. GA4 소스별 유입수
    if (data.ga4_source_summary) {
        renderGa4SourceSummary(data.ga4_source_summary);
    }
    
    // 4. 메타 광고 (기본 계정별 성과)
    if (data.meta_ads) {
        renderMetaAds(data.meta_ads);
    }
    
    console.log('✅ 모바일 데이터 렌더링 완료');
}

// 사이트 성과 요약 렌더링 (핵심 KPI)
function renderPerformanceSummary(performanceData) {
    console.log('📊 사이트 성과 요약 렌더링:', performanceData);
    
    // KPI 값들 설정
    document.getElementById('site-revenue').textContent = formatCurrency(performanceData.site_revenue || 0);
    document.getElementById('total-visitors').textContent = formatNumber(performanceData.total_visitors || 0);
    document.getElementById('ad-spend').textContent = formatCurrency(performanceData.ad_spend || 0);
    document.getElementById('total-purchases').textContent = formatNumber(performanceData.total_purchases || 0);
    document.getElementById('roas').textContent = formatPercentage(performanceData.roas_percentage || 0);
    
    // 사이트 성과 (주문수, 상품매출)
    document.getElementById('orders-count').textContent = formatNumber(performanceData.total_purchases || 0);
    document.getElementById('product-revenue').textContent = formatCurrency(performanceData.site_revenue || 0);
}

// 카페24 상품판매 렌더링
function renderCafe24ProductSales(products) {
    console.log('📦 카페24 상품판매 렌더링:', products);
    
    const tbody = document.getElementById('cafe24-products');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" class="text-center">데이터가 없습니다</td></tr>';
        return;
    }
    
    products.forEach(product => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="text-truncate">${product.item_product_name || '-'}</td>
            <td class="text-right">${formatNumber(product.item_qty || 0)}</td>
        `;
        tbody.appendChild(row);
    });
}

// GA4 소스별 유입수 렌더링
function renderGa4SourceSummary(sources) {
    console.log('🌐 GA4 소스별 유입수 렌더링:', sources);
    
    const tbody = document.getElementById('ga4-sources');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (sources.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" class="text-center">데이터가 없습니다</td></tr>';
        return;
    }
    
    sources.forEach(source => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="text-truncate">${source.source || '-'}</td>
            <td class="text-right">${formatNumber(source.visits || 0)}</td>
        `;
        tbody.appendChild(row);
    });
}

// 메타 광고 렌더링 (기본 계정별 성과)
function renderMetaAds(metaAds) {
    console.log('📊 메타 광고 렌더링:', metaAds);
    
    const tbody = document.getElementById('meta-ads-table');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (metaAds.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">데이터가 없습니다</td></tr>';
        return;
    }
    
    metaAds.forEach(row => {
        const tableRow = document.createElement('tr');
        tableRow.innerHTML = `
            <td class="text-truncate">${row.company_name || '-'}</td>
            <td class="text-truncate">-</td>
            <td class="text-right">${formatCurrency(row.total_spend || 0)}</td>
            <td class="text-right">${formatCurrency(row.cpc || 0)}</td>
            <td class="text-right">${formatNumber(row.total_purchases || 0)}</td>
            <td class="text-right">${formatPercentage(row.roas || 0)}</td>
        `;
        tbody.appendChild(tableRow);
    });
}

// 메타 광고 계정 필터 렌더링
function renderMetaAccountFilter(accounts) {
    console.log('🏢 메타 광고 계정 필터 렌더링:', accounts);
    
    const metaAccountFilter = document.getElementById('meta-account-filter');
    const metaAccountSelect = document.getElementById('meta-account-select');
    
    if (!metaAccountFilter || !metaAccountSelect) return;
    
    // 계정이 있으면 필터 표시
    if (accounts && accounts.length > 0) {
        metaAccountFilter.style.display = 'block';
        
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

// 메타 광고별 성과 렌더링 (광고 탭 기준)
function renderMetaAdsByAccount(adsData) {
    console.log('📊 메타 광고별 성과 렌더링:', adsData);
    
    const tbody = document.getElementById('meta-ads-table');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (adsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">데이터가 없습니다</td></tr>';
        return;
    }
    
    // 광고별 성과 데이터 렌더링
    adsData.forEach(row => {
        const tableRow = document.createElement('tr');
        tableRow.innerHTML = `
            <td class="text-truncate">${row.campaign_name || '-'}</td>
            <td class="text-truncate">${row.ad_name || '-'}</td>
            <td class="text-right">${formatCurrency(row.spend || 0)}</td>
            <td class="text-right">${formatCurrency(row.cpc || 0)}</td>
            <td class="text-right">${formatNumber(row.purchases || 0)}</td>
            <td class="text-right">${formatPercentage(row.roas || 0)}</td>
        `;
        tbody.appendChild(tableRow);
    });
    
    // 총합 로우 추가
    if (adsData.length > 0) {
        const totalSpend = adsData.reduce((sum, row) => sum + (row.spend || 0), 0);
        const totalPurchases = adsData.reduce((sum, row) => sum + (row.purchases || 0), 0);
        const totalCpc = adsData.reduce((sum, row) => sum + (row.cpc || 0), 0);
        const avgRoas = adsData.reduce((sum, row) => sum + (row.roas || 0), 0) / adsData.length;
        
        const totalRow = document.createElement('tr');
        totalRow.className = 'bg-gray-50 font-semibold';
        totalRow.innerHTML = `
            <td colspan="2" class="text-truncate">총합</td>
            <td class="text-right">${formatCurrency(totalSpend)}</td>
            <td class="text-right">${formatCurrency(totalCpc)}</td>
            <td class="text-right">${formatNumber(totalPurchases)}</td>
            <td class="text-right">${formatPercentage(avgRoas)}</td>
        `;
        tbody.appendChild(totalRow);
    }
}

// LIVE 광고 미리보기 렌더링
function renderLiveAds(liveAds) {
    console.log('🖼️ LIVE 광고 미리보기 렌더링:', liveAds);
    
    const liveAdsScroll = document.getElementById('live-ads-scroll');
    if (!liveAdsScroll) return;
    
    liveAdsScroll.innerHTML = '';
    
    if (liveAds.length === 0) {
        liveAdsScroll.innerHTML = '<div class="text-center">데이터가 없습니다</div>';
        return;
    }
    
    liveAds.forEach(ad => {
        const adCard = document.createElement('div');
        adCard.className = 'live-ad-card';
        adCard.innerHTML = `
            <div class="live-ad-image">
                <img src="${ad.image_url || ''}" alt="광고" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.style.display='none'">
            </div>
            <div class="live-ad-content">
                <div class="live-ad-title">${ad.headline || '광고 제목'}</div>
            </div>
        `;
        liveAdsScroll.appendChild(adCard);
    });
}

// LIVE 광고 섹션 표시/숨김
function showLiveAdsSection() {
    const liveAdsSection = document.getElementById('live-ads-section');
    if (liveAdsSection) {
        liveAdsSection.style.display = 'block';
    }
}

function hideLiveAdsSection() {
    const liveAdsSection = document.getElementById('live-ads-section');
    if (liveAdsSection) {
        liveAdsSection.style.display = 'none';
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