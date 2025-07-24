// File: static/js/common.js

// 로딩 상태 관리 함수들
function showLoading(target) {
  console.log("🔄 showLoading called for:", target);
  
  // target이 이미 로딩 오버레이인 경우
  if ($(target).hasClass('loading-overlay')) {
    $(target).addClass('loading').attr('style', 'display: flex !important; visibility: visible !important; opacity: 1 !important; pointer-events: auto !important;');
  } else {
    // target이 컨테이너인 경우, 내부의 로딩 오버레이를 찾아서 표시
    const overlay = $(target).find('.loading-overlay');
    if (overlay.length > 0) {
      $(target).addClass('loading');
      overlay.attr('style', 'display: flex !important; visibility: visible !important; opacity: 1 !important; pointer-events: auto !important;');
    }
  }
  
  console.log("✅ Loading started for:", target);
}

function hideLoading(target) {
  console.log("✅ hideLoading called for:", target);
  
  // target이 이미 로딩 오버레이인 경우
  if ($(target).hasClass('loading-overlay')) {
    $(target).removeClass('loading').attr('style', 'display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important;');
  } else {
    // target이 컨테이너인 경우, 내부의 로딩 오버레이를 찾아서 숨김
    const overlay = $(target).find('.loading-overlay');
    if (overlay.length > 0) {
      $(target).removeClass('loading');
      overlay.attr('style', 'display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important;');
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
  $(".loading-overlay").attr('style', 'display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important;');
  
  console.log("✅ All loading overlays force-hidden");
}

// 디버깅용 함수 - 로딩 오버레이 상태 확인
function debugLoadingOverlays() {
  console.log("🔍 현재 로딩 오버레이 상태:");
  $(".loading-overlay").each(function(index) {
    const $overlay = $(this);
    const id = $overlay.attr('id') || `overlay-${index}`;
    const display = $overlay.css('display');
    const visibility = $overlay.css('visibility');
    const opacity = $overlay.css('opacity');
    const style = $overlay.attr('style');
    
    console.log(`  ${id}: display=${display}, visibility=${visibility}, opacity=${opacity}`);
    console.log(`    style attribute: ${style}`);
  });
}

// 페이지 로드 시 자동으로 모든 로딩 오버레이 제거 (백업용)
$(document).ready(function() {
  // 60초 후 강제 제거 (최후의 수단)
  setTimeout(forceHideAllLoading, 60000);
  
  // 디버깅용 - 5초 후 로딩 오버레이 상태 확인
  setTimeout(debugLoadingOverlays, 5000);
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
