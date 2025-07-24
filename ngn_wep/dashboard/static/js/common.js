// File: static/js/common.js

// 로딩 상태 관리 함수들
function showLoading(target) {
  console.log("🔄 showLoading called for:", target);
  
  // target이 이미 로딩 오버레이인 경우
  if ($(target).hasClass('loading-overlay')) {
    $(target).addClass('loading').show().css({
      display: "flex",
      visibility: "visible",
      opacity: "1"
    });
  } else {
    // target이 컨테이너인 경우, 내부의 로딩 오버레이를 찾아서 표시
    const overlay = $(target).find('.loading-overlay');
    if (overlay.length > 0) {
      $(target).addClass('loading');
      overlay.show().css({
        display: "flex",
        visibility: "visible",
        opacity: "1"
      });
    }
  }
  
  console.log("✅ Loading started for:", target);
}

function hideLoading(target) {
  console.log("✅ hideLoading called for:", target);
  
  // target이 이미 로딩 오버레이인 경우
  if ($(target).hasClass('loading-overlay')) {
    $(target).removeClass('loading').hide().css({
      display: "none",
      visibility: "hidden",
      opacity: "0"
    });
  } else {
    // target이 컨테이너인 경우, 내부의 로딩 오버레이를 찾아서 숨김
    const overlay = $(target).find('.loading-overlay');
    if (overlay.length > 0) {
      $(target).removeClass('loading');
      overlay.hide().css({
        display: "none",
        visibility: "hidden",
        opacity: "0"
      });
    }
  }
  
  console.log("✅ Loading completed for:", target);
}

// 긴급 상황용 강제 제거 함수
function forceHideAllLoading() {
  console.log("🚨 FORCE HIDING ALL LOADING OVERLAYS");
  
  // 모든 로딩 클래스 제거
  $(".loading").removeClass("loading");
  
  // 모든 로딩 오버레이 숨김
  $(".loading-overlay").hide().css({
    display: "none",
    visibility: "hidden",
    opacity: "0"
  });
  
  console.log("✅ All loading overlays force-hidden");
}

// 페이지 로드 시 자동으로 모든 로딩 오버레이 제거 (백업용)
$(document).ready(function() {
  // 30초 후 강제 제거 (최후의 수단)
  setTimeout(forceHideAllLoading, 30000);
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
