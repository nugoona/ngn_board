let inactivityTime = function () {
  let timer;
  function logout() {
    console.log("🔒 자동 로그아웃 실행됨");
    window.location.href = "/logout";
  }
  function resetTimer() {
    clearTimeout(timer);
    timer = setTimeout(logout, 30 * 60 * 1000); // 30분
  }

  window.onload = resetTimer;
  document.onmousemove = resetTimer;
  document.onkeypress = resetTimer;
  document.onclick = resetTimer;
  document.onscroll = resetTimer;

  // ✅ ajax 요청이 완료될 때도 타이머 리셋
  if (window.jQuery) {
    $(document).ajaxComplete(function () {
      resetTimer();
    });
  }
};

inactivityTime();
