// File: static/js/common.js

function showLoading(target) {
  console.log("[DEBUG] showLoading 호출됨:", target);
  $(target).css({ 
    display: "flex",
    visibility: "visible",
    opacity: "1"
  });
  $(target).closest(".table-wrapper, .performance-summary-wrapper").addClass("loading");
  console.log("[DEBUG] showLoading 완료:", target);
}

function hideLoading(target) {
  console.log("[DEBUG] hideLoading 호출됨:", target);
  
  // 1. 오버레이 완전히 숨김 (DOM에서 제거하지 않음)
  $(target).css({ 
    display: "none !important",
    visibility: "hidden !important",
    opacity: "0 !important"
  });
  
  // 2. 부모 컨테이너에서 loading 클래스 제거 (핵심!)
  $(target).closest(".table-wrapper, .performance-summary-wrapper").removeClass("loading");
  
  // 3. 모든 부모에서도 loading 클래스 제거
  $(target).parents().removeClass("loading");
  
  console.log("[DEBUG] hideLoading 완료:", target);
}

function getRequestData(page = 1, extra = {}) {
  const companyName = $("#accountFilter").val() || "all";
  const period = $("#periodFilter").val();
  const startDate = $("#startDate").val()?.trim() || "";
  const endDate = $("#endDate").val()?.trim() || "";

  return {
    company_name: companyName,
    period: period,
    start_date: startDate,
    end_date: endDate,
    page: page,
    limit: 1000,
    ...extra
  };
}

function updateUpdatedAtText(timestamp) {
  $("#updatedAtText").text(`최종 업데이트: ${timestamp}`);
}
