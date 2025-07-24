// File: static/js/common.js

// 로딩 상태 관리 함수들
function showLoading(target) {
  console.log("🔄 showLoading called for:", target);
  
  const $target = $(target);
  console.log("Target element:", $target);
  console.log("Target length:", $target.length);
  
  if ($target.length === 0) {
    console.error("❌ Target element not found:", target);
    return;
  }
  
  // 🔥 더 강력한 스타일 설정 - 다른 코드가 덮어쓰지 못하도록
  $target.css({
    'display': 'flex !important',
    'visibility': 'visible !important',
    'opacity': '1 !important',
    'pointer-events': 'auto !important'
  });
  
  // 🔥 인라인 스타일로도 강제 설정
  $target.attr('style', 'display: flex !important; visibility: visible !important; opacity: 1 !important; pointer-events: auto !important;');
  
  console.log("✅ Loading started for:", target);
  console.log("Final display style:", $target.css('display'));
}

function hideLoading(target) {
  console.log("✅ hideLoading called for:", target);
  
  const $target = $(target);
  
  if ($target.length === 0) {
    console.error("❌ Target element not found:", target);
    return;
  }
  
  // 직접 스타일 설정
  $target.css({
    'display': 'none',
    'visibility': 'hidden',
    'opacity': '0',
    'pointer-events': 'none'
  });
  
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

// 브라우저 캐시 강제 새로고침 함수
function forceRefreshCache() {
  console.log("🔄 브라우저 캐시 강제 새로고침 실행");
  
  // 모든 로딩 오버레이 강제 숨김
  forceHideAllLoading();
  
  // 페이지 새로고침 (캐시 무시)
  if (window.location.reload) {
    window.location.reload(true);
  } else {
    // fallback
    window.location.href = window.location.href + '?t=' + new Date().getTime();
  }
}

// 페이지 로드 시 자동으로 모든 로딩 오버레이 제거 (백업용)
$(document).ready(function() {
  // 60초 후 강제 제거 (최후의 수단)
  setTimeout(forceHideAllLoading, 60000);
  
  // 개발 환경에서만 디버깅 기능 활성화
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname.includes('dev')) {
    // 디버깅용 - 5초 후 로딩 오버레이 상태 확인
    setTimeout(debugLoadingOverlays, 5000);
    
    // 캐시 문제 해결을 위한 키보드 단축키 (Ctrl+Shift+R)
    $(document).keydown(function(e) {
      if (e.ctrlKey && e.shiftKey && e.keyCode === 82) { // Ctrl+Shift+R
        console.log("🔄 Ctrl+Shift+R 감지 - 캐시 강제 새로고침");
        forceRefreshCache();
      }
    });
  }
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
