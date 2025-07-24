// File: static/js/common.js

function showLoading(target) {
  console.log("[DEBUG] showLoading 호출됨:", target);
  $(target).css({ display: "flex" });
  $(target).closest(".table-wrapper, .performance-summary-wrapper").addClass("loading");
  console.log("[DEBUG] showLoading 완료:", target);
}

function hideLoading(target) {
  console.log("[DEBUG] hideLoading 호출됨:", target);
  $(target).css({ display: "none" });
  $(target).closest(".table-wrapper, .performance-summary-wrapper").removeClass("loading");
  // 추가: 스피너와 로딩 텍스트도 완전히 숨김
  $(target).find(".spinner, .loading-text").hide();
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
