// File: static/js/common.js

function showLoading(target) {
  console.log("[DEBUG] showLoading 호출됨:", target);
  $(target).css({ display: "flex" });
  $(target).closest(".table-wrapper, .performance-summary-wrapper").addClass("loading");
  console.log("[DEBUG] showLoading 완료:", target);
}

function hideLoading(target) {
  console.log("[DEBUG] hideLoading 호출됨:", target);
  
  // 1. 오버레이 자체를 숨김
  $(target).css({ display: "none" });
  
  // 2. 부모 컨테이너에서 loading 클래스 제거 (핵심!)
  $(target).closest(".table-wrapper, .performance-summary-wrapper").removeClass("loading");
  
  // 3. 스피너와 로딩 텍스트를 강제로 숨김
  $(target).find(".spinner, .loading-text").hide();
  
  // 4. 추가: 오버레이 내부 모든 요소를 숨김
  $(target).find("*").hide();
  
  // 5. 추가: !important로 강제 숨김
  $(target).css({ 
    display: "none !important",
    visibility: "hidden !important",
    opacity: "0 !important"
  });
  
  // 6. 추가: 부모 컨테이너에서도 loading 클래스 제거
  $(target).parents().removeClass("loading");
  
  // 7. 추가: 오버레이 요소를 DOM에서 완전히 제거
  $(target).remove();
  
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
