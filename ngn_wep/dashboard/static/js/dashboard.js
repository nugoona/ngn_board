// ✅ 전역 isLoading 상태 (filters.js와 공유)
window.isLoading = window.isLoading || false;
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
      debugLog("🚀 필터 변경 - filters.js에서 처리됨 (중복 호출 방지)");
      // updateAllData(); // 중복 호출 방지를 위해 주석 처리 - filters.js에서 처리
    }
  });

  $("#endDate, #applyDateFilter").on("change click", function () {
    debugLog("🔄 날짜 필터 변경 감지:", $(this).attr('id'));
    const period = $("#periodFilter").val();
    const endDate = $("#endDate").val()?.trim();
    if (period === "manual" && !endDate) return;
    debugLog("🚀 날짜 필터 변경 - filters.js에서 처리됨 (중복 호출 방지)");
    // updateAllData(); // 중복 호출 방지를 위해 주석 처리 - filters.js에서 처리
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

// updateAllData 함수를 전역으로 노출
window.updateAllData = async function() {
  console.log("🎯 dashboard.js의 updateAllData() 함수 시작 (Batch API)");

  if (window.isLoading) {
    console.log("⚠️ 이미 로딩 중이므로 중단");
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
  window.isLoading = true;

  // ✅ 모든 위젯의 로딩 스피너 표시
  const loadingOverlays = [
    "#loadingOverlayPerformanceSummary",
    "#loadingOverlayCafe24Sales",
    "#loadingOverlayCafe24Products",
    "#loadingOverlayGa4Source",
    "#loadingOverlayViewitemSummary",
    "#loadingOverlayProductSalesRatio",
    "#loadingOverlayPlatformSalesSummary",
    "#loadingOverlayPlatformSalesRatio",
    "#loadingOverlayMonthlyChart"
  ];
  
  loadingOverlays.forEach(overlayId => {
    const overlay = $(overlayId);
    if (overlay.length > 0) {
      showLoading(overlayId);
    }
  });

  // ✅ 파라미터 수집 (명확한 Selector)
  const companyName = sessionStorage.getItem("selectedCompany") || $("#accountFilter").val() || "all";
  const date_type = $("input[name='dateType']:checked").val() || "summary";
  const date_sort = $("#dateSort").val() || "desc";
  const sort_by = $("input[name='cafe24_product_sort']:checked").val() || "sales";
  const platform_date_type = $("input[name='platformDateType']:checked").val() || "summary";
  const platform_date_sort = $("#platformDateSort").val() || "desc";

  let startDate = "", endDateParam = "";
  if (period === "manual") {
    startDate = $("#startDate").val()?.trim() || "";
    endDateParam = $("#endDate").val()?.trim() || "";
  }

  // ✅ Batch API 요청 데이터 구성
  const batchRequestData = {
    company_name: companyName,
    period: period,
    date_type: date_type,
    date_sort: date_sort,
    sort_by: sort_by,
    platform_date_type: platform_date_type,
    platform_date_sort: platform_date_sort
  };

  if (period === "manual") {
    batchRequestData.start_date = startDate;
    batchRequestData.end_date = endDateParam;
  }

  try {
    debugLog("🔄 Batch API 요청 시작:", batchRequestData);
    
    // ✅ Batch API 호출
    const response = await fetch('/dashboard/get_batch_dashboard_data', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(batchRequestData)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    debugLog("✅ Batch API 응답 받음:", data);

    if (!data || data.status !== "success") {
      throw new Error("Batch API 응답 오류: " + (data.message || "알 수 없음"));
    }

    // ✅ 응답 데이터를 각 렌더링 함수에 분배
    try {
      if (typeof renderPerformanceSummaryWidget === 'function' && data.performance_summary !== undefined) {
        renderPerformanceSummaryWidget(data.performance_summary, data.latest_update);
      } else {
        debugLog("[WARNING] renderPerformanceSummaryWidget 함수가 없거나 데이터 없음");
      }
    } catch (e) {
      debugError("[ERROR] renderPerformanceSummaryWidget 실패:", e);
    }

    try {
      if (typeof renderCafe24SalesWidget === 'function' && data.cafe24_sales !== undefined) {
        renderCafe24SalesWidget(data.cafe24_sales, data.cafe24_sales_total_count || 0);
      } else {
        debugLog("[WARNING] renderCafe24SalesWidget 함수가 없거나 데이터 없음");
      }
    } catch (e) {
      debugError("[ERROR] renderCafe24SalesWidget 실패:", e);
    }

    try {
      if (typeof renderCafe24ProductsWidget === 'function' && data.cafe24_product_sales !== undefined) {
        renderCafe24ProductsWidget(data.cafe24_product_sales, data.cafe24_product_sales_total_count || 0);
      } else {
        debugLog("[WARNING] renderCafe24ProductsWidget 함수가 없거나 데이터 없음");
      }
    } catch (e) {
      debugError("[ERROR] renderCafe24ProductsWidget 실패:", e);
    }

    try {
      if (typeof renderGa4SourceWidget === 'function' && data.ga4_source_summary !== undefined) {
        renderGa4SourceWidget(data.ga4_source_summary, data.ga4_source_summary_total_count || 0);
      } else {
        debugLog("[WARNING] renderGa4SourceWidget 함수가 없거나 데이터 없음");
      }
    } catch (e) {
      debugError("[ERROR] renderGa4SourceWidget 실패:", e);
    }

    try {
      if (typeof renderViewItemSummaryWidget === 'function' && data.viewitem_summary !== undefined) {
        renderViewItemSummaryWidget(data.viewitem_summary, data.viewitem_summary_total_count || 0);
      } else {
        debugLog("[WARNING] renderViewItemSummaryWidget 함수가 없거나 데이터 없음");
      }
    } catch (e) {
      debugError("[ERROR] renderViewItemSummaryWidget 실패:", e);
    }

    try {
      if (typeof renderMonthlyNetSalesVisitorsWidget === 'function' && data.monthly_net_sales_visitors !== undefined) {
        renderMonthlyNetSalesVisitorsWidget(data.monthly_net_sales_visitors);
      } else {
        debugLog("[WARNING] renderMonthlyNetSalesVisitorsWidget 함수가 없거나 데이터 없음");
      }
    } catch (e) {
      debugError("[ERROR] renderMonthlyNetSalesVisitorsWidget 실패:", e);
    }

    try {
      if (typeof renderPlatformSalesSummaryWidget === 'function' && data.platform_sales_summary !== undefined) {
        renderPlatformSalesSummaryWidget(data.platform_sales_summary);
      } else {
        debugLog("[WARNING] renderPlatformSalesSummaryWidget 함수가 없거나 데이터 없음");
      }
    } catch (e) {
      debugError("[ERROR] renderPlatformSalesSummaryWidget 실패:", e);
    }

    try {
      if (typeof renderPlatformSalesRatioWidget === 'function' && data.platform_sales_ratio !== undefined) {
        renderPlatformSalesRatioWidget(data.platform_sales_ratio);
      } else {
        debugLog("[WARNING] renderPlatformSalesRatioWidget 함수가 없거나 데이터 없음");
      }
    } catch (e) {
      debugError("[ERROR] renderPlatformSalesRatioWidget 실패:", e);
    }

    try {
      if (typeof renderProductSalesRatioWidget === 'function' && data.product_sales_ratio !== undefined) {
        renderProductSalesRatioWidget(data.product_sales_ratio);
      } else {
        debugLog("[WARNING] renderProductSalesRatioWidget 함수가 없거나 데이터 없음");
      }
    } catch (e) {
      debugError("[ERROR] renderProductSalesRatioWidget 실패:", e);
    }

    debugLog("✅ Batch API 데이터 분배 완료");

  } catch (e) {
    debugError("[ERROR] Batch API 실패, 기존 방식으로 폴백:", e);
    
    // ✅ 폴백: 기존 개별 API 호출 방식으로 전환
    try {
      const salesRequest = getRequestData(1, {
        data_type: "cafe24_sales",
        date_type: date_type,
        date_sort: date_sort,
        limit: 30,
      });

      const productRequest = getRequestData(1, {
        data_type: "cafe24_product_sales",
        sort_by: sort_by,
        limit: 13,
      });

      const promises = [];
      
      if (typeof fetchCafe24SalesData === 'function') {
        promises.push(fetchCafe24SalesData(salesRequest).catch(e => {
          debugError("[ERROR] fetchCafe24SalesData 실패:", e);
        }));
      }
      
      if (typeof fetchCafe24ProductSalesData === 'function') {
        promises.push(fetchCafe24ProductSalesData(productRequest).catch(e => {
          debugError("[ERROR] fetchCafe24ProductSalesData 실패:", e);
        }));
      }
      
      if (promises.length > 0) {
        await Promise.all(promises);
      }

      // 기존 개별 함수 호출
      if (typeof fetchPerformanceSummaryData === 'function') {
        fetchPerformanceSummaryData();
      }
      if (typeof fetchMonthlyNetSalesVisitors === 'function') {
        fetchMonthlyNetSalesVisitors();
      }
      if (typeof fetchPlatformSalesSummary === 'function') {
        fetchPlatformSalesSummary();
      }
      if (typeof fetchPlatformSalesRatio === 'function') {
        fetchPlatformSalesRatio();
      }
      if (typeof fetchGa4ViewItemSummaryData === 'function') {
        const requestData = getRequestData(1, {});
        fetchGa4ViewItemSummaryData(requestData);
      }
      if (typeof fetchGa4SourceSummaryData === 'function') {
        fetchGa4SourceSummaryData(1);
      }
      if (typeof fetchProductSalesRatio === 'function') {
        fetchProductSalesRatio();
      }

      debugLog("✅ 폴백 방식으로 데이터 로드 완료");
    } catch (fallbackError) {
      debugError("[ERROR] 폴백 방식도 실패:", fallbackError);
    }
  } finally {
    window.isLoading = false;

    // ✅ 안전장치: 모든 로딩 스피너 제거
    loadingOverlays.forEach(overlayId => {
      hideLoading(overlayId);
    });

    debugLog("✅ updateAllData completed - Batch API");
  }
}





