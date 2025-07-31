// 모바일 감지 보조 스크립트
(function() {
  var screenWidth = window.screen.width;
  var viewportWidth = window.innerWidth;
  
  if (screenWidth <= 768 || viewportWidth <= 768) {
    var currentUrl = new URL(window.location);
    currentUrl.searchParams.set('screen_width', screenWidth);
    currentUrl.searchParams.set('viewport_width', viewportWidth);
    
    if (currentUrl.toString() !== window.location.href) {
      console.log('[MOBILE DETECTION] Mobile screen detected, redirecting...');
      window.location.href = currentUrl.toString();
    }
  }
})(); 