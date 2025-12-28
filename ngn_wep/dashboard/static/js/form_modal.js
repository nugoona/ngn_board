// Form Modal JavaScript

/**
 * 모달 열기
 */
function openFormModal() {
  const modal = document.getElementById('formModal');
  if (modal) {
    modal.classList.remove('hidden');
    // 모달이 열릴 때 스크롤 방지
    document.body.style.overflow = 'hidden';
  }
}

/**
 * 모달 닫기
 */
function closeFormModal() {
  const modal = document.getElementById('formModal');
  if (modal) {
    modal.classList.add('hidden');
    // 모달이 닫힐 때 스크롤 복원
    document.body.style.overflow = '';
    // 폼 리셋
    const form = document.getElementById('formModalForm');
    if (form) {
      form.reset();
    }
  }
}

/**
 * 모달 외부 클릭 시 닫기
 */
function handleModalBackdropClick(event) {
  const modal = document.getElementById('formModal');
  if (event.target === modal) {
    closeFormModal();
  }
}

/**
 * 폼 제출 처리
 */
function handleFormSubmit(event) {
  event.preventDefault();
  
  // 폼 데이터 수집
  const formData = {
    name: document.getElementById('formName').value.trim(),
    description: document.getElementById('formDescription').value.trim(),
    type: document.getElementById('formType').value,
    status: document.getElementById('formStatus').value
  };
  
  // 유효성 검사
  if (!formData.name || !formData.description || !formData.type || !formData.status) {
    alert('모든 필드를 입력해주세요.');
    return;
  }
  
  // 여기서 폼 데이터를 처리할 수 있습니다
  // 예: API 호출, 콘솔 출력 등
  console.log('Form submitted:', formData);
  
  // 성공 메시지 (실제로는 API 호출 후 처리)
  alert(`제출 완료!\n\nName: ${formData.name}\nDescription: ${formData.description}\nType: ${formData.type}\nStatus: ${formData.status}`);
  
  // 모달 닫기
  closeFormModal();
}

// DOMContentLoaded 이벤트 리스너
document.addEventListener('DOMContentLoaded', function() {
  // 모달 열기 버튼
  const openBtn = document.getElementById('openFormModalBtn');
  if (openBtn) {
    openBtn.addEventListener('click', function(e) {
      e.preventDefault();
      openFormModal();
      // 햄버거 메뉴 닫기
      const hamburgerDropdown = document.getElementById('hamburgerDropdown');
      if (hamburgerDropdown) {
        hamburgerDropdown.style.display = 'none';
      }
    });
  }
  
  // 모달 닫기 버튼
  const closeBtn = document.getElementById('closeFormModalBtn');
  if (closeBtn) {
    closeBtn.addEventListener('click', closeFormModal);
  }
  
  // 취소 버튼
  const cancelBtn = document.getElementById('cancelFormBtn');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', closeFormModal);
  }
  
  // 모달 배경 클릭 시 닫기
  const modal = document.getElementById('formModal');
  if (modal) {
    modal.addEventListener('click', handleModalBackdropClick);
  }
  
  // 폼 제출
  const form = document.getElementById('formModalForm');
  if (form) {
    form.addEventListener('submit', handleFormSubmit);
  }
  
  // ESC 키로 모달 닫기
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      const modal = document.getElementById('formModal');
      if (modal && !modal.classList.contains('hidden')) {
        closeFormModal();
      }
    }
  });
});

