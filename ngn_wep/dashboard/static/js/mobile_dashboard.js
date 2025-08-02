// File: ngn_wep/dashboard/static/js/mobile_dashboard.js
// 모바일 대시보드 JavaScript - 웹버전과 동일한 구조, 데이터만 축소

// 🔥 성능 최적화: 요청 중복 방지
// requestRegistry 제거 - 병렬 처리로 최적화

// ─────────────────────────────────────────────
// 1) 전역 변수 (웹버전과 동일)
// ─────────────────────────────────────────────
let mobileData = null;
let isLoading = false;
let selectedMetaAccount = null;

// 🚀 디바운싱을 위한 변수 추가
let fetchMobileDataTimeout = null;
const FETCH_DEBOUNCE_DELAY = 300; // 300ms 디바운스

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

// 🚀 디바운싱 함수 추가
function debounceFetchMobileData() {
    if (fetchMobileDataTimeout) {
        clearTimeout(fetchMobileDataTimeout);
    }
    
    fetchMobileDataTimeout = setTimeout(() => {
        console.log('🚀 디바운싱된 fetchMobileData 호출');
        fetchMobileData();
    }, FETCH_DEBOUNCE_DELAY);
}

// ================================
// 로딩 상태 관리 함수들 (웹버전과 동일)
// ================================

function showLoading(target) {
    console.log("🔄 showLoading called for:", target);
    
    const element = document.querySelector(target);
    console.log("Target element:", element);
    
    if (!element) {
        console.error("❌ Target element not found:", target);
        return;
    }
    
    // 🔥 더 강력한 스타일 설정 - 다른 코드가 덮어쓰지 못하도록
    element.style.display = 'flex';
    element.style.visibility = 'visible';
    element.style.opacity = '1';
    element.style.pointerEvents = 'auto';
    
    console.log("✅ Loading started for:", target);
    console.log("Final display style:", element.style.display);
}

function hideLoading(target) {
    console.log("✅ hideLoading called for:", target);
    
    const element = document.querySelector(target);
    
    if (!element) {
        console.error("❌ Target element not found:", target);
        return;
    }
    
    // 직접 스타일 설정
    element.style.display = 'none';
    element.style.visibility = 'hidden';
    element.style.opacity = '0';
    element.style.pointerEvents = 'none';
    
    console.log("✅ Loading completed for:", target);
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
async function fetchCafe24ProductSalesData(page = 1) {
    console.log('🔄 모바일 fetchCafe24ProductSalesData() 호출 - 페이지:', page);
    
    cafe24ProductSalesCurrentPage = page;
    
    try {
        const companySelect = document.getElementById('accountFilter');
        const startDate = document.getElementById('startDate');
        const endDate = document.getElementById('endDate');
        const periodSelect = document.getElementById('periodFilter');
        
        const companyName = companySelect ? companySelect.value : 'all';
        const period = periodSelect ? periodSelect.value : 'today';
        const startDateValue = startDate ? startDate.value : '';
        const endDateValue = endDate ? endDate.value : '';
        
        showLoading("#loadingOverlayCafe24Products");
        
        const response = await fetch('/dashboard/get_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                data_type: 'cafe24_product_sales',
                company_name: companyName,
                period: period,
                start_date: startDateValue,
                end_date: endDateValue,
                page: page,
                limit: 5
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ 카페24 상품판매 데이터 로딩 성공:', data);
        
        if (data.status === 'success' && data.cafe24_product_sales) {
            renderCafe24ProductSales(data.cafe24_product_sales, data.cafe24_product_sales_total_count);
            hideLoading("#loadingOverlayCafe24Products");  // 렌더링 후 로딩 숨김
        }
        
    } catch (error) {
        console.error('❌ 카페24 상품판매 데이터 로딩 실패:', error);
        hideLoading("#loadingOverlayCafe24Products");
    }
}

// 웹버전의 fetchGa4SourceSummaryData 함수와 동일한 역할
async function fetchGa4SourceSummaryData() {
    console.log('🔄 모바일 fetchGa4SourceSummaryData() 호출');
    await fetchMobileData();
}

// ─────────────────────────────────────────────
// 5) API 호출 함수 (웹버전과 동일한 단일 호출)
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
        
        // 🚀 웹버전과 동일한 병렬 API 호출로 최적화
        console.log('🚀 병렬 API 호출로 모든 데이터 로딩 시작...');
        
        // 실제 존재하는 로딩 스피너만 표시
        showLoading("#loadingOverlaySitePerformance");
        showLoading("#loadingOverlayAdPerformance");
        showLoading("#loadingOverlayCafe24Products");
        // showLoading("#loadingOverlayGa4Source"); // 존재하지 않는 요소 제거
        
        // 🚀 병렬 처리로 개별 API 호출 (웹버전과 동일한 방식)
        const promises = [];
        
        // 1. Performance Summary
        promises.push(
            fetch('/dashboard/get_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    data_type: 'performance_summary',
                    company_name: companyName,
                    period: period,
                    start_date: startDateValue,
                    end_date: endDateValue,
                    limit: 5
                    // _cache_buster 제거로 캐시 활용
                })
            }).then(response => response.json())
        );
        
        // 2. Cafe24 Product Sales
        promises.push(
            fetch('/dashboard/get_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    data_type: 'cafe24_product_sales',
                    company_name: companyName,
                    period: period,
                    start_date: startDateValue,
                    end_date: endDateValue,
                    limit: 5
                    // _cache_buster 제거로 캐시 활용
                })
            }).then(response => response.json())
        );
        
        // 3. GA4 Source Summary
        promises.push(
            fetch('/dashboard/get_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    data_type: 'ga4_source_summary',
                    company_name: companyName,
                    period: period,
                    start_date: startDateValue,
                    end_date: endDateValue,
                    limit: 5
                    // _cache_buster 제거로 캐시 활용
                })
            }).then(response => response.json())
        );
        
        // 🚀 병렬로 모든 API 호출 실행
        const results = await Promise.all(promises);
        console.log('✅ 병렬 API 호출 완료:', results);
        
        // 📊 데이터 통합 및 렌더링
        const combinedData = {
            status: 'success',
            performance_summary: results[0]?.performance_summary || [],
            cafe24_product_sales: results[1]?.cafe24_product_sales || [],
            cafe24_product_sales_total_count: results[1]?.cafe24_product_sales_total_count || 0,
            ga4_source_summary: results[2]?.ga4_source_summary || [],
            latest_update: results[0]?.latest_update || results[1]?.latest_update || results[2]?.latest_update
        };
        
        console.log('✅ 모바일 데이터 로딩 완료:', combinedData);
        
        // 📊 데이터 렌더링
        if (combinedData.status === 'success') {
            // 1. Performance Summary 렌더링
            if (combinedData.performance_summary) {
                renderPerformanceSummary(combinedData.performance_summary);
                hideLoading("#loadingOverlaySitePerformance");
                hideLoading("#loadingOverlayAdPerformance");
            }
            
            // 2. Cafe24 Product Sales 렌더링
            if (combinedData.cafe24_product_sales) {
                renderCafe24ProductSales(combinedData.cafe24_product_sales, combinedData.cafe24_product_sales_total_count);
                hideLoading("#loadingOverlayCafe24Products");
            }
            
            // 3. GA4 Source Summary 렌더링
            if (combinedData.ga4_source_summary) {
                renderGa4SourceSummary(combinedData.ga4_source_summary);
                hideLoading("#loadingOverlayGa4Sources");
            }
            
            // 4. 업데이트 시간 표시
            if (combinedData.latest_update) {
                updateMobileTimestamp(combinedData.latest_update);
            }
        }
        
    } catch (error) {
        console.error('❌ 모바일 데이터 로딩 실패:', error);
        showError('데이터 로드 실패');
        // 에러 시에도 로딩 스피너 숨김
        hideLoading("#loadingOverlaySitePerformance");
        hideLoading("#loadingOverlayAdPerformance");
        hideLoading("#loadingOverlayCafe24Products");
        hideLoading("#loadingOverlayGa4Sources");
    } finally {
        isLoading = false;
    }
}

// 개별 API 호출 함수들 (웹버전과 동일한 구조, 단일 호출로 통합)
async function fetchMobilePerformanceSummary(companyName, period, startDate, endDate) {
    // 단일 API 호출로 통합되었으므로 별도 구현 불필요
    console.log('🔄 모바일 Performance Summary - 단일 API 호출로 통합됨');
}

async function fetchMobileCafe24Products(companyName, period, startDate, endDate) {
    // 단일 API 호출로 통합되었으므로 별도 구현 불필요
    console.log('🔄 모바일 Cafe24 Products - 단일 API 호출로 통합됨');
}

async function fetchMobileGa4Sources(companyName, period, startDate, endDate) {
    // 단일 API 호출로 통합되었으므로 별도 구현 불필요
    console.log('🔄 모바일 GA4 Sources - 단일 API 호출로 통합됨');
}

function updateMobileTimestamp(latestUpdate) {
    const updatedAtText = document.getElementById('updatedAtText');
    if (!updatedAtText || !latestUpdate) return;
    
    try {
        console.log('🔍 원본 latest_update:', latestUpdate);
        
        // 다양한 날짜 형식 처리
        let dateStr = latestUpdate;
        
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
            console.warn('❌ 유효하지 않은 날짜 형식:', latestUpdate);
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

// ─────────────────────────────────────────────
// 6) 메타 광고 계정 목록 조회
// ─────────────────────────────────────────────
async function fetchMetaAccounts() {
    try {
        const companySelect = document.getElementById('accountFilter');
        const companyName = companySelect ? companySelect.value : 'all';
        
        // 모바일 전용 엔드포인트 사용
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
            console.log('📊 메타 광고 계정 목록:', data.meta_accounts);
            renderMetaAccountFilter(data.meta_accounts);
        } else {
            console.warn('⚠️ 메타 광고 계정 목록 데이터 없음');
        }
        
    } catch (error) {
        console.error('❌ 메타 광고 계정 목록 로딩 실패:', error);
    }
}

// ─────────────────────────────────────────────
// 7) 메타 광고별 성과 조회
// ─────────────────────────────────────────────
async function fetchMetaAdsByAccount(accountId, page = 1) {
    if (!accountId) return;
    
    // 메타 광고 로딩 오버레이 표시
    showLoading("#loadingOverlayMetaAds");
    
    try {
        const periodSelect = document.getElementById('periodFilter');
        const startDate = document.getElementById('startDate');
        const endDate = document.getElementById('endDate');
        
        const companySelect = document.getElementById('accountFilter');
        const period = periodSelect ? periodSelect.value : 'today';
        const startDateValue = startDate ? startDate.value : '';
        const endDateValue = endDate ? endDate.value : '';
        const companyName = companySelect ? companySelect.value : 'all';
        
        metaAdsCurrentPage = page;
        
        // 전체 데이터를 한 번에 가져오기 (limit 없이)
        console.log('📊 메타 광고 전체 데이터 요청 파라미터:', {
            data_type: 'meta_ads_insight_table',
            level: 'ad',
            account_id: accountId,
            company_name: companyName,
            period: period,
            start_date: startDateValue,
            end_date: endDateValue
        });
        
        // 모바일 전용 엔드포인트 사용 (전체 데이터 요청)
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
                // limit과 page 제거하여 전체 데이터 요청
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ 메타 광고별 성과 로딩 성공:', data);
        
        if (data.status === 'success' && data.meta_ads_by_account) {
            console.log('📊 메타 광고별 성과 전체 데이터:', data.meta_ads_by_account);
            console.log('📊 메타 광고별 성과 전체 개수:', data.meta_ads_by_account.length);
            
            // 전체 데이터 저장
            metaAdsAllData = data.meta_ads_by_account;
            console.log('📊 전체 메타 광고 데이터 저장:', metaAdsAllData.length, '개');
            
            // 초기 로딩 시 지출 내림차순으로 정렬
            metaAdsAllData.sort((a, b) => {
                const aSpend = a.spend || 0;
                const bSpend = b.spend || 0;
                return bSpend - aSpend; // 내림차순
            });
            
            console.log('🔄 초기 지출 내림차순 정렬 완료');
            
            // 페이지별 데이터로 렌더링
            const startIndex = (page - 1) * 10;
            const endIndex = startIndex + 10;
            const pageData = metaAdsAllData.slice(startIndex, endIndex);
            
            renderMetaAdsByAccount(pageData, metaAdsAllData.length);
            // 렌더링 후 로딩 숨김
            hideLoading("#loadingOverlayMetaAds");
        } else {
            console.warn('⚠️ 메타 광고별 성과 데이터 없음 또는 실패:', data);
            hideLoading("#loadingOverlayMetaAds");
        }
        
    } catch (error) {
        console.error('❌ 메타 광고별 성과 로딩 실패:', error);
        hideLoading("#loadingOverlayMetaAds");
    } finally {
        // 🔥 추가로 모든 로딩 오버레이 확인
        hideAllLoadingOverlays();
    }
}

// ─────────────────────────────────────────────
// 8) LIVE 광고 미리보기 조회
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
            showLiveAdsSection();
        } else {
            console.warn('🔍 LIVE 광고 미리보기 데이터 없음');
            hideLiveAdsSection();
        }
        
    } catch (error) {
        console.error('❌ LIVE 광고 미리보기 로딩 실패:', error);
        hideLiveAdsSection();
        // 🔥 추가로 모든 로딩 오버레이 확인
        hideAllLoadingOverlays();
    }
}

// ─────────────────────────────────────────────
// 9) 에러 처리 함수
// ─────────────────────────────────────────────
function showError(message) {
    console.error('🚨 에러:', message);
}

// 상품명 토스트 메시지 표시
function showProductNameToast(productName) {
    // 기존 토스트 제거
    const existingToast = document.getElementById('product-name-toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // 새 토스트 생성
    const toast = document.createElement('div');
    toast.id = 'product-name-toast';
    toast.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: var(--bg-primary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 16px 20px;
        font-size: 14px;
        color: var(--text-primary);
        max-width: 80%;
        word-wrap: break-word;
        z-index: 10000;
        box-shadow: var(--shadow-xl);
        text-align: center;
    `;
    toast.textContent = productName;
    
    document.body.appendChild(toast);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 3000);
    
    // 터치 시 즉시 제거
    toast.addEventListener('click', () => {
        toast.remove();
    });
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
    
    // 기간 변경 시
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
            
            // 🚀 디바운싱 적용
            debounceFetchMobileData();
            
            // 메타 광고 계정이 선택되어 있으면 광고별 성과도 업데이트
            if (selectedMetaAccount) {
                console.log('🔄 기간 변경으로 인한 메타 광고 데이터 재로딩:', selectedMetaAccount);
                fetchMetaAdsByAccount(selectedMetaAccount);
                fetchLiveAds(selectedMetaAccount);
            } else {
                // 메타 광고 계정이 선택되어 있지 않으면 현재 선택된 계정 확인
                const metaAccountSelect = document.getElementById('metaAccountSelector');
                if (metaAccountSelect && metaAccountSelect.value) {
                    selectedMetaAccount = metaAccountSelect.value;
                    console.log('🔄 기간 변경으로 인한 메타 광고 데이터 재로딩 (자동 선택):', selectedMetaAccount);
                    fetchMetaAdsByAccount(selectedMetaAccount);
                    fetchLiveAds(selectedMetaAccount);
                }
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
            
            // 메타 광고 테이블 초기화
            const metaAdsTable = document.getElementById('meta-ads-table');
            if (metaAdsTable) {
                metaAdsTable.innerHTML = '<tr><td colspan="6" class="text-center">데이터가 없습니다</td></tr>';
            }
            
            // 🚀 디바운싱 적용
            debounceFetchMobileData();
            fetchMetaAccounts(); // 메타 광고 계정 목록 업데이트
        });
    }
    
    // 날짜 변경 시
    if (startDate) {
        startDate.addEventListener('change', () => {
            console.log('📅 시작일 변경:', startDate.value);
            // 🚀 디바운싱 적용
            debounceFetchMobileData();
            
            // 메타 광고 계정이 선택되어 있으면 광고별 성과도 업데이트
            if (selectedMetaAccount) {
                console.log('🔄 시작일 변경으로 인한 메타 광고 데이터 재로딩:', selectedMetaAccount);
                fetchMetaAdsByAccount(selectedMetaAccount);
                fetchLiveAds(selectedMetaAccount);
            } else {
                // 메타 광고 계정이 선택되어 있지 않으면 현재 선택된 계정 확인
                const metaAccountSelect = document.getElementById('metaAccountSelector');
                if (metaAccountSelect && metaAccountSelect.value) {
                    selectedMetaAccount = metaAccountSelect.value;
                    console.log('🔄 시작일 변경으로 인한 메타 광고 데이터 재로딩 (자동 선택):', selectedMetaAccount);
                    fetchMetaAdsByAccount(selectedMetaAccount);
                    fetchLiveAds(selectedMetaAccount);
                }
            }
        });
    }
    
    if (endDate) {
        endDate.addEventListener('change', () => {
            console.log('📅 종료일 변경:', endDate.value);
            // 🚀 디바운싱 적용
            debounceFetchMobileData();
            
            // 메타 광고 계정이 선택되어 있으면 광고별 성과도 업데이트
            if (selectedMetaAccount) {
                console.log('🔄 종료일 변경으로 인한 메타 광고 데이터 재로딩:', selectedMetaAccount);
                fetchMetaAdsByAccount(selectedMetaAccount);
                fetchLiveAds(selectedMetaAccount);
            } else {
                // 메타 광고 계정이 선택되어 있지 않으면 현재 선택된 계정 확인
                const metaAccountSelect = document.getElementById('metaAccountSelector');
                if (metaAccountSelect && metaAccountSelect.value) {
                    selectedMetaAccount = metaAccountSelect.value;
                    console.log('🔄 종료일 변경으로 인한 메타 광고 데이터 재로딩 (자동 선택):', selectedMetaAccount);
                    fetchMetaAdsByAccount(selectedMetaAccount);
                    fetchLiveAds(selectedMetaAccount);
                }
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
                console.log('🔄 메타 광고 계정 선택으로 인한 데이터 로딩:', accountId);
                // 전체 데이터 초기화
                metaAdsAllData = [];
                fetchMetaAdsByAccount(accountId);
                fetchLiveAds(accountId);
                showLiveAdsSection();
            } else {
                console.log('🔄 메타 광고 계정 선택 해제');
                hideLiveAdsSection();
                
                // 메타 광고 테이블 초기화
                const metaAdsTable = document.getElementById('meta-ads-table');
                if (metaAdsTable) {
                    metaAdsTable.innerHTML = '<tr><td colspan="6" class="text-center">데이터가 없습니다</td></tr>';
                }
            }
        });
    }
    
    // 캠페인 필터 이벤트 설정
    addCampaignFilterEvents();
}

// Flatpickr 초기화 함수
function initializeFlatpickr() {
    const commonConfig = {
        locale: 'ko',
        dateFormat: 'Y-m-d',
        disableMobile: false,
        allowInput: false
    };

    const startDatePicker = flatpickr("#startDate", {
        ...commonConfig,
        maxDate: new Date(),
        onChange: function(selectedDates, dateStr, instance) {
            // 종료일 최소값을 시작일로 설정
            endDatePicker.set('minDate', dateStr);
        }
    });

    const endDatePicker = flatpickr("#endDate", {
        ...commonConfig,
        maxDate: new Date(),
        onOpen: function(selectedDates, dateStr, instance) {
            // 시작일이 선택되어 있으면 최소 날짜 제한
            const startDate = startDatePicker.selectedDates[0];
            if (startDate) {
                instance.set('minDate', startDate);
            }
        }
    });

    // 기간 필터가 "직접 선택"일 때만 날짜 선택 컨테이너 표시
    $("#periodFilter").change(function() {
        const isManual = $(this).val() === "manual";
        $("#dateRangeContainer").toggle(isManual);
        if (!isManual) {
            startDatePicker.clear();
            endDatePicker.clear();
            fetchAllData();  // 데이터 새로고침
        }
    });

    // 날짜 선택 시 데이터 새로고침
    $("#startDate, #endDate").change(function() {
        const startDate = $("#startDate").val();
        const endDate = $("#endDate").val();
        if (startDate && endDate) {
            fetchAllData();
        }
    });
}

// ─────────────────────────────────────────────
// 11) 초기화 함수
// ─────────────────────────────────────────────
function initMobileDashboard() {
    console.log('🚀 모바일 대시보드 초기화 시작...');
    
    // Flatpickr 초기화
    initializeFlatpickr();
    
    // 🔥 모든 로딩 오버레이 숨기기 (화이트 패널 문제 해결)
    hideAllLoadingOverlays();
    
    // 웹버전과 동일한 업체명 자동 선택 로직
    setupCompanyAutoSelection();
    
    setupFilters();
    
    // 🚀 초기 데이터 로딩 (중복 방지)
    if (!isLoading) {
        fetchMobileData();
    }
    
    fetchMetaAccounts(); // 메타 광고 계정 목록 로드
    
    console.log('✅ 모바일 대시보드 초기화 완료');
}

// 🔥 모든 로딩 오버레이 숨기기 함수
function hideAllLoadingOverlays() {
    console.log('🔧 모든 로딩 오버레이 숨기기 시작');
    
    const loadingOverlays = document.querySelectorAll('[id*="loadingOverlay"]');
    loadingOverlays.forEach(overlay => {
        console.log('🔧 로딩 오버레이 숨기기:', overlay.id);
        overlay.style.display = 'none';
        overlay.style.visibility = 'hidden';
        overlay.style.opacity = '0';
        overlay.style.pointerEvents = 'none';
    });
    
    console.log('✅ 모든 로딩 오버레이 숨기기 완료');
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

// 🔥 추가 안전장치: 5초 후 모든 로딩 오버레이 강제 숨기기
setTimeout(() => {
    console.log('🔧 5초 후 모든 로딩 오버레이 강제 숨기기');
    hideAllLoadingOverlays();
}, 5000);

// ─────────────────────────────────────────────
// 13) 페이지네이션 전역 변수
// ─────────────────────────────────────────────
let cafe24ProductSalesCurrentPage = 1;
let cafe24ProductSalesTotalCount = 0;
let metaAdsCurrentPage = 1;
let metaAdsTotalCount = 0;
let metaAdsAllData = []; // 전체 메타 광고 데이터 저장
let tableSortEventsAdded = false; // 테이블 정렬 이벤트 중복 등록 방지



// 사이트 성과 요약 렌더링 (핵심 KPI)
function renderPerformanceSummary(performanceData) {
    console.log('📊 사이트 성과 요약 렌더링:', performanceData);
    
    // 성과 데이터가 배열인 경우 첫 번째 요소 사용
    const data = Array.isArray(performanceData) ? performanceData[0] : performanceData;
    
    // 사이트 성과 요약 KPI 값들 설정
    document.getElementById('site-revenue').textContent = formatCurrency(data.site_revenue || 0);
    // 방문자는 K 없이 원래 숫자로 표시 (예: 1,278)
    const visitors = data.total_visitors || 0;
    document.getElementById('total-visitors').textContent = visitors.toLocaleString();
    // performance_summary_new.py에서 통합으로 가져온 total_orders 사용
    const ordersCount = data.total_orders || 0;
    document.getElementById('orders-count').textContent = formatNumber(ordersCount);
    // 매출대비 광고비 (백분율로 표시)
    const adSpendRatio = data.ad_spend_ratio || 0;
    document.getElementById('ad-spend-ratio').textContent = formatPercentage(adSpendRatio);
    
    // 광고 성과 요약 KPI 값들 설정
    document.getElementById('ad-spend').textContent = formatCurrency(data.ad_spend || 0);
    document.getElementById('total-purchases').textContent = formatNumber(data.total_purchases || 0);
    // avg_opo는 실제로 avg_cpc 필드입니다 - CPC는 정수로 표시
    const cpcValue = data.avg_opo || data.avg_cpc || 0;
    document.getElementById('cpc').textContent = formatCurrency(Math.round(cpcValue));
    document.getElementById('roas').textContent = formatPercentage(data.roas_percentage || 0);
    
    // 광고 성과 요약 제목에 광고 미디어 정보 추가
    const adMedia = data.ad_media || '';
    const adPerformanceSection = document.querySelector('.section:nth-child(3) .section-header');
    if (adMedia && adPerformanceSection) {
        adPerformanceSection.textContent = `광고 성과 요약 - ${adMedia}`;
    }
}

// 카페24 상품판매 렌더링
function renderCafe24ProductSales(products, totalCount = 0) {
    console.log('📦 카페24 상품판매 렌더링:', products);
    
    const tbody = document.getElementById('cafe24-products');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center">데이터가 없습니다</td></tr>';
        return;
    }
    
    // 첫 페이지 5개만 표시
    const displayProducts = products.slice(0, 5);
    
    displayProducts.forEach(product => {
        const row = document.createElement('tr');
        const productName = product.product_name || '-';
        const salesAmount = product.item_product_sales || 0;
        
        row.innerHTML = `
            <td class="text-truncate" title="${productName}">${productName}</td>
            <td class="text-right">${formatNumber(product.item_quantity || 0)}</td>
            <td class="text-right">${formatCurrency(salesAmount)}</td>
        `;
        
        // 상품명 터치 시 전체 텍스트 표시 (모바일 전용)
        const productNameCell = row.querySelector('td:first-child');
        if (productNameCell) {
            const productName = productNameCell.textContent.trim();
            if (productName && productName !== '-') {
                productNameCell.classList.add('product-name-cell');
                productNameCell.setAttribute('data-full-text', productName);
                productNameCell.setAttribute('title', productName);
                
                productNameCell.addEventListener('click', function() {
                    // 터치 시 전체 텍스트를 토스트로 표시
                    showProductNameToast(productName);
                });
            }
        }
        
        tbody.appendChild(row);
    });
    
    // 페이지네이션 업데이트
    cafe24ProductSalesTotalCount = totalCount;
    updatePagination('cafe24_product_sales', cafe24ProductSalesCurrentPage, totalCount);
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
    
    // (not set) 제외하고 상위 5개만 필터링
    const filteredSources = sources
        .filter(source => source.source && source.source !== '(not set)' && source.source !== 'not set')
        .slice(0, 5);
    
    console.log('🔍 필터링된 GA4 소스:', filteredSources);
    
    filteredSources.forEach(source => {
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
            <td class="text-left">${row.campaign_name || '-'}</td>
            <td class="text-left">${row.ad_name || '-'}</td>
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
    
    const metaAccountSelect = document.getElementById('metaAccountSelector');
    
    if (!metaAccountSelect) return;
    
    // 기존 옵션 제거 (기본 옵션 제외)
    metaAccountSelect.innerHTML = '<option value="">계정을 선택해주세요</option>';
    
    // 계정이 있으면 옵션 추가
    if (accounts && accounts.length > 0) {
        accounts.forEach(account => {
            const option = document.createElement('option');
            option.value = account.account_id;
            option.textContent = account.account_name;
            metaAccountSelect.appendChild(option);
        });
        
        // 계정이 1개면 자동 선택
        if (accounts.length === 1) {
            const accountId = accounts[0].account_id;
            metaAccountSelect.value = accountId;
            console.log('🏢 계정 1개 자동 선택:', accountId);
            fetchMetaAdsByAccount(accountId);
            fetchLiveAds(accountId); // LIVE 광고 미리보기 로드
        } else if (accounts.length > 1) {
            // 계정이 여러 개인 경우 "공홈"이 포함된 계정 우선 선택
            let selectedAccount = accounts[0]; // 기본값은 첫 번째 계정
            
            // "공홈"이 포함된 계정 찾기
            const gonghomAccount = accounts.find(account => 
                account.account_name && account.account_name.includes('공홈')
            );
            
            if (gonghomAccount) {
                selectedAccount = gonghomAccount;
                console.log('🏢 "공홈" 포함 계정 자동 선택:', selectedAccount.account_id, selectedAccount.account_name);
            } else {
                console.log('🏢 "공홈" 포함 계정이 없어 첫 번째 계정 자동 선택:', selectedAccount.account_id);
            }
            
            metaAccountSelect.value = selectedAccount.account_id;
            fetchMetaAdsByAccount(selectedAccount.account_id);
            fetchLiveAds(selectedAccount.account_id); // LIVE 광고 미리보기 로드
        }
    }
    
    // 계정 선택 이벤트 추가
    metaAccountSelect.addEventListener('change', function() {
        const selectedAccountId = this.value;
        console.log('🏢 선택된 메타 계정:', selectedAccountId);
        
        if (selectedAccountId) {
            fetchMetaAdsByAccount(selectedAccountId);
            fetchLiveAds(selectedAccountId); // LIVE 광고 미리보기 로드
        } else {
            // 계정이 선택되지 않은 경우 테이블 초기화
            const tbody = document.getElementById('meta-ads-table');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center">계정을 선택해주세요</td></tr>';
            }
            hideLiveAdsSection(); // LIVE 광고 섹션 숨기기
        }
    });
}

// 메타 광고별 성과 렌더링 (광고 탭 기준)
function renderMetaAdsByAccount(adsData, totalCount = null) {
    console.log('📊 메타 광고별 성과 렌더링:', adsData);
    console.log('📊 메타 광고별 성과 전체 개수:', totalCount);
    
    const tbody = document.getElementById('meta-ads-table');
    if (!tbody) {
        console.error('❌ meta-ads-table 요소를 찾을 수 없습니다');
        return;
    }
    
    tbody.innerHTML = '';
    
    if (!adsData || adsData.length === 0) {
        console.log('⚠️ 메타 광고 데이터가 없습니다');
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">데이터가 없습니다</td></tr>';
        return;
    }
    
    console.log('📊 원본 메타 광고 데이터:', adsData);
    
    // 모바일용 데이터 처리 (CPC, ROAS 계산 포함)
    const processedAdsData = processMetaAdsForMobile(adsData);
    console.log('📊 처리된 메타 광고 데이터:', processedAdsData);
    
    // 첫 페이지 10개만 표시
    const displayAdsData = processedAdsData.slice(0, 10);
    
    // 광고별 성과 데이터 렌더링
    displayAdsData.forEach((row, index) => {
        console.log(`📊 광고 ${index + 1}:`, row);
        
        // CPC와 ROAS 계산 (웹버전과 동일한 로직)
        const spend = row.spend || 0;
        const clicks = row.clicks || 0;
        const purchases = row.purchases || 0;
        const purchase_value = row.purchase_value || 0;
        
        const cpc = clicks > 0 ? Math.round(spend / clicks) : 0;
        const roas = spend > 0 ? Math.round((purchase_value / spend) * 100) : 0;
        
        const tableRow = document.createElement('tr');
        tableRow.innerHTML = `
            <td class="text-left">${row.campaign_name || '-'}</td>
            <td class="text-left">${row.ad_name || '-'}</td>
            <td class="text-right">${formatNumber(spend)}</td>
            <td class="text-right">${formatNumber(cpc)}</td>
            <td class="text-right">${formatNumber(purchases)}</td>
            <td class="text-right">${formatNumber(roas)}%</td>
        `;
        tbody.appendChild(tableRow);
    });
    
    // 총합 로우 추가 (전체 데이터 기준 - 페이지와 관계없이 고정)
    if (metaAdsAllData.length > 0) {
        // 전체 데이터로 총합 계산 (페이지와 관계없이)
        const totalSpend = metaAdsAllData.reduce((sum, row) => sum + (row.spend || 0), 0);
        const totalClicks = metaAdsAllData.reduce((sum, row) => sum + (row.clicks || 0), 0);
        const totalPurchases = metaAdsAllData.reduce((sum, row) => sum + (row.purchases || 0), 0);
        const totalPurchaseValue = metaAdsAllData.reduce((sum, row) => sum + (row.purchase_value || 0), 0);
        
        // 총합 CPC와 ROAS 계산 (웹버전과 동일한 로직)
        const totalCpc = totalClicks > 0 ? Math.round(totalSpend / totalClicks) : 0;
        const totalRoas = totalSpend > 0 ? Math.round((totalPurchaseValue / totalSpend) * 100) : 0;
        
        console.log('📊 전체 데이터 기준 총합 (페이지와 관계없이):', {
            totalSpend,
            totalClicks,
            totalPurchases,
            totalPurchaseValue,
            totalCpc,
            totalRoas
        });
        
        const totalRow = document.createElement('tr');
        totalRow.className = 'bg-gray-50 font-semibold';
        totalRow.innerHTML = `
            <td colspan="2" class="text-truncate">총합</td>
            <td class="text-right">${formatNumber(totalSpend)}</td>
            <td class="text-right">${formatNumber(totalCpc)}</td>
            <td class="text-right">${formatNumber(totalPurchases)}</td>
            <td class="text-right">${formatNumber(totalRoas)}%</td>
        `;
        tbody.appendChild(totalRow);
    }
    
    // 페이지네이션 업데이트 (전체 데이터 개수 사용)
    metaAdsTotalCount = totalCount || adsData.length; // 서버에서 받은 전체 개수 또는 현재 데이터 개수
    updatePagination('meta_ads', metaAdsCurrentPage, metaAdsTotalCount);
    
    // 테이블 헤더 클릭 이벤트는 한 번만 등록 (중복 방지)
    if (!tableSortEventsAdded) {
        addTableSortEvents();
        tableSortEventsAdded = true;
    }
    
    console.log('✅ 메타 광고별 성과 렌더링 완료');
}

// LIVE 광고 미리보기 렌더링 (웹버전과 동일한 인스타그램 스타일)
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
        adCard.className = 'insta-card';
        
        // 인스타그램 스타일 카드 생성 (웹버전과 동일)
        const instagramAccName = ad.instagram_acc_name || 'No Name';
        const message = ad.message || '(문구 없음)';
        const firstLine = message.split('\n')[0];
        
        const accountNameHTML = `<span style='font-weight:bold;'>${instagramAccName}</span>`;
        const shortCaption = `${accountNameHTML} ${firstLine} <span class='more-toggle' style='color: #737373; font-size: 13px; cursor: pointer; white-space: nowrap;'>... more</span>`;
        
        adCard.innerHTML = `
            <div class="insta-header">
                <div class="insta-header-left">
                    <img class="profile-image" src="https://cdn-icons-png.flaticon.com/512/1946/1946429.png" alt="프로필">
                    <div class="account-info">
                        <span class="insta-account-name">${instagramAccName}</span>
                        <span class="ad-label" style="color: gray;">광고</span>
                    </div>
                </div>
                <div class="insta-menu">⋯</div>
            </div>

            <div class="insta-image" style="position: relative;">
                <img class="ad-image" src="${ad.image_url || ''}" alt="광고 이미지" loading="lazy" onerror="this.style.display='none'">
                
                ${ad.is_video ? '<div class="play-overlay" style="display: flex;"><svg viewBox="0 0 100 100" class="play-icon" xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="48" fill="rgba(0, 0, 0, 0.4)" /><polygon points="40,30 70,50 40,70" fill="white" /></svg></div>' : '<div class="play-overlay" style="display: none;"></div>'}
            </div>

            <div class="insta-cta">
                <a class="cta-link" href="${ad.link || '#'}" target="_blank">
                    <span>더 알아보기</span>
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="#385185" viewBox="0 0 24 24" width="18" height="18">
                        <path d="M9 6l6 6-6 6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                </a>
            </div>

            <div class="insta-footer">
                <div class="insta-icons">
                    <div class="insta-icons-left">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                        </svg>
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path d="M21 11.5a8.38 8.38 0 0 1-1.9 5.4 8.5 8.5 0 0 1-6.6 3.1 8.38 8.38 0 0 1-5.4-1.9L3 21l2.9-3.1a8.38 8.38 0 0 1-1.9-5.4 8.5 8.5 0 0 1 3.1-6.6A8.38 8.38 0 0 1 12.5 3a8.5 8.5 0 0 1 6.6 3.1A8.38 8.38 0 0 1 21 11.5z"/>
                        </svg>
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path d="M22 2L11 13"></path><path d="M22 2L15 22L11 13L2 9L22 2Z"></path>
                        </svg>
                    </div>
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
                    </svg>
                </div>
                <div class="insta-caption ad-caption">${shortCaption}</div>
            </div>
        `;
        
        // 더보기/접기 기능 추가
        const captionElement = adCard.querySelector('.ad-caption');
        if (captionElement) {
            const fullCaption = `${accountNameHTML} ${message} <span class='less-toggle' style='color: #737373; font-size: 13px; cursor: pointer; white-space: nowrap;'>... less</span>`;
            
            captionElement.addEventListener('click', function(e) {
                if (e.target.classList.contains('more-toggle')) {
                    this.innerHTML = fullCaption;
                } else if (e.target.classList.contains('less-toggle')) {
                    this.innerHTML = shortCaption;
                }
            });
        }
        
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
// 15) 페이지네이션 함수
// ─────────────────────────────────────────────
function updatePagination(table, currentPage, totalItems) {
    let limit = table === 'cafe24_product_sales' ? 5 : 10; // 카페24는 5개, 메타광고는 10개
    let totalPages = totalItems > 0 ? Math.ceil(totalItems / limit) : 1;

    console.log(`📄 ${table} 페이지네이션 업데이트`);
    console.log(`📄 현재 페이지: ${currentPage}`);
    console.log(`📄 전체 페이지 수: ${totalPages}`);
    console.log(`📄 전체 데이터 개수: ${totalItems}`);

    let paginationContainer = document.getElementById(`pagination_${table}`);

    if (!paginationContainer) {
        console.warn(`⚠️ 페이지네이션 컨테이너를 찾을 수 없음: #pagination_${table}`);
        return;
    }

    paginationContainer.innerHTML = ''; // 기존 버튼 제거 후 다시 추가

    let prevDisabled = currentPage <= 1 ? "disabled" : "";
    let nextDisabled = currentPage >= totalPages ? "disabled" : "";

    paginationContainer.innerHTML = `
        <button class="pagination-btn prev-btn" data-table="${table}" data-page="${currentPage - 1}" ${prevDisabled}>이전</button>
        <span class="pagination-info">${currentPage} / ${totalPages}</span>
        <button class="pagination-btn next-btn" data-table="${table}" data-page="${currentPage + 1}" ${nextDisabled}>다음</button>
    `;

    // 이벤트 핸들러 제거 후 다시 추가 (중복 방지)
    paginationContainer.querySelectorAll(".pagination-btn").forEach(btn => {
        btn.addEventListener('click', function() {
            let newPage = parseInt(this.dataset.page);
            let tableName = this.dataset.table;

            if (!this.hasAttribute("disabled") && newPage !== currentPage) {
                console.log(`📄 ${tableName} 페이지 이동: ${newPage}`);

                if (tableName === 'cafe24_product_sales') {
                    fetchCafe24ProductSalesData(newPage);
                } else if (tableName === 'meta_ads') {
                    fetchMetaAdsByAccount(selectedMetaAccount, newPage);
                }
            } else {
                console.log(`📄 ${tableName} 버튼 클릭 불가 (비활성화 상태 또는 현재 페이지)`);
            }
        });
    });
}

// ─────────────────────────────────────────────
// 16) 테이블 정렬 기능
// ─────────────────────────────────────────────
function addTableSortEvents() {
    const table = document.querySelector('#meta-ads-table').closest('table');
    if (!table) return;
    
    const headers = table.querySelectorAll('th');
    headers.forEach((header, index) => {
        // 원본 텍스트 저장 (정렬 표시 제외)
        if (!header.dataset.originalText) {
            header.dataset.originalText = header.textContent.replace(' ↑', '').replace(' ↓', '');
        }
        
        header.style.cursor = 'pointer';
        header.addEventListener('click', () => {
            sortTable(table, index);
        });
    });
}

function sortTable(table, columnIndex) {
    console.log('🔄 전체 데이터 정렬 시작 - 컬럼:', columnIndex);
    
    // 헤더 정렬 상태 확인 및 업데이트
    const header = table.querySelector(`th:nth-child(${columnIndex + 1})`);
    const currentOrder = header.dataset.order || 'none';
    const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
    
    console.log('🔄 정렬 상태 변경:', currentOrder, '→', newOrder);
    
    // 전체 데이터 정렬
    if (metaAdsAllData.length > 0) {
        // 정렬 기준 컬럼에 따라 전체 데이터 정렬
        const sortedData = [...metaAdsAllData].sort((a, b) => {
            let aValue, bValue;
            
            switch (columnIndex) {
                case 0: // 캠페인
                    aValue = (a.campaign_name || '').toLowerCase();
                    bValue = (b.campaign_name || '').toLowerCase();
                    break;
                case 1: // 광고
                    aValue = (a.ad_name || '').toLowerCase();
                    bValue = (b.ad_name || '').toLowerCase();
                    break;
                case 2: // 지출
                    aValue = a.spend || 0;
                    bValue = b.spend || 0;
                    break;
                case 3: // CPC
                    aValue = a.clicks > 0 ? Math.round(a.spend / a.clicks) : 0;
                    bValue = b.clicks > 0 ? Math.round(b.spend / b.clicks) : 0;
                    break;
                case 4: // 구매
                    aValue = a.purchases || 0;
                    bValue = b.purchases || 0;
                    break;
                case 5: // ROAS
                    aValue = a.spend > 0 ? Math.round((a.purchase_value / a.spend) * 100) : 0;
                    bValue = b.spend > 0 ? Math.round((b.purchase_value / b.spend) * 100) : 0;
                    break;
                default:
                    aValue = 0;
                    bValue = 0;
            }
            
            // 문자열 비교
            if (typeof aValue === 'string' && typeof bValue === 'string') {
                if (newOrder === 'asc') {
                    return aValue.localeCompare(bValue);
                } else {
                    return bValue.localeCompare(aValue);
                }
            }
            
            // 숫자 비교
            if (newOrder === 'asc') {
                return aValue - bValue;
            } else {
                return bValue - aValue;
            }
        });
        
        // 정렬된 전체 데이터 저장
        metaAdsAllData = sortedData;
        console.log('🔄 전체 데이터 정렬 완료:', sortedData.length, '개');
        
        // 정렬 시 페이지를 1로 리셋
        metaAdsCurrentPage = 1;
        
        // 첫 페이지 데이터로 다시 렌더링
        const pageData = metaAdsAllData.slice(0, 10);
        
        renderMetaAdsByAccount(pageData, metaAdsAllData.length);
    }
    
    // 모든 헤더의 정렬 표시 제거
    table.querySelectorAll('th').forEach(th => {
        th.dataset.order = 'none';
        th.textContent = th.dataset.originalText || th.textContent.replace(' ↑', '').replace(' ↓', '');
    });
    
    // 현재 헤더에 정렬 표시
    header.dataset.order = newOrder;
    header.textContent = (header.dataset.originalText || header.textContent.replace(' ↑', '').replace(' ↓', '')) + (newOrder === 'asc' ? ' ↑' : ' ↓');
    
    console.log('🔄 정렬 표시 업데이트 완료:', header.textContent);
}

function getCellValue(row, columnIndex) {
    const cell = row.cells[columnIndex];
    if (!cell) return 0;
    
    const text = cell.textContent.trim();
    
    // 숫자 추출 (쉼표와 % 제거)
    const number = parseFloat(text.replace(/[%,]/g, ''));
    return isNaN(number) ? text : number;
}

// ─────────────────────────────────────────────
// 17) 캠페인 필터 기능
// ─────────────────────────────────────────────
function addCampaignFilterEvents() {
    const filterCheckboxes = document.querySelectorAll('.campaign-filter input[type="checkbox"]');
    
    filterCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            filterMetaAdsByCampaign();
        });
    });
}

function filterMetaAdsByCampaign() {
    const selectedCampaigns = [];
    document.querySelectorAll('.campaign-filter input[type="checkbox"]:checked').forEach(checkbox => {
        selectedCampaigns.push(checkbox.value);
    });
    
    console.log('🔍 선택된 캠페인:', selectedCampaigns);
    
    // 전체 데이터에서 필터링
    if (metaAdsAllData.length > 0) {
        const filteredData = metaAdsAllData.filter(row => {
            const campaignName = row.campaign_name || '';
            
            // 선택된 캠페인 타입이 없으면 모든 데이터 표시
            if (selectedCampaigns.length === 0) {
                return true;
            }
            
            // 선택된 캠페인 타입 중 하나라도 포함되면 표시
            return selectedCampaigns.some(campaignType => 
                campaignName.includes(campaignType)
            );
        });
        
        console.log('🔍 필터링된 데이터:', filteredData.length, '개');
        
        // 필터링된 데이터로 렌더링 (첫 페이지)
        const startIndex = 0;
        const endIndex = 10;
        const pageData = filteredData.slice(startIndex, endIndex);
        
        // 필터링된 데이터를 임시로 저장하여 총합 계산에 사용
        const originalMetaAdsAllData = metaAdsAllData;
        metaAdsAllData = filteredData;
        
        renderMetaAdsByAccount(pageData, filteredData.length);
        
        // 원본 데이터 복원
        metaAdsAllData = originalMetaAdsAllData;
        
        // 페이지네이션 업데이트
        metaAdsCurrentPage = 1;
        metaAdsTotalCount = filteredData.length;
        updatePagination('meta_ads', metaAdsCurrentPage, metaAdsTotalCount);
    }
}

// ─────────────────────────────────────────────
// 18) 디버깅용 전역 함수 (개발용)
// ─────────────────────────────────────────────
window.mobileDashboard = {
    fetchData: fetchMobileData,
    getData: () => mobileData,
    isLoading: () => isLoading,
    renderData: fetchMobileData, // renderMobileData 대신 fetchMobileData 사용
    fetchMetaAccounts: fetchMetaAccounts,
    fetchMetaAdsByAccount: fetchMetaAdsByAccount,
    fetchLiveAds: fetchLiveAds,
    processMetaAdsForMobile: processMetaAdsForMobile
}; 