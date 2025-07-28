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
// 3) 메타 광고 데이터 처리 함수 (모바일 전용)
// ─────────────────────────────────────────────
function processMetaAdsForMobile(metaAdsData) {
    console.log('🔧 메타 광고 데이터 모바일 처리 시작:', metaAdsData);
    
    return metaAdsData.map(row => {
        const processedRow = { ...row };
        
        // 캠페인명 처리: "전환", "도달", "유입" 키워드만 추출
        const campaignName = row.campaign_name || '';
        if (campaignName) {
            if (campaignName.includes('전환')) {
                processedRow.campaign_name = '전환';
            } else if (campaignName.includes('도달')) {
                processedRow.campaign_name = '도달';
            } else if (campaignName.includes('유입')) {
                processedRow.campaign_name = '유입';
            }
        }
        
        // 광고명 처리: [ ] 부분 제거
        const adName = row.ad_name || '';
        if (adName) {
            // [ ] 패턴을 모두 제거
            const cleanedAdName = adName.replace(/\[[^\]]*\]/g, '').trim();
            processedRow.ad_name = cleanedAdName;
        }
        
        return processedRow;
    });
}

// ─────────────────────────────────────────────
// 4) 웹버전과 호환되는 함수들 (filters.js 호환)
// ─────────────────────────────────────────────

// 웹버전의 updateAllData 함수와 동일한 역할
async function updateAllData() {
    console.log('🔄 모바일 updateAllData() 호출');
    await fetchMobileData();
}

// 웹버전의 fetchPerformanceSummaryData 함수와 동일한 역할
async function fetchPerformanceSummaryData() {
    console.log('🔄 모바일 fetchPerformanceSummaryData() 호출');
    await fetchMobileData();
}

// 웹버전의 fetchCafe24SalesData 함수와 동일한 역할
async function fetchCafe24SalesData() {
    console.log('🔄 모바일 fetchCafe24SalesData() 호출');
    await fetchMobileData();
}

// 웹버전의 fetchCafe24ProductSalesData 함수와 동일한 역할
async function fetchCafe24ProductSalesData() {
    console.log('🔄 모바일 fetchCafe24ProductSalesData() 호출');
    await fetchMobileData();
}

// 웹버전의 fetchGa4SourceSummaryData 함수와 동일한 역할
async function fetchGa4SourceSummaryData() {
    console.log('🔄 모바일 fetchGa4SourceSummaryData() 호출');
    await fetchMobileData();
}

// ─────────────────────────────────────────────
// 5) API 호출 함수 (웹버전과 동일한 구조)
// ─────────────────────────────────────────────
async function fetchMobileData() {
    if (isLoading) return;
    
    isLoading = true;
    console.log('🔄 모바일 데이터 로딩 시작...');
    
    try {
        // 현재 필터 값들 가져오기 (웹버전과 동일)
        const companySelect = document.getElementById('accountFilter');
        const startDate = document.getElementById('startDate');
        const endDate = document.getElementById('endDate');
        const periodSelect = document.getElementById('periodFilter');
        
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
        const updatedAtText = document.getElementById('updatedAtText');
        if (updatedAtText && data.latest_update) {
            try {
                console.log('🔍 원본 latest_update:', data.latest_update);
                
                // 다양한 날짜 형식 처리
                let dateStr = data.latest_update;
                
                // 2025-07-28-22-11 형식인 경우 처리
                if (dateStr.includes('-') && dateStr.split('-').length >= 5) {
                    const parts = dateStr.split('-');
                    const year = parts[0];
                    const month = parts[1];
                    const day = parts[2];
                    const hour = parts[3];
                    const minute = parts[4];
                    dateStr = `${year}-${month}-${day}T${hour}:${minute}:00`;
                    console.log('🔧 변환된 날짜 형식:', dateStr);
                }
                
                const utc = new Date(dateStr);
                
                // 유효한 날짜인지 확인
                if (isNaN(utc.getTime())) {
                    console.warn('❌ 유효하지 않은 날짜 형식:', data.latest_update);
                    updatedAtText.textContent = '최종 업데이트: -';
                    return;
                }
                
                // 시간만 보정 (날짜는 그대로 유지)
                const hours = utc.getUTCHours() + 9;
                const adjustedHour = hours % 24;
                const carryDate = hours >= 24 ? 1 : 0;
                
                const year = utc.getUTCFullYear();
                const month = utc.getUTCMonth() + 1;
                const date = utc.getUTCDate();
                const finalDate = date + carryDate;
                const minutes = utc.getUTCMinutes().toString().padStart(2, '0');
                
                const formatted = `${year}년 ${month}월 ${finalDate}일 ${adjustedHour}시 ${minutes}분`;
                updatedAtText.textContent = `최종 업데이트: ${formatted}`;
                console.log('✅ 업데이트 시간 표시 완료:', formatted);
            } catch (error) {
                console.error('❌ 업데이트 시간 처리 오류:', error);
                updatedAtText.textContent = '최종 업데이트: -';
            }
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
// 6) 메타 광고 계정 목록 조회
// ─────────────────────────────────────────────
async function fetchMetaAccounts() {
    try {
        const companySelect = document.getElementById('accountFilter');
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
// 7) 메타 광고별 성과 조회
// ─────────────────────────────────────────────
async function fetchMetaAdsByAccount(accountId) {
    if (!accountId) return;
    
    try {
        const periodSelect = document.getElementById('periodFilter');
        const startDate = document.getElementById('startDate');
        const endDate = document.getElementById('endDate');
        
        const companySelect = document.getElementById('accountFilter');
        const period = periodSelect ? periodSelect.value : 'today';
        const startDateValue = startDate ? startDate.value : '';
        const endDateValue = endDate ? endDate.value : '';
        const companyName = companySelect ? companySelect.value : 'all';
        
        const response = await fetch('/m/get_meta_ads_by_account', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                account_id: accountId,
                company_name: companyName,
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
// 8) LIVE 광고 미리보기 조회
// ─────────────────────────────────────────────
async function fetchLiveAds(accountId) {
    if (!accountId) return;
    
    try {
        const response = await fetch('/dashboard/get_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                data_type: 'meta_ads_preview_list',
                account_id: accountId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ LIVE 광고 미리보기 로딩 성공:', data);
        
        if (data.status === 'success' && data.meta_ads_preview_list) {
            renderLiveAds(data.meta_ads_preview_list);
            showLiveAdsSection();
        } else {
            console.warn('🔍 LIVE 광고 미리보기 데이터 없음');
            hideLiveAdsSection();
        }
        
    } catch (error) {
        console.error('❌ LIVE 광고 미리보기 로딩 실패:', error);
        hideLiveAdsSection();
    }
}

// ─────────────────────────────────────────────
// 9) 에러 처리 함수
// ─────────────────────────────────────────────
function showError(message) {
    console.error('🚨 에러:', message);
}

// ─────────────────────────────────────────────
// 10) 필터 이벤트 핸들러 (웹버전과 동일)
// ─────────────────────────────────────────────
function setupFilters() {
    const companySelect = document.getElementById('accountFilter');
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    const periodSelect = document.getElementById('periodFilter');
    const metaAccountSelect = document.getElementById('metaAccountSelector');
    
    // 기간 필터 변경 시
    if (periodSelect) {
        periodSelect.addEventListener('change', () => {
            console.log('📅 기간 변경:', periodSelect.value);
            
            // 직접 선택 모드일 때 날짜 입력 필드 표시/숨김
            const dateRangeContainer = document.getElementById('dateRangeContainer');
            if (dateRangeContainer) {
                if (periodSelect.value === 'manual') {
                    dateRangeContainer.style.display = 'flex';
                } else {
                    dateRangeContainer.style.display = 'none';
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
            
            // 메타 광고 계정 선택 초기화
            selectedMetaAccount = null;
            if (metaAccountSelect) {
                metaAccountSelect.value = '';
            }
            hideLiveAdsSection();
            
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
// 11) 초기화 함수
// ─────────────────────────────────────────────
function initMobileDashboard() {
    console.log('🚀 모바일 대시보드 초기화 시작...');
    
    // 웹버전과 동일한 업체명 자동 선택 로직
    setupCompanyAutoSelection();
    
    setupFilters();
    fetchMobileData();
    fetchMetaAccounts(); // 메타 광고 계정 목록 로드
    
    console.log('✅ 모바일 대시보드 초기화 완료');
}

// 웹버전과 동일한 업체명 자동 선택 로직
function setupCompanyAutoSelection() {
    const companySelect = document.getElementById('accountFilter');
    if (!companySelect) return;
    
    // 현재 사용자 정보 확인
    const isDemoUser = currentUserId === "demo";
    
    if (isDemoUser) {
        // demo 사용자는 demo만 선택
        companySelect.innerHTML = '<option value="demo" selected>demo</option>';
    } else {
        // 일반 사용자는 업체 목록에서 demo 제외
        const filteredCompanies = userCompanyList.filter(name => name.toLowerCase() !== "demo");
        
        if (filteredCompanies.length === 1) {
            // 업체가 1개면 자동 선택
            const company = filteredCompanies[0];
            companySelect.innerHTML = `<option value="${company.toLowerCase()}" selected>${company}</option>`;
        } else if (filteredCompanies.length > 1) {
            // 업체가 2개 이상이면 "모든 업체" 옵션 추가
            companySelect.innerHTML = '<option value="all" selected>모든 업체</option>';
            filteredCompanies.forEach(company => {
                const option = document.createElement('option');
                option.value = company.toLowerCase();
                option.textContent = company;
                companySelect.appendChild(option);
            });
        }
    }
    
    console.log('🏢 업체명 자동 선택 완료:', companySelect.value);
}

// ─────────────────────────────────────────────
// 12) DOM 로드 시 초기화
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', initMobileDashboard);

// ─────────────────────────────────────────────
// 13) 데이터 렌더링 함수 (요구사항에 맞게 구현)
// ─────────────────────────────────────────────
function renderMobileData(data) {
    console.log('🎨 모바일 데이터 렌더링 시작...');
    
    // 1. 사이트 성과 요약 (핵심 KPI)
    if (data.performance_summary && data.performance_summary.length > 0) {
        renderPerformanceSummary(data.performance_summary[0], data.total_orders);
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
function renderPerformanceSummary(performanceData, totalOrders) {
    console.log('📊 사이트 성과 요약 렌더링:', performanceData);
    
    // 사이트 성과 요약 KPI 값들 설정
    document.getElementById('site-revenue').textContent = formatCurrency(performanceData.site_revenue || 0);
    // 방문자는 K 없이 원래 숫자로 표시 (예: 1,278)
    const visitors = performanceData.total_visitors || 0;
    document.getElementById('total-visitors').textContent = visitors.toLocaleString();
    // 모바일 전용: total_orders 사용 (totalOrders가 있으면 사용, 없으면 total_purchases 사용)
    const ordersCount = totalOrders !== undefined ? totalOrders : (performanceData.total_purchases || 0);
    document.getElementById('orders-count').textContent = formatNumber(ordersCount);
    // 매출대비 광고비 (백분율로 표시)
    const adSpendRatio = performanceData.ad_spend_ratio || 0;
    document.getElementById('ad-spend-ratio').textContent = formatPercentage(adSpendRatio);
    
    // 광고 성과 요약 KPI 값들 설정
    document.getElementById('ad-spend').textContent = formatCurrency(performanceData.ad_spend || 0);
    document.getElementById('total-purchases').textContent = formatNumber(performanceData.total_purchases || 0);
    // avg_opo는 실제로 avg_cpc 필드입니다
    document.getElementById('cpc').textContent = formatCurrency(performanceData.avg_opo || performanceData.avg_cpc || 0);
    document.getElementById('roas').textContent = formatPercentage(performanceData.roas_percentage || 0);
    
    // 광고 성과 요약 제목에 광고 미디어 정보 추가
    const adMedia = performanceData.ad_media || '';
    const adPerformanceSection = document.querySelector('.section:nth-child(3) .section-header');
    if (adMedia && adPerformanceSection) {
        adPerformanceSection.textContent = `광고 성과 요약 - ${adMedia}`;
    }
}

// 카페24 상품판매 렌더링
function renderCafe24ProductSales(products) {
    console.log('📦 카페24 상품판매 렌더링:', products);
    
    const tbody = document.getElementById('cafe24-products');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center">데이터가 없습니다</td></tr>';
        return;
    }
    
    products.forEach(product => {
        const row = document.createElement('tr');
        const productName = product.product_name || '-';
        const salesAmount = product.item_product_sales || 0;
        
        row.innerHTML = `
            <td class="text-truncate" title="${productName}">${productName}</td>
            <td class="text-right">${formatNumber(product.item_quantity || 0)}</td>
            <td class="text-right">${formatCurrency(salesAmount)}</td>
        `;
        
        // 상품명 터치 시 전체 텍스트 표시 (모바일 전용)
        const productNameCell = row.querySelector('td[title]');
        if (productNameCell && productNameCell.title !== productNameCell.textContent) {
            productNameCell.addEventListener('click', function() {
                this.classList.toggle('expanded');
            });
        }
        
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
            <td class="text-right">${formatNumber(source.total_users || 0)}</td>
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
    
    // 모바일용 데이터 처리
    const processedMetaAds = processMetaAdsForMobile(metaAds);
    
    processedMetaAds.forEach(row => {
        const tableRow = document.createElement('tr');
        tableRow.innerHTML = `
            <td class="text-truncate">${row.campaign_name || '-'}</td>
            <td class="text-truncate">${row.ad_name || '-'}</td>
            <td class="text-right">${formatNumber(row.total_spend || 0)}</td>
            <td class="text-right">${formatNumber(row.cpc || 0)}</td>
            <td class="text-right">${formatNumber(row.total_purchases || 0)}</td>
            <td class="text-right">${formatNumber(row.roas || 0)}</td>
        `;
        tbody.appendChild(tableRow);
    });
}

// 메타 광고 계정 필터 렌더링
function renderMetaAccountFilter(accounts) {
    console.log('🏢 메타 광고 계정 필터 렌더링:', accounts);
    
    const metaAccountFilter = document.getElementById('meta-account-filter');
    const metaAccountSelect = document.getElementById('metaAccountSelector');
    
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
    
    // 모바일용 데이터 처리
    const processedAdsData = processMetaAdsForMobile(adsData);
    
    // 광고별 성과 데이터 렌더링
    processedAdsData.forEach(row => {
        const tableRow = document.createElement('tr');
        tableRow.innerHTML = `
            <td class="text-truncate">${row.campaign_name || '-'}</td>
            <td class="text-truncate">${row.ad_name || '-'}</td>
            <td class="text-right">${formatNumber(row.spend || 0)}</td>
            <td class="text-right">${formatNumber(row.cpc || 0)}</td>
            <td class="text-right">${formatNumber(row.purchases || 0)}</td>
            <td class="text-right">${formatNumber(row.roas || 0)}</td>
        `;
        tbody.appendChild(tableRow);
    });
    
    // 총합 로우 추가
    if (processedAdsData.length > 0) {
        const totalSpend = processedAdsData.reduce((sum, row) => sum + (row.spend || 0), 0);
        const totalPurchases = processedAdsData.reduce((sum, row) => sum + (row.purchases || 0), 0);
        const totalCpc = processedAdsData.reduce((sum, row) => sum + (row.cpc || 0), 0);
        const avgRoas = processedAdsData.reduce((sum, row) => sum + (row.roas || 0), 0) / processedAdsData.length;
        
        const totalRow = document.createElement('tr');
        totalRow.className = 'bg-gray-50 font-semibold';
        totalRow.innerHTML = `
            <td colspan="2" class="text-truncate">총합</td>
            <td class="text-right">${formatNumber(totalSpend)}</td>
            <td class="text-right">${formatNumber(totalCpc)}</td>
            <td class="text-right">${formatNumber(totalPurchases)}</td>
            <td class="text-right">${formatNumber(avgRoas)}</td>
        `;
        tbody.appendChild(totalRow);
    }
}

// LIVE 광고 미리보기 렌더링 (웹버전과 동일)
function renderLiveAds(liveAds) {
    console.log('🖼️ LIVE 광고 미리보기 렌더링:', liveAds);
    
    const liveAdsScroll = document.getElementById('live-ads-scroll');
    if (!liveAdsScroll) return;
    
    liveAdsScroll.innerHTML = '';
    
    if (liveAds.length === 0) {
        liveAdsScroll.innerHTML = '<div class="text-center" style="padding: 20px; color: #6b7280;">미리볼 광고가 없습니다.</div>';
        return;
    }
    
    liveAds.forEach(ad => {
        const adCard = document.createElement('div');
        adCard.className = 'live-ad-card';
        
        // 인스타그램 스타일 카드 생성
        const instagramAccName = ad.instagram_acc_name || 'No Name';
        const message = ad.message || '(문구 없음)';
        const firstLine = message.split('\n')[0];
        const shortCaption = `${instagramAccName} ${firstLine}...`;
        
        adCard.innerHTML = `
            <div class="live-ad-image">
                <img src="${ad.image_url || ''}" alt="광고" onerror="this.style.display='none'">
                ${ad.is_video ? '<div class="play-overlay" style="display: flex; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);"><svg viewBox="0 0 100 100" style="width: 40px; height: 40px;"><circle cx="50" cy="50" r="48" fill="rgba(0, 0, 0, 0.4)" /><polygon points="40,30 70,50 40,70" fill="white" /></svg></div>' : ''}
            </div>
            <div class="live-ad-content">
                <div class="live-ad-title">${shortCaption}</div>
                <div class="live-ad-link">${ad.link || '#'}</div>
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
// 14) 디버깅용 전역 함수 (개발용)
// ─────────────────────────────────────────────
window.mobileDashboard = {
    fetchData: fetchMobileData,
    getData: () => mobileData,
    isLoading: () => isLoading,
    renderData: renderMobileData,
    fetchMetaAccounts: fetchMetaAccounts,
    fetchMetaAdsByAccount: fetchMetaAdsByAccount,
    fetchLiveAds: fetchLiveAds,
    processMetaAdsForMobile: processMetaAdsForMobile
}; 