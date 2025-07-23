function updatePagination(table, currentPage, totalItems) {
    let limit = 15; // ✅ 한 페이지당 15개 제한
    let totalPages = totalItems > 0 ? Math.ceil(totalItems / limit) : 1;

    console.log(`[DEBUG] ${table} 페이지네이션 업데이트`);
    console.log(`[DEBUG] 현재 페이지: ${currentPage}`);
    console.log(`[DEBUG] 전체 페이지 수: ${totalPages}`);
    console.log(`[DEBUG] 전체 데이터 개수: ${totalItems}`);

    let paginationContainer = $(`#pagination_${table}`);

    if (paginationContainer.length === 0) {
        console.warn(`[WARN] 페이지네이션 컨테이너를 찾을 수 없음: #pagination_${table}`);
        return;
    }

    paginationContainer.empty(); // ✅ 기존 버튼 제거 후 다시 추가

    let prevDisabled = currentPage <= 1 ? "disabled" : "";
    let nextDisabled = currentPage >= totalPages ? "disabled" : "";

    paginationContainer.append(`
        <button class="pagination-btn prev-btn" data-table="${table}" data-page="${currentPage - 1}" ${prevDisabled}>이전</button>
        <span class="currentPage">${currentPage} / ${totalPages}</span>
        <button class="pagination-btn next-btn" data-table="${table}" data-page="${currentPage + 1}" ${nextDisabled}>다음</button>
    `);

    // ✅ 이벤트 핸들러 제거 후 다시 추가 (중복 방지)
    paginationContainer.find(".pagination-btn").off("click").on("click", function () {
        let newPage = parseInt($(this).data("page"));
        let table = $(this).data("table");

        if (!$(this).attr("disabled") && newPage !== currentPage) {
            console.log(`[DEBUG] ${table} 페이지 이동: ${newPage}`);

            // ✅ 현재 페이지(`/` or `/ads`)에 맞는 데이터만 요청
            if (window.location.pathname === "/ads" && table === "meta_ads") {
                fetchMetaAdsData(newPage);
            } else if (window.location.pathname === "/" && table === "cafe24_sales") {
                fetchCafe24SalesData(newPage);
            } else if (window.location.pathname === "/" && table === "cafe24_product_sales") {
                fetchCafe24ProductSalesData(newPage);
            } else {
                console.log(`[DEBUG] 현재 페이지(${window.location.pathname})에서 ${table} 데이터 요청 안함`);
            }
        } else {
            console.log(`[DEBUG] ${table} 버튼 클릭 불가 (비활성화 상태 또는 현재 페이지)`);
        }
    });

    // ✅ 기존 페이지와 변경된 페이지가 같으면 fetch 실행 안 함
    if (window.prevTotalPages && window.prevTotalPages[table] === totalPages) {
        console.log(`[DEBUG] ${table} 페이지네이션 동일 - fetch 실행 안 함`);
        return;
    }

    // ✅ 페이지 수 저장 (fetch 중복 실행 방지)
    if (!window.prevTotalPages) {
        window.prevTotalPages = {};
    }
    window.prevTotalPages[table] = totalPages;
}
