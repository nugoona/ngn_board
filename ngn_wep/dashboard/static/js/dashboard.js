let isLoading = false;
const requestRegistry = {};

function latestAjaxRequestWrapper(key, ajaxOptions, onSuccess) {
  if (!requestRegistry[key]) requestRegistry[key] = { id: 0 };
  const requestId = ++requestRegistry[key].id;

  const originalSuccess = ajaxOptions.success;
  ajaxOptions.success = function (res, status, xhr) {
    if (requestId !== requestRegistry[key].id) {
      console.debug(`[SKIP] ${key} 오래된 응답 무시됨`);
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
  console.log("📋 dashboard.js document.ready 시작");
  
  $("#accountFilter, #periodFilter").change(function () {
    console.log("🔄 필터 변경 감지:", $(this).attr('id'), "값:", $(this).val());
    const period = $("#periodFilter").val();
    if (period !== "manual") {
      $("#startDate").val("");
      $("#endDate").val("");
      console.log("🚀 updateAllData() 호출 - 필터 변경");
      updateAllData();
    }
  });

  $("#endDate, #applyDateFilter").on("change click", function () {
    console.log("🔄 날짜 필터 변경 감지:", $(this).attr('id'));
    const period = $("#periodFilter").val();
    const endDate = $("#endDate").val()?.trim();
    if (period === "manual" && !endDate) return;
    console.log("🚀 updateAllData() 호출 - 날짜 필터 변경");
    updateAllData();
  });
  
  console.log("📋 dashboard.js document.ready 완료");
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
  console.log("🎯 updateAllData() 함수 시작");
  
  if (isLoading) {
    console.log("⚠️ 이미 로딩 중이므로 중단");
    return; // 이미 데이터 요청 중이면 중지
  }

  const period = $("#periodFilter").val();
  const endDate = $("#endDate").val()?.trim();
  console.log("📊 현재 필터 값:", { period, endDate });
  
  if (period === "manual" && !endDate) {
    console.log("⚠️ manual 모드에서 endDate가 없으므로 중단");
    return;
  }

  console.log("✅ updateAllData() 실행 조건 만족 - 로딩 시작");
  isLoading = true;

  // 🔥 즉시 의존성 로딩 스피너 시작 - 필터 변경 시에도 작동
  console.log("🔄 의존성 로딩 스피너 시작 - 필터 변경 감지");
  
  // 성과 요약 로딩 오버레이 즉시 표시
  const performanceOverlay = $("#loadingOverlayPerformanceSummary");
  console.log("🔍 성과 요약 오버레이 검색 결과:", performanceOverlay.length, "개 발견");
  
  if (performanceOverlay.length > 0) {
    console.log("✅ 성과 요약 로딩 오버레이 찾음 - 필터 변경 시 즉시 표시");
    
    // 즉시 모든 방법으로 표시
    performanceOverlay.show();
    performanceOverlay.css('display', 'flex');
    performanceOverlay.css('visibility', 'visible');
    performanceOverlay.css('opacity', '1');
    performanceOverlay.css('pointer-events', 'auto');
    
    // 강제 스타일 속성 설정
    performanceOverlay.attr('style', 'display: flex !important; visibility: visible !important; opacity: 1 !important; pointer-events: auto !important;');
    
    console.log("✅ 성과 요약 로딩 스피너 즉시 표시 완료 - 필터 변경");
  } else {
    console.error("❌ 성과 요약 로딩 오버레이를 찾을 수 없음");
    console.log("🔍 DOM에서 loadingOverlayPerformanceSummary 검색 중...");
    
    // DOM에서 직접 검색
    const allElements = document.querySelectorAll('[id*="loadingOverlay"]');
    console.log("🔍 모든 loadingOverlay 요소들:", allElements.length, "개");
    allElements.forEach((el, index) => {
      console.log(`🔍 ${index}: ${el.id}`);
    });
  }

  // 필수 데이터 요청 객체
  const salesRequest = getRequestData(1, {
    data_type: "cafe24_sales",
    date_type: $("input[name='dateType']:checked").val(),
    date_sort: $("#dateSort").val() || "desc",
    limit: 30,
  });

  const productRequest = getRequestData(1, {
    data_type: "cafe24_product_sales",
    sort_by: $("input[name='productSortType']:checked").val(),
    limit: 15,
  });

  try {
    console.log("🔄 Cafe24 데이터 요청 시작 - 필터 변경");
    
    // 필수 데이터는 병렬로 실행하되 실패해도 계속 진행
    const promises = [];
    
    // fetchCafe24SalesData 함수가 정의되어 있는지 확인
    if (typeof fetchCafe24SalesData === 'function') {
      promises.push(fetchCafe24SalesData(salesRequest).catch(e => {
        console.error("[ERROR] fetchCafe24SalesData 실패:", e);
      }));
    } else {
      console.warn("[WARNING] fetchCafe24SalesData 함수가 정의되지 않음");
    }
    
    // fetchCafe24ProductSalesData 함수가 정의되어 있는지 확인
    if (typeof fetchCafe24ProductSalesData === 'function') {
      promises.push(fetchCafe24ProductSalesData(productRequest).catch(e => {
        console.error("[ERROR] fetchCafe24ProductSalesData 실패:", e);
      }));
    } else {
      console.warn("[WARNING] fetchCafe24ProductSalesData 함수가 정의되지 않음");
    }
    
    // Promise가 있을 때만 실행
    if (promises.length > 0) {
      await Promise.all(promises);
    }

    console.log("✅ Cafe24 데이터 요청 완료 - 필터 변경");
    
    // 카페24 매출 완료 후 사이트 성과 요약 로딩 스피너도 함께 숨김
    console.log("✅ 의존성 로딩 스피너 종료 - 필터 변경");
    hideLoading("#loadingOverlayPerformanceSummary");

    // 메인 성과 데이터 요청 (Promise 반환하지 않는 함수들은 try-catch로 처리)
    const fetchMainData = [];
    
    try {
      fetchPerformanceSummaryData();
    } catch (e) {
      console.error("[ERROR] fetchPerformanceSummaryData 실패:", e);
    }
    
    try {
      fetchMonthlyNetSalesVisitors();
    } catch (e) {
      console.error("[ERROR] fetchMonthlyNetSalesVisitors 실패:", e);
    }

    // 플랫폼 데이터 요청 (Promise 반환하지 않는 함수들은 try-catch로 처리)
    const fetchPlatformData = [];
    
    try {
      fetchPlatformSalesSummary();
    } catch (e) {
      console.error("[ERROR] fetchPlatformSalesSummary 실패:", e);
    }
    
    try {
      fetchPlatformSalesRatio();
    } catch (e) {
      console.error("[ERROR] fetchPlatformSalesRatio 실패:", e);
    }

    // 유입 데이터 요청은 각각의 JS 파일에서 자체적으로 처리됨
    // fetchViewItemSummaryData와 fetchGa4SourceSummaryData는 별도 파일에서 정의됨
    
    try {
      fetchGa4ViewItemSummaryData();
    } catch (e) {
      console.error("[ERROR] fetchGa4ViewItemSummaryData 실패:", e);
    }
    
    try {
      fetchGa4SourceSummaryData();
    } catch (e) {
      console.error("[ERROR] fetchGa4SourceSummaryData 실패:", e);
    }
    
    try {
      fetchProductSalesRatio();
    } catch (e) {
      console.error("[ERROR] fetchProductSalesRatio 실패:", e);
    }

    // 빈 배열이므로 Promise.all 호출 불필요
    // await Promise.all([
    //   Promise.all(fetchMainData),
    //   Promise.all(fetchPlatformData),
    //   Promise.all(fetchViewData)
    // ]);

  } catch (e) {
    console.error("[ERROR] updateAllData() 전체 오류:", e);
    // 에러 발생 시에도 로딩 스피너 숨김
    hideLoading("#loadingOverlayPerformanceSummary");
  } finally {
    isLoading = false;
    // 각 위젯이 자체적으로 로딩 상태를 관리하므로 전역 제거하지 않음
    console.log("✅ updateAllData completed - 필터 변경");
  }
}

