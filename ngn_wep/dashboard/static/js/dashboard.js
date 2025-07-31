let isLoading = false;
const requestRegistry = {};

// ✅ 배포 환경에서는 디버깅 로그 비활성화 (전역 변수로 선언)
window.isProduction = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
const debugLog = window.isProduction ? () => {} : console.log;
const debugError = window.isProduction ? () => {} : console.error;

function latestAjaxRequestWrapper(key, ajaxOptions, onSuccess) {
  if (!requestRegistry[key]) requestRegistry[key] = { id: 0 };
  const requestId = ++requestRegistry[key].id;

  const originalSuccess = ajaxOptions.success;
  ajaxOptions.success = function (res, status, xhr) {
    if (requestId !== requestRegistry[key].id) {
      debugLog(`[SKIP] ${key} 오래된 응답 무시됨`);
      return;
    }
    onSuccess(res, status, xhr);
    if (originalSuccess) originalSuccess(res, status, xhr);
  };

  const originalError = ajaxOptions.error;
  ajaxOptions.error = function (xhr, status, error) {
    if (requestId === requestRegistry[key].id && originalError) {
      originalError(xhr, status, error);
    }
  };

  $.ajax(ajaxOptions);
}

window.latestAjaxRequest = latestAjaxRequestWrapper;

$(window).on("load", () => updateAllData());

$(document).ready(function () {
  debugLog("📋 dashboard.js document.ready 시작");
  
  $("#accountFilter, #periodFilter").change(function () {
    debugLog("🔄 필터 변경 감지:", $(this).attr('id'), "값:", $(this).val());
    const period = $("#periodFilter").val();
    if (period !== "manual") {
      $("#startDate").val("");
      $("#endDate").val("");
      debugLog("🚀 updateAllData() 호출 - 필터 변경");
      updateAllData();
    }
  });

  $("#endDate, #applyDateFilter").on("change click", function () {
    debugLog("🔄 날짜 필터 변경 감지:", $(this).attr('id'));
    const period = $("#periodFilter").val();
    const endDate = $("#endDate").val()?.trim();
    if (period === "manual" && !endDate) return;
    debugLog("🚀 updateAllData() 호출 - 날짜 필터 변경");
    updateAllData();
  });
  
  debugLog("📋 dashboard.js document.ready 완료");
});

// showLoading/hideLoading 함수는 common.js에서 정의됨

function cleanData(value, decimalPlaces = 0) {
  if (value === undefined || value === null || value === "-" || value === "") return "0";
  if (!isNaN(value)) {
    return parseFloat(value).toLocaleString("en-US", {
      minimumFractionDigits: decimalPlaces,
      maximumFractionDigits: decimalPlaces,
    });
  }
  return value;
}
window.cleanData = cleanData;

function getRequestData(page = 1, extra = {}) {
  const companyName = sessionStorage.getItem("selectedCompany") || $("#accountFilter").val() || "all";
  const period = sessionStorage.getItem("selectedPeriod") || $("#periodFilter").val() || "today";

  let startDate = "", endDate = "";
  if (period === "manual") {
    startDate = $("#startDate").val()?.trim() || "";
    endDate = $("#endDate").val()?.trim() || "";
  }

  // 기간 필터가 필요 없는 테이블에 대해서는 start_date, end_date를 제외하도록 조건 추가
  const requestData = {
    company_name: companyName,
    period,
    page,
    ...extra,
  };

  if (period === "manual") {
    requestData.start_date = startDate;
    requestData.end_date = endDate;
  }

  return requestData;
}

async function updateAllData() {
  debugLog("🎯 updateAllData() 함수 시작");
  
  if (isLoading) {
    debugLog("⚠️ 이미 로딩 중이므로 중단");
    return; // 이미 데이터 요청 중이면 중지
  }

  const period = $("#periodFilter").val();
  const endDate = $("#endDate").val()?.trim();
  debugLog("📊 현재 필터 값:", { period, endDate });
  
  if (period === "manual" && !endDate) {
    debugLog("⚠️ manual 모드에서 endDate가 없으므로 중단");
    return;
  }

  debugLog("✅ updateAllData() 실행 조건 만족 - 로딩 시작");
  isLoading = true;

  // 🔥 즉시 의존성 로딩 스피너 시작 - 필터 변경 시에도 작동
  debugLog("🔄 의존성 로딩 스피너 시작 - 필터 변경 감지");
  
  // 🔥 모든 위젯의 로딩 스피너 표시 (사용자 경험 개선)
  const loadingOverlays = [
    "#loadingOverlayPerformanceSummary",  // 성과 요약
    "#loadingOverlayCafe24Sales",        // 카페24 매출
    "#loadingOverlayCafe24Products",     // 카페24 상품판매
    "#loadingOverlayGa4Source",          // GA4 소스별 유입
    "#loadingOverlayViewitemSummary",    // 상품 조회 요약
    "#loadingOverlayProductSalesRatio"   // 상품 판매 비율
  ];
  
  loadingOverlays.forEach(overlayId => {
    const overlay = $(overlayId);
    if (overlay.length > 0) {
      debugLog(`✅ ${overlayId} 로딩 스피너 표시`);
      showLoading(overlayId);
    } else {
      debugLog(`⚠️ ${overlayId} 로딩 오버레이를 찾을 수 없음`);
    }
  });

  // 필수 데이터 요청 객체
  const salesRequest = getRequestData(1, {
    data_type: "cafe24_sales",
    date_type: $("input[name='dateType']:checked").val(),
    date_sort: $("#dateSort").val() || "desc",
    limit: 30,
  });

  const productRequest = getRequestData(1, {
    data_type: "cafe24_product_sales",
    sort_by: $("input[name='cafe24_product_sort']:checked").val() || "sales",
    limit: 13,
  });

  try {
    debugLog("🔄 Cafe24 데이터 요청 시작 - 필터 변경");
    
    // 필수 데이터는 병렬로 실행하되 실패해도 계속 진행
    const promises = [];
    
    // fetchCafe24SalesData 함수가 정의되어 있는지 확인
    if (typeof fetchCafe24SalesData === 'function') {
      promises.push(fetchCafe24SalesData(salesRequest).catch(e => {
        debugError("[ERROR] fetchCafe24SalesData 실패:", e);
      }));
    } else {
      debugLog("[WARNING] fetchCafe24SalesData 함수가 정의되지 않음");
    }
    
    // fetchCafe24ProductSalesData 함수가 정의되어 있는지 확인
    if (typeof fetchCafe24ProductSalesData === 'function') {
      promises.push(fetchCafe24ProductSalesData(productRequest).catch(e => {
        debugError("[ERROR] fetchCafe24ProductSalesData 실패:", e);
      }));
    } else {
      debugLog("[WARNING] fetchCafe24ProductSalesData 함수가 정의되지 않음");
    }
    
    // Promise가 있을 때만 실행
    if (promises.length > 0) {
      await Promise.all(promises);
    }

    debugLog("✅ Cafe24 데이터 요청 완료 - 필터 변경");
    
    // 🔥 사이트 성과 요약 로딩 스피너는 모든 데이터 요청 완료 후에 숨김
    // (카페24 매출 완료 후 바로 숨기지 않음)

    // 메인 성과 데이터 요청 (Promise 반환하지 않는 함수들은 try-catch로 처리)
    const fetchMainData = [];
    
    try {
      fetchPerformanceSummaryData();
    } catch (e) {
      debugError("[ERROR] fetchPerformanceSummaryData 실패:", e);
    }
    
    try {
      fetchMonthlyNetSalesVisitors();
    } catch (e) {
      debugError("[ERROR] fetchMonthlyNetSalesVisitors 실패:", e);
    }

    // 플랫폼 데이터 요청 (Promise 반환하지 않는 함수들은 try-catch로 처리)
    const fetchPlatformData = [];
    
    try {
      fetchPlatformSalesSummary();
    } catch (e) {
      debugError("[ERROR] fetchPlatformSalesSummary 실패:", e);
    }
    
    try {
      fetchPlatformSalesRatio();
    } catch (e) {
      debugError("[ERROR] fetchPlatformSalesRatio 실패:", e);
    }

    // 유입 데이터 요청은 각각의 JS 파일에서 자체적으로 처리됨
    // fetchViewItemSummaryData와 fetchGa4SourceSummaryData는 별도 파일에서 정의됨
    
    try {
      if (typeof fetchGa4ViewItemSummaryData === 'function') {
        const requestData = getRequestData(1, {});
        fetchGa4ViewItemSummaryData(requestData);
      } else {
        debugLog("[WARNING] fetchGa4ViewItemSummaryData 함수가 정의되지 않음");
      }
    } catch (e) {
      debugError("[ERROR] fetchGa4ViewItemSummaryData 실패:", e);
    }
    
    try {
      if (typeof fetchGa4SourceSummaryData === 'function') {
        fetchGa4SourceSummaryData(1);
      } else {
        debugLog("[WARNING] fetchGa4SourceSummaryData 함수가 정의되지 않음");
      }
    } catch (e) {
      debugError("[ERROR] fetchGa4SourceSummaryData 실패:", e);
    }
    
    try {
      if (typeof fetchProductSalesRatio === 'function') {
        fetchProductSalesRatio();
      } else {
        debugLog("[WARNING] fetchProductSalesRatio 함수가 정의되지 않음");
      }
    } catch (e) {
      debugError("[ERROR] fetchProductSalesRatio 실패:", e);
    }

    // 🔥 모든 데이터 요청 완료 후 사이트 성과 요약 로딩 스피너 숨김 - 제거
    // 🔥 performance_summary.js에서 독립적으로 관리하므로 dashboard.js에서 숨기지 않음
    // debugLog("✅ 모든 데이터 요청 완료 - 사이트 성과 요약 로딩 스피너 종료");
    // hideLoading("#loadingOverlayPerformanceSummary");

  } catch (e) {
    debugError("[ERROR] updateAllData() 전체 오류:", e);
    // 🔥 에러 발생 시에도 로딩 스피너 숨김 - 제거
    // 🔥 performance_summary.js에서 독립적으로 관리
    // hideLoading("#loadingOverlayPerformanceSummary");
  } finally {
    isLoading = false;
    // 각 위젯이 자체적으로 로딩 상태를 관리하므로 전역 제거하지 않음
    debugLog("✅ updateAllData completed - 필터 변경");
  }
}





