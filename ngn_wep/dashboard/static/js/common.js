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
  
  // 10초 후 자동으로 로딩 해제 (무한로딩 방지)
  setTimeout(() => {
    console.log("[DEBUG] 자동 로딩 해제:", target);
    hideLoading(target);
  }, 10000);
}

function hideLoading(target) {
  console.log("[DEBUG] hideLoading 호출됨:", target);
  
  // 1. 오버레이 완전히 숨김
  $(target).hide();
  $(target).css({ 
    display: "none !important",
    visibility: "hidden !important",
    opacity: "0 !important"
  });
  
  // 2. 부모 컨테이너에서 loading 클래스 제거 (핵심!)
  $(target).closest(".table-wrapper, .performance-summary-wrapper").removeClass("loading");
  
  // 3. 모든 부모에서도 loading 클래스 제거
  $(target).parents().removeClass("loading");
  
  // 4. 강제로 모든 loading 클래스 제거
  $(".loading").removeClass("loading");
  
  console.log("[DEBUG] hideLoading 완료:", target);
}

// 모든 로딩 오버레이 강제 해제
function forceHideAllLoading() {
  console.log("[DEBUG] 모든 로딩 강제 해제");
  
  // 모든 로딩 오버레이 숨김
  $(".loading-overlay").hide().css({
    display: "none !important",
    visibility: "hidden !important", 
    opacity: "0 !important"
  });
  
  // 모든 loading 클래스 제거
  $(".loading").removeClass("loading");
  
  console.log("[DEBUG] 모든 로딩 강제 해제 완료");
}

// 페이지 로드 시 모든 로딩 해제
$(document).ready(function() {
  setTimeout(forceHideAllLoading, 1000);
  
  // 15초 후에도 한번 더 실행
  setTimeout(forceHideAllLoading, 15000);
});

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
