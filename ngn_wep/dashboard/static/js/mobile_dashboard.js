// File: ngn_wep/dashboard/static/js/mobile_dashboard.js
// 모바일 대시보드 JavaScript - 웹버전과 동일한 구조, 데이터만 축소

// 🔥 성능 최적화: 요청 중복 방지 및 메모리 효율성 개선
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

// 🔥 로딩 스피너 개선을 위한 전역 변수 추가 (단순화)
let isLoadingData = false;
const LOADING_TIMEOUT = 15000; // 15초 타임아웃
let loadingTimeoutId = null;

// 🚀 성능 최적화를 위한 캐시 추가
const dataCache = new Map();
const CACHE_DURATION = 5 * 60 * 1000; // 5분 캐시

// ✅ Flatpickr 전역 변수 추가
let startDatePicker = null;
let endDatePicker = null;

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

// 🔥 로딩 상태 관리 함수들 개선 (단순화)
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
    
    console.log("✅ Loading stopped for:", target);
}

// 🔥 단순화된 로딩 상태 관리
function startLoading() {
    isLoadingData = true;
    console.log('🔄 전체 로딩 시작');
    
    // 모든 로딩 오버레이 표시
    showLoading("#loadingOverlaySitePerformance");
    showLoading("#loadingOverlayAdPerformance");
    showLoading("#loadingOverlayCafe24Products");
    showLoading("#loadingOverlayGa4Sources");
    showLoading("#loadingOverlayMetaAds");
    
    // 타임아웃 시작
    startLoadingTimeout();
}

function stopLoading() {
    isLoadingData = false;
    console.log('✅ 전체 로딩 완료');
    
    // 타임아웃 제거
    clearLoadingTimeout();
    
    // 모든 로딩 오버레이 숨기기
    hideAllLoadingOverlays();
}

function clearLoadingTimeout() {
    if (loadingTimeoutId) {
        clearTimeout(loadingTimeoutId);
        loadingTimeoutId = null;
        console.log('⏰ 로딩 타임아웃 제거');
    }
}

function startLoadingTimeout() {
    clearLoadingTimeout();
    loadingTimeoutId = setTimeout(() => {
        console.warn('⚠️ 로딩 타임아웃 발생 - 강제 종료');
        stopLoading();
        showError('데이터 로딩 시간이 초과되었습니다. 다시 시도해주세요.');
    }, LOADING_TIMEOUT);
    console.log('⏰ 로딩 타임아웃 시작:', LOADING_TIMEOUT + 'ms');
}

// 🔥 수정: 모든 로딩 오버레이 숨기기 (메타 광고 포함)
function hideAllLoadingOverlays() {
    console.log("🔄 모든 로딩 오버레이 숨기기");
    hideLoading("#loadingOverlaySitePerformance");
    hideLoading("#loadingOverlayAdPerformance");
    hideLoading("#loadingOverlayCafe24Products");
    hideLoading("#loadingOverlayGa4Sources");
    hideLoading("#loadingOverlayMetaAds"); // 🔥 누락된 메타 광고 추가
}

// 🔥 에러 처리 함수
function handleError(error, context) {
    console.error(`❌ ${context} 실패:`, error);
    showError(`${context}를 불러올 수 없습니다.`);
}

function showError(message) {
    console.error('❌ 에러 메시지:', message);
    // 간단한 토스트 메시지 표시
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #ff4444;
        color: white;
        padding: 12px 16px;
        border-radius: 8px;
        z-index: 10000;
        font-size: 14px;
        max-width: 300px;
        word-wrap: break-word;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 5000);
}

// 🚀 성능 최적화: 캐시 관리
function getCacheKey(type, params) {
    return `${type}_${JSON.stringify(params)}`;
}

function getCachedData(key) {
    const cached = dataCache.get(key);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
        console.log('📦 캐시된 데이터 사용:', key);
        return cached.data;
    }
    return null;
}

function setCachedData(key, data) {
    dataCache.set(key, {
        data: data,
        timestamp: Date.now()
    });
    console.log('📦 데이터 캐시 저장:', key);
}

// 🚀 성능 최적화: DOM 조작 최적화
function createDocumentFragment() {
    return document.createDocumentFragment();
}

function batchDOMUpdates(updates) {
    requestAnimationFrame(() => {
        updates.forEach(update => update());
    });
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

// ✅ Flatpickr 초기화 함수 (웹버전과 동일)
function initializeMobileFlatpickr() {
  // Flatpickr가 로드되었는지 확인
  if (typeof flatpickr === 'undefined') {
    console.warn('Flatpickr not loaded, retrying in 100ms...');
    setTimeout(initializeMobileFlatpickr, 100);
    return;
  }

  const commonConfig = {
    locale: 'ko',
    dateFormat: 'Y-m-d',
    allowInput: false,
    clickOpens: true,
    theme: 'material_blue',
    disableMobile: false,
    time_24hr: true
  };

  // 시작일 선택기
  const startDateInput = document.getElementById('startDate');
  if (startDateInput && !startDatePicker) {
    startDatePicker = flatpickr(startDateInput, {
      ...commonConfig,
      onChange: function(selectedDates, dateStr) {
        console.log('📅 시작일 변경:', dateStr);
        if (periodSelect.value === 'manual') {
          debounceFetchMobileData();
        }
      },
      onClose: function(selectedDates, dateStr) {
        console.log('📅 시작일 선택 완료:', dateStr);
      }
    });
    console.log('✅ 시작일 Flatpickr 초기화 완료');
  }

  // 종료일 선택기
  const endDateInput = document.getElementById('endDate');
  if (endDateInput && !endDatePicker) {
    endDatePicker = flatpickr(endDateInput, {
      ...commonConfig,
      onChange: function(selectedDates, dateStr) {
        console.log('📅 종료일 변경:', dateStr);
        if (periodSelect.value === 'manual') {
          debounceFetchMobileData();
        }
      },
      onClose: function(selectedDates, dateStr) {
        console.log('📅 종료일 선택 완료:', dateStr);
      }
    });
    console.log('✅ 종료일 Flatpickr 초기화 완료');
  }
}

// ─────────────────────────────────────────────
// 5) 데이터 요청 함수들 (웹버전과 동일한 구조)
// ─────────────────────────────────────────────

// 🔥 최적화된 데이터 요청 함수
async function fetchMobileData() {
    console.log('🔄 모바일 데이터 요청 시작');
    
    if (isLoading) {
        console.log('⚠️ 이미 로딩 중이므로 중단');
        return;
    }
    
    isLoading = true;
    
    try {
        const companySelect = document.getElementById('accountFilter');
        const periodSelect = document.getElementById('periodFilter');
        const startDateInput = document.getElementById('startDate');
        const endDateInput = document.getElementById('endDate');
        
        const companyName = companySelect ? companySelect.value : 'all';
        const period = periodSelect ? periodSelect.value : 'today';
        const startDate = startDateInput ? startDateInput.value.trim() : '';
        const endDate = endDateInput ? endDateInput.value.trim() : '';
        
        // ✅ 직접 선택 모드에서 날짜 검증 (웹버전과 동일)
        if (period === 'manual' && (!startDate || !endDate)) {
            console.warn('[BLOCKED] 직접 선택: 날짜 누락 → 실행 안함');
            isLoading = false;
            return;
        }
        
        console.log('📊 요청 파라미터:', { companyName, period, startDate, endDate });
        
        // 🔥 단순화된 로딩 시작
        startLoading();
        
        // 🚀 병렬로 데이터 요청 (최적화)
        const promises = [
            fetchMobilePerformanceSummary(companyName, period, startDate, endDate),
            fetchMobileCafe24Products(companyName, period, startDate, endDate),
            fetchMobileGa4Sources(companyName, period, startDate, endDate)
        ];
        
        const results = await Promise.allSettled(promises);
        
        // 결과 처리 및 latest_update 추출
        let latestUpdate = null;
        let hasError = false;
        
        results.forEach((result, index) => {
            if (result.status === 'rejected') {
                console.error(`❌ 데이터 요청 실패 (${index}):`, result.reason);
                hasError = true;
            } else if (result.value && result.value.latest_update) {
                // 성공한 API 응답에서 latest_update 사용
                latestUpdate = result.value.latest_update;
                console.log('✅ API 응답에서 latest_update 추출:', latestUpdate);
            }
        });
        
        // ✅ 타임스탬프 업데이트 (API 응답의 latest_update 우선, 없으면 현재 시간)
        if (latestUpdate) {
            updateMobileTimestamp(latestUpdate);
        } else {
            updateMobileTimestamp(new Date().toLocaleString('ko-KR'));
        }
        
        // 에러가 있으면 사용자에게 알림
        if (hasError) {
            showError('일부 데이터를 불러올 수 없습니다.');
        }
        
    } catch (error) {
        console.error('❌ 모바일 데이터 요청 실패:', error);
        handleError(error, '데이터 요청');
    } finally {
        isLoading = false;
        // 🔥 로딩 완료
        stopLoading();
    }
}

// 🚀 최적화된 개별 API 호출 함수들
async function fetchMobilePerformanceSummary(companyName, period, startDate, endDate) {
    const cacheKey = getCacheKey('performance', { companyName, period, startDate, endDate });
    const cached = getCachedData(cacheKey);
    
    if (cached) {
        renderPerformanceSummary(cached.performance_summary);
        return cached;
    }
    
    try {
        console.log('🔄 모바일 Performance Summary API 호출');
        
        const response = await fetch('/dashboard/get_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                data_type: 'performance_summary',
                company_name: companyName,
                period: period,
                start_date: startDate,
                end_date: endDate
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ 모바일 Performance Summary 로딩 성공:', data);
        
        if (data.status === 'success' && data.performance_summary) {
            renderPerformanceSummary(data.performance_summary);
            setCachedData(cacheKey, data);
        }
        
        return data;
        
    } catch (error) {
        console.error('❌ 모바일 Performance Summary 로딩 실패:', error);
        return null;
    }
}

async function fetchMobileCafe24Products(companyName, period, startDate, endDate) {
    const cacheKey = getCacheKey('cafe24', { companyName, period, startDate, endDate });
    const cached = getCachedData(cacheKey);
    
    if (cached) {
        renderCafe24ProductSales(cached.cafe24_product_sales, cached.cafe24_product_sales_total_count);
        return cached;
    }
    
    try {
        console.log('🔄 모바일 Cafe24 Products API 호출');
        
        const response = await fetch('/dashboard/get_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                data_type: 'cafe24_product_sales',
                company_name: companyName,
                period: period,
                start_date: startDate,
                end_date: endDate,
                page: 1,
                limit: 5
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ 모바일 Cafe24 Products 로딩 성공:', data);
        
        if (data.status === 'success' && data.cafe24_product_sales) {
            renderCafe24ProductSales(data.cafe24_product_sales, data.cafe24_product_sales_total_count);
            setCachedData(cacheKey, data);
        }
        
        return data;
        
    } catch (error) {
        console.error('❌ 모바일 Cafe24 Products 로딩 실패:', error);
        return null;
    }
}

async function fetchMobileGa4Sources(companyName, period, startDate, endDate) {
    const cacheKey = getCacheKey('ga4', { companyName, period, startDate, endDate });
    const cached = getCachedData(cacheKey);
    
    if (cached) {
        renderGa4SourceSummary(cached.ga4_source_summary);
        return cached;
    }
    
    try {
        console.log('🔄 모바일 GA4 Sources API 호출');
        
        const response = await fetch('/dashboard/get_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                data_type: 'ga4_source_summary',
                company_name: companyName,
                period: period,
                start_date: startDate,
                end_date: endDate
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ 모바일 GA4 Sources 로딩 성공:', data);
        
        if (data.status === 'success' && data.ga4_source_summary) {
            renderGa4SourceSummary(data.ga4_source_summary);
            setCachedData(cacheKey, data);
        }
        
        return data;
        
    } catch (error) {
        console.error('❌ 모바일 GA4 Sources 로딩 실패:', error);
        return null;
    }
}

// ─────────────────────────────────────────────
// 6) 메타 광고 관련 함수들 (최적화)
// ─────────────────────────────────────────────

// 🚀 최적화된 메타 계정 조회
async function fetchMetaAccounts() {
    try {
        console.log('🔄 메타 광고 계정 목록 요청');
        
        const response = await fetch('/m/get_meta_accounts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('✅ 메타 광고 계정 목록 로딩 성공:', data);
        
        if (data.status === 'success' && data.meta_accounts) {
            renderMetaAccountFilter(data.meta_accounts);
            
            // 첫 번째 계정이 있으면 자동 선택
            if (data.meta_accounts.length > 0) {
                const firstAccount = data.meta_accounts[0];
                selectedMetaAccount = firstAccount.account_id;
                console.log('🔄 첫 번째 메타 계정 자동 선택:', selectedMetaAccount);
                
                // 메타 광고 데이터 로딩
                await fetchMetaAdsByAccount(selectedMetaAccount, 1);
            }
        }
        
    } catch (error) {
        console.error('❌ 메타 광고 계정 목록 로딩 실패:', error);
        showError('메타 광고 계정 목록을 불러올 수 없습니다.');
    }
}

// 🚀 최적화된 메타 광고 데이터 조회
async function fetchMetaAdsByAccount(accountId, page = 1) {
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
        
        metaAdsCurrentPage = page;
        
        console.log('📊 메타 광고 데이터 요청:', {
            account_id: accountId,
            company_name: companyName,
            period: period,
            start_date: startDateValue,
            end_date: endDateValue
        });
        
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
        console.log('✅ 메타 광고 데이터 로딩 성공:', data);
        
        if (data.status === 'success' && data.meta_ads_by_account) {
            // 데이터 처리 및 렌더링
            const processedData = processMetaAdsForMobile(data.meta_ads_by_account);
            
            // 지출 내림차순 정렬
            processedData.sort((a, b) => {
                const aSpend = a.spend || 0;
                const bSpend = b.spend || 0;
                return bSpend - aSpend;
            });
            
            // 페이지별 데이터로 렌더링
            const startIndex = (page - 1) * 10;
            const endIndex = startIndex + 10;
            const pageData = processedData.slice(startIndex, endIndex);
            
            renderMetaAdsByAccount(pageData, processedData.length);
        } else {
            console.warn('⚠️ 메타 광고 데이터 없음:', data);
        }
        
    } catch (error) {
        console.error('❌ 메타 광고 데이터 로딩 실패:', error);
        handleError(error, '메타 광고 데이터');
    }
}

// ─────────────────────────────────────────────
// 7) LIVE 광고 미리보기 조회 (최적화)
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
    }
}

// ─────────────────────────────────────────────
// 8) UI 유틸리티 함수들
// ─────────────────────────────────────────────

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
// 9) 필터 이벤트 핸들러 (웹버전과 동일)
// ─────────────────────────────────────────────
function setupFilters() {
    const companySelect = document.getElementById('accountFilter');
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    const periodSelect = document.getElementById('periodFilter');
    const metaAccountSelect = document.getElementById('metaAccountSelector');
    
    // ✅ Flatpickr 초기화
    initializeMobileFlatpickr();
    
    // 기간 변경 시
    if (periodSelect) {
        periodSelect.addEventListener('change', () => {
            console.log('📅 기간 변경:', periodSelect.value);
            
            // ✅ 직접 선택 모드일 때 날짜 입력 필드 표시/숨김 (웹버전과 동일)
            const dateRangeContainer = document.getElementById('dateRangeContainer');
            if (dateRangeContainer) {
                if (periodSelect.value === 'manual') {
                    dateRangeContainer.style.display = 'flex';
                    // Flatpickr 인스턴스 재활성화
                    startDatePicker?.enable();
                    endDatePicker?.enable();
                } else {
                    dateRangeContainer.style.display = 'none';
                    startDatePicker?.clear();
                    endDatePicker?.clear();
                    startDate.value = "";
                    endDate.value = "";
                }
            }
            
            // 데이터 새로고침
            debounceFetchMobileData();
        });
    }
    
    // 회사 변경 시
    if (companySelect) {
        companySelect.addEventListener('change', () => {
            console.log('🏢 회사 변경:', companySelect.value);
            debounceFetchMobileData();
        });
    }
    
    // 시작일 변경 시
    if (startDate) {
        startDate.addEventListener('change', () => {
            console.log('📅 시작일 변경:', startDate.value);
            if (periodSelect.value === 'manual') {
                debounceFetchMobileData();
            }
        });
    }
    
    // 종료일 변경 시
    if (endDate) {
        endDate.addEventListener('change', () => {
            console.log('📅 종료일 변경:', endDate.value);
            if (periodSelect.value === 'manual') {
                debounceFetchMobileData();
            }
        });
    }
    
    // 메타 계정 변경 시
    if (metaAccountSelect) {
        metaAccountSelect.addEventListener('change', () => {
            const selectedAccountId = metaAccountSelect.value;
            console.log('📊 메타 계정 변경:', selectedAccountId);
            
            if (selectedAccountId) {
                selectedMetaAccount = selectedAccountId;
                fetchMetaAdsByAccount(selectedAccountId, 1);
            }
        });
    }
}

// ─────────────────────────────────────────────
// 10) 초기화 함수들
// ─────────────────────────────────────────────

// 🔥 최적화된 모바일 대시보드 초기화
function initMobileDashboard() {
    console.log('🚀 모바일 대시보드 초기화 시작');
    
    // 필터 설정
    setupFilters();
    
    // 회사 자동 선택 설정
    setupCompanyAutoSelection();
    
    // 메타 광고 계정 목록 로딩
    fetchMetaAccounts();
    
    // 초기 데이터 로딩
    fetchMobileData();
    
    console.log('✅ 모바일 대시보드 초기화 완료');
}

// 회사 자동 선택 설정
function setupCompanyAutoSelection() {
    const companySelect = document.getElementById('accountFilter');
    if (companySelect && companySelect.options.length > 0) {
        // 첫 번째 옵션 선택 (all 또는 첫 번째 회사)
        companySelect.selectedIndex = 0;
        console.log('🏢 첫 번째 회사 자동 선택:', companySelect.value);
    }
}

// ─────────────────────────────────────────────
// 11) 렌더링 함수들 (성능 최적화)
// ─────────────────────────────────────────────

// 🚀 최적화된 성과 요약 렌더링
function renderPerformanceSummary(performanceData) {
    if (!performanceData) return;
    
    console.log('📊 성과 요약 렌더링:', performanceData);
    
    // DocumentFragment 사용으로 DOM 조작 최적화
    const fragment = createDocumentFragment();
    
    const updates = [
        () => {
            const totalSalesElement = document.getElementById('total-sales');
            if (totalSalesElement) {
                totalSalesElement.textContent = formatCurrency(performanceData.total_sales || 0);
            }
        },
        () => {
            const ordersCountElement = document.getElementById('orders-count');
            if (ordersCountElement) {
                ordersCountElement.textContent = formatNumber(performanceData.orders_count || 0);
            }
        },
        () => {
            const adSpendRatioElement = document.getElementById('ad-spend-ratio');
            if (adSpendRatioElement) {
                adSpendRatioElement.textContent = formatPercentage(performanceData.ad_spend_ratio || 0);
            }
        },
        () => {
            const adSpendElement = document.getElementById('ad-spend');
            if (adSpendElement) {
                adSpendElement.textContent = formatCurrency(performanceData.ad_spend || 0);
            }
        },
        () => {
            const totalPurchasesElement = document.getElementById('total-purchases');
            if (totalPurchasesElement) {
                totalPurchasesElement.textContent = formatNumber(performanceData.total_purchases || 0);
            }
        },
        () => {
            const cpcElement = document.getElementById('cpc');
            if (cpcElement) {
                cpcElement.textContent = formatCurrency(performanceData.cpc || 0);
            }
        },
        () => {
            const roasElement = document.getElementById('roas');
            if (roasElement) {
                roasElement.textContent = formatPercentage(performanceData.roas || 0);
            }
        }
    ];
    
    // 배치 업데이트로 성능 최적화
    batchDOMUpdates(updates);
    
    console.log('✅ 성과 요약 렌더링 완료');
}

// 🚀 최적화된 카페24 상품판매 렌더링
function renderCafe24ProductSales(products, totalCount = 0) {
    if (!products || !Array.isArray(products)) return;
    
    console.log('📊 카페24 상품판매 렌더링:', products);
    
    const tbody = document.getElementById('cafe24-products');
    if (!tbody) return;
    
    // DocumentFragment 사용
    const fragment = createDocumentFragment();
    
    products.forEach(product => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="product-name" onclick="showProductNameToast('${product.product_name || ''}')">${product.product_name || '--'}</td>
            <td class="text-right">${formatNumber(product.total_quantity || 0)}</td>
            <td class="text-right">${formatCurrency(product.total_sales || 0)}</td>
        `;
        fragment.appendChild(row);
    });
    
    // 한 번에 DOM 업데이트
    tbody.innerHTML = '';
    tbody.appendChild(fragment);
    
    console.log('✅ 카페24 상품판매 렌더링 완료');
}

// 🚀 최적화된 GA4 소스별 유입수 렌더링
function renderGa4SourceSummary(sources) {
    if (!sources || !Array.isArray(sources)) return;
    
    console.log('📊 GA4 소스별 유입수 렌더링:', sources);
    
    const tbody = document.getElementById('ga4-sources');
    if (!tbody) return;
    
    // DocumentFragment 사용
    const fragment = createDocumentFragment();
    
    sources.forEach(source => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${source.source || '--'}</td>
            <td class="text-right">${formatNumber(source.users || 0)}</td>
        `;
        fragment.appendChild(row);
    });
    
    // 한 번에 DOM 업데이트
    tbody.innerHTML = '';
    tbody.appendChild(fragment);
    
    console.log('✅ GA4 소스별 유입수 렌더링 완료');
}

// 🚀 최적화된 메타 광고 렌더링
function renderMetaAds(metaAds) {
    if (!metaAds || !Array.isArray(metaAds)) return;
    
    console.log('📊 메타 광고 렌더링:', metaAds);
    
    const tbody = document.getElementById('meta-ads-table');
    if (!tbody) return;
    
    // DocumentFragment 사용
    const fragment = createDocumentFragment();
    
    metaAds.forEach(ad => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="text-left">${ad.campaign_name || '--'}</td>
            <td class="text-left">${ad.ad_name || '--'}</td>
            <td class="text-right">${formatCurrency(ad.spend || 0)}</td>
            <td class="text-right">${formatCurrency(ad.cpc || 0)}</td>
            <td class="text-right">${formatNumber(ad.purchases || 0)}</td>
            <td class="text-right">${formatPercentage(ad.roas || 0)}</td>
        `;
        fragment.appendChild(row);
    });
    
    // 한 번에 DOM 업데이트
    tbody.innerHTML = '';
    tbody.appendChild(fragment);
    
    console.log('✅ 메타 광고 렌더링 완료');
}

// 메타 계정 필터 렌더링
function renderMetaAccountFilter(accounts) {
    if (!accounts || !Array.isArray(accounts)) return;
    
    console.log('📊 메타 계정 필터 렌더링:', accounts);
    
    const select = document.getElementById('metaAccountSelector');
    if (!select) return;
    
    // 기존 옵션 제거 (placeholder 제외)
    const placeholder = select.querySelector('.placeholder-option');
    select.innerHTML = '';
    if (placeholder) {
        select.appendChild(placeholder);
    }
    
    // 새 옵션 추가
    accounts.forEach(account => {
        const option = document.createElement('option');
        option.value = account.account_id;
        option.textContent = account.account_name || account.account_id;
        select.appendChild(option);
    });
    
    console.log('✅ 메타 계정 필터 렌더링 완료');
}

// 🚀 최적화된 메타 광고별 성과 렌더링
function renderMetaAdsByAccount(adsData, totalCount = null) {
    if (!adsData || !Array.isArray(adsData)) return;
    
    console.log('📊 메타 광고별 성과 렌더링:', adsData);
    
    const tbody = document.getElementById('meta-ads-table');
    if (!tbody) return;
    
    // DocumentFragment 사용
    const fragment = createDocumentFragment();
    
    adsData.forEach(ad => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="text-left">${ad.campaign_name || '--'}</td>
            <td class="text-left">${ad.ad_name || '--'}</td>
            <td class="text-right">${formatCurrency(ad.spend || 0)}</td>
            <td class="text-right">${formatCurrency(ad.cpc || 0)}</td>
            <td class="text-right">${formatNumber(ad.purchases || 0)}</td>
            <td class="text-right">${formatPercentage(ad.roas || 0)}</td>
        `;
        fragment.appendChild(row);
    });
    
    // 한 번에 DOM 업데이트
    tbody.innerHTML = '';
    tbody.appendChild(fragment);
    
    // 페이지네이션 업데이트
    if (totalCount !== null) {
        updatePagination(document.querySelector('.data-table'), metaAdsCurrentPage, totalCount);
    }
    
    console.log('✅ 메타 광고별 성과 렌더링 완료');
}

// ─────────────────────────────────────────────
// 12) 페이지네이션 함수
// ─────────────────────────────────────────────
function updatePagination(table, currentPage, totalItems) {
    const itemsPerPage = 10;
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    
    if (totalPages <= 1) return;
    
    const paginationContainer = document.getElementById('pagination_meta_ads');
    if (!paginationContainer) return;
    
    let paginationHTML = '<div class="pagination">';
    
    // 이전 페이지 버튼
    if (currentPage > 1) {
        paginationHTML += `<button class="page-btn" onclick="changePage(${currentPage - 1})">이전</button>`;
    }
    
    // 페이지 번호들
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    for (let i = startPage; i <= endPage; i++) {
        if (i === currentPage) {
            paginationHTML += `<button class="page-btn active">${i}</button>`;
        } else {
            paginationHTML += `<button class="page-btn" onclick="changePage(${i})">${i}</button>`;
        }
    }
    
    // 다음 페이지 버튼
    if (currentPage < totalPages) {
        paginationHTML += `<button class="page-btn" onclick="changePage(${currentPage + 1})">다음</button>`;
    }
    
    paginationHTML += '</div>';
    paginationContainer.innerHTML = paginationHTML;
}

// 페이지 변경 함수
function changePage(page) {
    if (selectedMetaAccount) {
        metaAdsCurrentPage = page;
        fetchMetaAdsByAccount(selectedMetaAccount, page);
    }
}

// ─────────────────────────────────────────────
// 13) 테이블 정렬 기능
// ─────────────────────────────────────────────
function addTableSortEvents() {
    const tables = document.querySelectorAll('.data-table');
    tables.forEach(table => {
        const headers = table.querySelectorAll('th');
        headers.forEach((header, index) => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => {
                sortTable(table, index);
            });
        });
    });
}

function sortTable(table, columnIndex) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // 현재 정렬 방향 확인
    const header = table.querySelector(`th:nth-child(${columnIndex + 1})`);
    const isAscending = header.classList.contains('sort-asc');
    
    // 정렬 방향 토글
    table.querySelectorAll('th').forEach(th => th.classList.remove('sort-asc', 'sort-desc'));
    header.classList.add(isAscending ? 'sort-desc' : 'sort-asc');
    
    // 데이터 정렬
    rows.sort((a, b) => {
        const aValue = getCellValue(a, columnIndex);
        const bValue = getCellValue(b, columnIndex);
        
        // 숫자 정렬
        if (!isNaN(aValue) && !isNaN(bValue)) {
            return isAscending ? bValue - aValue : aValue - bValue;
        }
        
        // 문자열 정렬
        const aStr = String(aValue).toLowerCase();
        const bStr = String(bValue).toLowerCase();
        
        if (isAscending) {
            return bStr.localeCompare(aStr);
        } else {
            return aStr.localeCompare(bStr);
        }
    });
    
    // 정렬된 행들을 테이블에 다시 추가
    rows.forEach(row => tbody.appendChild(row));
}

function getCellValue(row, columnIndex) {
    const cell = row.querySelector(`td:nth-child(${columnIndex + 1})`);
    if (!cell) return '';
    
    let value = cell.textContent.trim();
    
    // 숫자 추출 (통화, 퍼센트 등 제거)
    const numericMatch = value.match(/[\d,]+/);
    if (numericMatch) {
        value = numericMatch[0].replace(/,/g, '');
        return parseFloat(value) || 0;
    }
    
    return value;
}

// ─────────────────────────────────────────────
// 14) 캠페인 필터 기능
// ─────────────────────────────────────────────
function addCampaignFilterEvents() {
    const filterCheckboxes = document.querySelectorAll('.campaign-filter input[type="checkbox"]');
    filterCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', filterMetaAdsByCampaign);
    });
}

function filterMetaAdsByCampaign() {
    if (!metaAdsAllData || metaAdsAllData.length === 0) return;
    
    const conversionFilter = document.getElementById('filter-conversion');
    const inflowFilter = document.getElementById('filter-inflow');
    const reachFilter = document.getElementById('filter-reach');
    
    const showConversion = conversionFilter ? conversionFilter.checked : true;
    const showInflow = inflowFilter ? inflowFilter.checked : true;
    const showReach = reachFilter ? reachFilter.checked : true;
    
    const filteredData = metaAdsAllData.filter(ad => {
        const campaignName = ad.campaign_name || '';
        
        if (campaignName.includes('전환') && showConversion) return true;
        if (campaignName.includes('유입') && showInflow) return true;
        if (campaignName.includes('도달') && showReach) return true;
        
        return false;
    });
    
    // 필터링된 데이터로 페이지네이션 업데이트
    const startIndex = (metaAdsCurrentPage - 1) * 10;
    const endIndex = startIndex + 10;
    const pageData = filteredData.slice(startIndex, endIndex);
    
    renderMetaAdsByAccount(pageData, filteredData.length);
}

// ─────────────────────────────────────────────
// 15) LIVE 광고 섹션 표시/숨김
// ─────────────────────────────────────────────
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
// 16) 디버깅용 전역 함수 (개발용)
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

function updateMobileTimestamp(latestUpdate) {
    const updatedAtText = document.getElementById('updatedAtText');
    if (!updatedAtText || !latestUpdate) return;
    
    try {
        console.log('🔍 원본 latest_update:', latestUpdate);
        
        // 다양한 날짜 형식 처리
        let dateStr = latestUpdate;
        
        // ✅ toLocaleString('ko-KR') 형식 처리 추가
        if (dateStr.includes('오전') || dateStr.includes('오후')) {
            // 2025. 8. 2. 오후 6:29:00 형식 처리
            const match = dateStr.match(/(\d+)\.\s*(\d+)\.\s*(\d+)\.\s*(오전|오후)\s*(\d+):(\d+):(\d+)/);
            if (match) {
                const [, year, month, day, ampm, hour, minute, second] = match;
                let adjustedHour = parseInt(hour);
                if (ampm === '오후' && adjustedHour !== 12) {
                    adjustedHour += 12;
                } else if (ampm === '오전' && adjustedHour === 12) {
                    adjustedHour = 0;
                }
                dateStr = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}T${adjustedHour.toString().padStart(2, '0')}:${minute}:${second}`;
                console.log('🔧 변환된 날짜 형식 (toLocaleString):', dateStr);
            }
        }
        // 2025-07-28-22-11 형식인 경우 처리
        else if (dateStr.includes('-') && dateStr.split('-').length >= 5) {
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
// 17) 전역 변수들
// ─────────────────────────────────────────────
let cafe24ProductSalesCurrentPage = 1;
let cafe24ProductSalesTotalCount = 0;
let metaAdsCurrentPage = 1;
let metaAdsTotalCount = 0;
let metaAdsAllData = []; // 전체 메타 광고 데이터 저장
let tableSortEventsAdded = false; // 테이블 정렬 이벤트 중복 등록 방지

// ─────────────────────────────────────────────
// 18) DOM 로드 시 초기화
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', initMobileDashboard);

// 🔥 추가 안전장치: 5초 후 모든 로딩 오버레이 강제 숨기기
setTimeout(() => {
    console.log('🔧 5초 후 모든 로딩 오버레이 강제 숨기기');
    hideAllLoadingOverlays();
}, 5000);