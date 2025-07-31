/**
 * 페이지네이션을 업데이트하는 공통 함수
 */
function updatePagination(currentPage, totalPages, containerSelector = ".pagination") {
    let paginationContainer = $(containerSelector);
    paginationContainer.empty();  // ✅ 기존 페이지네이션 제거 후 업데이트

    let prevButton = `<button class="prev ${currentPage === 1 ? "disabled" : ""}" data-page="${currentPage - 1}">이전</button>`;
    let nextButton = `<button class="next ${currentPage === totalPages ? "disabled" : ""}" data-page="${currentPage + 1}">다음</button>`;

    paginationContainer.append(prevButton);
    paginationContainer.append(`<span id="pageInfo">${currentPage} / ${totalPages}</span>`);
    paginationContainer.append(nextButton);
}
