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
  $("#accountFilter, #periodFilter").change(function () {
    const period = $("#periodFilter").val();
    if (period !== "manual") {
      $("#startDate").val("");
      $("#endDate").val("");
      updateAllData();
    }
  });

  $("#endDate, #applyDateFilter").on("change click", function () {
    const period = $("#periodFilter").val();
    const endDate = $("#endDate").val()?.trim();
    if (period === "manual" && !endDate) return;
    updateAllData();
  });
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
  if (isLoading) return; // 이미 데이터 요청 중이면 중지

  const period = $("#periodFilter").val();
  const endDate = $("#endDate").val()?.trim();
  if (period === "manual" && !endDate) return;

  isLoading = true;

  // 의존성 로딩 스피너 시작 - 카페24 매출과 사이트 성과 요약 동시 표시
  showLoading("#loadingOverlayPerformanceSummary");

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
    // 필수 데이터는 병렬로 실행하되 실패해도 계속 진행
    await Promise.all([
      fetchCafe24SalesData(salesRequest).catch(e => {
        console.error("[ERROR] fetchCafe24SalesData 실패:", e);
      }),
      fetchCafe24ProductSalesData(productRequest).catch(e => {
        console.error("[ERROR] fetchCafe24ProductSalesData 실패:", e);
      }),
    ]);

    // 카페24 매출 완료 후 사이트 성과 요약 로딩 스피너도 함께 숨김
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

    // 유입 데이터 요청 (Promise 반환하지 않는 함수들은 try-catch로 처리)
    const fetchViewData = [];
    
    try {
      fetchViewItemSummaryData(1);
    } catch (e) {
      console.error("[ERROR] fetchViewItemSummaryData 실패:", e);
    }
    
    try {
      fetchGa4SourceSummaryData(1);
    } catch (e) {
      console.error("[ERROR] fetchGa4SourceSummaryData 실패:", e);
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
    console.log("✅ updateAllData completed");
  }
}

