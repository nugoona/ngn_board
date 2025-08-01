// File: common_ui.js
export function showInlinePopup(message = "알 수 없는 오류입니다") {
  // 기존 팝업이 있으면 제거
  const existing = document.querySelector(".custom-popup");
  if (existing) existing.remove();

  // 팝업 생성
  const popup = document.createElement("div");
  popup.className = "custom-popup";
  popup.innerText = message;

  // body에 추가
  document.body.appendChild(popup);

  // 클릭 시 즉시 제거
  popup.addEventListener("click", () => popup.remove());

  // 3초 후 페이드아웃 및 제거
  setTimeout(() => {
    popup.style.opacity = "0";
    setTimeout(() => popup.remove(), 500);
  }, 3000);
}
