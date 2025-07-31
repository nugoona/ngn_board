function fetchData(page) {
    console.log(`[DEBUG] 대시보드 데이터 요청 (페이지: ${page})`);

    let requestData = getRequestData(page);
    localStorage.setItem("currentPage", page); // ✅ 현재 페이지 저장

    // ✅ 현재 페이지(`/` or `/ads`)에 맞게 data_type 설정
    if (window.location.pathname === "/ads") {
        requestData.data_type = "meta_ads"; // ✅ 광고 페이지에서는 메타 광고 데이터만 요청
    } else if (window.location.pathname === "/") {
        requestData.data_type = "all"; // ✅ 대시보드에서는 전체 데이터 요청
    }

    // ✅ 모든 로딩 애니메이션 표시
    $(".loading-overlay").show();

    $.ajax({
        url: "/dashboard/get_data",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify(requestData),
        success: function (response) {
            console.log("[DEBUG] 서버 응답 데이터: ", response);

            if (!response || response.status !== "success") {
                console.error(`[ERROR] 데이터 불러오기 오류: `, response.message || "알 수 없는 오류");
                return;
            }

            // ✅ 현재 페이지에 맞는 데이터만 UI 업데이트
            if (window.location.pathname === "/ads") {
                if (response.meta_ads && typeof updateMetaAdsTable === "function") {
                    updateMetaAdsTable(response.meta_ads);
                }
                updatePagination("meta_ads", page, response.meta_ads_total_count);
            } else if (window.location.pathname === "/") {
                // ✅ performance_summary 반영
                if (response.performance_summary && typeof updatePerformanceSummaryCards === "function") {
                    console.log("[DEBUG] performance_summary 데이터 감지됨, UI 업데이트 실행");
                    updatePerformanceSummaryCards(response.performance_summary);
                }

                if (response.cafe24_sales && typeof updateCafe24SalesTable === "function") {
                    updateCafe24SalesTable(response.cafe24_sales);
                }

                if (response.cafe24_product_sales && typeof updateCafe24ProductSalesTable === "function") {
                    updateCafe24ProductSalesTable(response.cafe24_product_sales);
                }

                // ✅ 페이지네이션 업데이트
                updatePagination("cafe24_sales", page, response.cafe24_sales_total_count);
                updatePagination("cafe24_product_sales", page, response.cafe24_product_sales_total_count);
            } else {
                console.warn("[WARN] 현재 페이지에 해당하는 데이터 없음.");
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.error(`[ERROR] 서버 오류: ${textStatus}, ${errorThrown}`, jqXHR);
        },
        complete: function () {
            // ✅ 모든 로딩 애니메이션 숨김
            $(".loading-overlay").hide();
        }
    });
}
