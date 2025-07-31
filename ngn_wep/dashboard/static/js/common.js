// File: static/js/common.js

// 로딩 상태 관리 함수들
function showLoading(target) {
  console.log("🔄 showLoading called for:", target);
  
  // 🔥 성능 최적화: 프로덕션에서는 로그 비활성화
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    // 프로덕션에서는 로그 출력 안함
  } else {
    console.log("🔄 showLoading called for:", target);
  }
  
  const $target = $(target);
  
  if ($target.length === 0) {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      console.error("❌ Target element not found:", target);
    }
    return;
  }
  
  // 🔥 table-wrapper에 loading 클래스 추가
  const $tableWrapper = $target.closest('.table-wrapper');
  if ($tableWrapper.length > 0) {
    $tableWrapper.addClass('loading');
  }
  
  // ✅ 로딩 스피너 표시 - 완전 투명 배경
  $target.attr('style', `
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    z-index: 1000 !important;
    background: transparent !important;
    background-color: transparent !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
  `);
  
  // 스피너만 보이도록 설정 (텍스트는 숨김)
  $target.find('.spinner').css({
    'display': 'block !important',
    'visibility': 'visible !important',
    'opacity': '1 !important'
  });
  
  // 로딩 텍스트 숨김
  $target.find('.loading-text').css({
    'display': 'none !important',
    'visibility': 'hidden !important',
    'opacity': '0 !important'
  });
  
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    console.log("✅ Loading started for:", target);
  }
}

function hideLoading(target) {
  console.log("✅ hideLoading called for:", target);
  
  const $target = $(target);
  
  if ($target.length === 0) {
    console.error("❌ Target element not found:", target);
    return;
  }
  
  // 직접 스타일 설정 - 더 확실한 숨김
  $target.attr('style', `
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
  `);
  
  // 스피너와 텍스트도 숨김
  $target.find('.spinner, .loading-text').css({
    'display': 'none !important',
    'visibility': 'hidden !important',
    'opacity': '0 !important'
  });
  
  // 🔥 table-wrapper에서 loading 클래스 제거
  const $tableWrapper = $target.closest('.table-wrapper');
  if ($tableWrapper.length > 0) {
    $tableWrapper.removeClass('loading');
  }
  
  console.log("✅ Loading completed for:", target);
}

// 긴급 상황용 강제 제거 함수
function forceHideAllLoading() {
  console.log("🚨 FORCE HIDING ALL LOADING OVERLAYS");
  
  // 모든 로딩 클래스 제거
  $(".loading").removeClass("loading");
  
  // 🔥 모든 table-wrapper에서 loading 클래스 제거
  $(".table-wrapper").removeClass("loading");
  
  // 모든 로딩 오버레이 숨김 - 완전 투명하게 설정
  $(".loading-overlay").each(function() {
    $(this).attr('style', `
      display: none !important;
      visibility: hidden !important;
      opacity: 0 !important;
      pointer-events: none !important;
      background: transparent !important;
      background-color: transparent !important;
      backdrop-filter: none !important;
      -webkit-backdrop-filter: none !important;
    `);
  });
  
  // 스피너와 텍스트도 숨김
  $(".spinner, .loading-text").css({
    'display': 'none !important',
    'visibility': 'hidden !important',
    'opacity': '0 !important'
  });
  
  console.log("✅ All loading overlays force-hidden");
}

// 전체 페이지 로딩 오버레이 제어 함수
function showFullPageLoading() {
  console.log("🔄 전체 페이지 로딩 시작");
  const overlay = document.getElementById("fullPageLoadingOverlay");
  if (overlay) {
    overlay.style.display = "flex";
  }
}

function hideFullPageLoading() {
  console.log("✅ 전체 페이지 로딩 완료");
  const overlay = document.getElementById("fullPageLoadingOverlay");
  if (overlay) {
    overlay.style.display = "none";
  }
}

// 전역으로 함수 노출
window.showFullPageLoading = showFullPageLoading;
window.hideFullPageLoading = hideFullPageLoading;

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
    const background = $overlay.css('background');
    const backgroundColor = $overlay.css('background-color');
    
    console.log(`  ${id}: display=${display}, visibility=${visibility}, opacity=${opacity}`);
    console.log(`    background: ${background}, background-color: ${backgroundColor}`);
    console.log(`    style attribute: ${style}`);
    
    // 스피너와 텍스트 상태도 확인
    const $spinner = $overlay.find('.spinner');
    const $text = $overlay.find('.loading-text');
    if ($spinner.length > 0) {
      console.log(`    spinner: display=${$spinner.css('display')}, visibility=${$spinner.css('visibility')}`);
    }
    if ($text.length > 0) {
      console.log(`    text: display=${$text.css('display')}, visibility=${$text.css('visibility')}`);
    }
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

// 로딩 스피너 테스트 함수
function testLoadingSpinner() {
  console.log("🧪 로딩 스피너 테스트 시작");
  
  // 모든 로딩 오버레이를 강제로 표시
  $(".loading-overlay").each(function() {
    const $overlay = $(this);
    const id = $overlay.attr('id') || 'unknown';
    
    console.log(`🧪 테스트: ${id} 로딩 스피너 표시`);
    
    $overlay.css({
      'display': 'flex !important',
      'visibility': 'visible !important',
      'opacity': '1 !important',
      'pointer-events': 'auto !important',
      'background': 'transparent !important',
      'background-color': 'transparent !important',
      'backdrop-filter': 'none !important'
    });
    
    // 스피너와 텍스트도 강제 표시
    $overlay.find('.spinner, .loading-text').css({
      'display': 'block !important',
      'visibility': 'visible !important',
      'opacity': '1 !important'
    });
  });
  
  // 3초 후 자동으로 숨김
  setTimeout(() => {
    console.log("🧪 테스트 완료 - 로딩 스피너 숨김");
    forceHideAllLoading();
  }, 3000);
}

// 페이지 로드 시 자동으로 모든 로딩 오버레이 제거 (백업용)
$(document).ready(function() {
  // 60초 후 강제 제거 (최후의 수단)
  setTimeout(forceHideAllLoading, 60000);
  
  // 햄버거 메뉴 토글
  $('#hamburgerIcon').on('click', function() {
    const $dropdown = $('#hamburgerDropdown');
    if ($dropdown.is(':visible')) {
      $dropdown.hide();
    } else {
      $dropdown.css('display', 'flex').show();
    }
  });
  
  // 햄버거 메뉴 외부 클릭 시 닫기
  $(document).on('click', function(e) {
    if (!$(e.target).closest('.hamburger-menu-wrapper').length) {
      $('#hamburgerDropdown').hide();
    }
  });
  
  // 햄버거 메뉴 링크 클릭 시 닫기
  $('.hamburger-dropdown a').on('click', function() {
    $('#hamburgerDropdown').hide();
  });
  
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
    
    // 로딩 스피너 테스트를 위한 키보드 단축키 (Ctrl+Shift+T)
    $(document).keydown(function(e) {
      if (e.ctrlKey && e.shiftKey && e.keyCode === 84) { // Ctrl+Shift+T
        console.log("🧪 Ctrl+Shift+T 감지 - 로딩 스피너 테스트");
        testLoadingSpinner();
      }
    });
  }
});

function getRequestData(page = 1, extra = {}) {
  const companyName = $("#accountFilter").val() || "all";
  const period = $("#periodFilter").val();
  
  // 기간에 따라 날짜 계산
  let startDate = "";
  let endDate = "";
  
  if (period && period !== "manual") {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, "0");
    const dd = String(today.getDate()).padStart(2, "0");
    
    if (period === "today") {
      startDate = `${yyyy}-${mm}-${dd}`;
      endDate = startDate;
    } else if (period === "yesterday") {
      const y = new Date(today);
      y.setDate(y.getDate() - 1);
      startDate = y.toISOString().slice(0, 10);
      endDate = startDate;
    } else if (period === "last7days") {
      const s = new Date(today);
      s.setDate(s.getDate() - 7);
      startDate = s.toISOString().slice(0, 10);
      endDate = `${yyyy}-${mm}-${dd}`;
    } else if (period === "last_month") {
      const s = new Date(today);
      s.setMonth(s.getMonth() - 1);
      s.setDate(1);
      const e = new Date(s.getFullYear(), s.getMonth() + 1, 0);
      startDate = s.toISOString().slice(0, 10);
      endDate = e.toISOString().slice(0, 10);
    }
  } else {
    // 수동 날짜 선택인 경우 DOM에서 가져오기
    startDate = $("#startDate").val()?.trim() || "";
    endDate = $("#endDate").val()?.trim() || "";
  }

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
