// File: static/js/meta_ads.js
import { getRequestData } from "./request_utils.js";

$(document).ready(function () {
    if (window.location.pathname === "/ads") {
        console.log("[DEBUG] Meta Ads 데이터 JS 로드됨");

        // ✅ '기간합 / 일자별' 선택 UI 삽입
        $("#metaAdsTable").before(`
            <div class="date-type-filter" style="margin-bottom: 10px; font-size: 18px;">
                <label style="margin-right: 5px; padding: 8px;">
                    <input type="radio" name="metaDateType" value="summary" checked> <b>기간합</b>
                </label>
                <label style="padding: 8px;">
                    <input type="radio" name="metaDateType" value="daily"> <b>일자별</b>
                </label>
                <select id="metaDateSort" style="display: none; margin-left: 10px; padding: 5px; font-size: 16px;">
                    <option value="desc" selected>날짜 내림차순</option>
                    <option value="asc">날짜 오름차순</option>
                </select>
            </div>
        `);

        // ✅ 이벤트 연결
        $("input[name='metaDateType']").change(function () {
            $("#metaDateSort").toggle($(this).val() === "daily");
            fetchMetaAdsData(1);
        });

        $("#metaDateSort").change(function () {
            if ($("input[name='metaDateType']:checked").val() === "daily") {
                fetchMetaAdsData(1);
            }
        });

        $("#accountFilter, #periodFilter, #startDate, #endDate").change(function () {
            fetchMetaAdsData(1);
        });

        $("#applyDateFilter").click(function () {
            fetchMetaAdsData(1);
        });

        // ✅ 초기 로딩
        fetchMetaAdsData(1);
    }
});

// ✅ Meta Ads 데이터 요청
function fetchMetaAdsData(page) {
    if (window.location.pathname !== "/ads") return;

    console.log(`[DEBUG] Meta Ads 데이터 요청 (페이지: ${page})`);

    const period = $("#periodFilter").val();
    const endDate = $("#endDate").val()?.trim();
    if (period === "manual" && (!endDate || endDate === "")) {
        console.log("[DEBUG] (meta_ads) 직접 선택 + 종료일 없음 → 실행 중단");
        return;
    }

    let requestData = getRequestData(page);
    requestData.date_type = $("input[name='metaDateType']:checked").val() || "summary";

    if (requestData.date_type === "daily") {
        requestData.date_sort = $("#metaDateSort").val();
    }

    showLoading("#loadingOverlayMetaAds");

    $.ajax({
        url: "/dashboard/get_data",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify(requestData),
        success: function (response) {
            console.log("[DEBUG] Meta Ads 서버 응답 데이터:", response);

            if (!response || response.status !== "success" || !response.meta_ads) {
                console.error("[ERROR] Meta Ads 데이터 불러오기 오류:", response.error || "알 수 없는 오류");
                return;
            }

            updateMetaAdsTable(response.meta_ads);
            updatePagination("meta_ads", page, response.meta_ads_total_count);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.error(`[ERROR] Meta Ads 서버 오류: ${textStatus}, ${errorThrown}`, jqXHR);
        },
        complete: function () {
            hideLoading("#loadingOverlayMetaAds");
        }
    });
}

// ✅ Meta Ads 테이블 렌더링 (계정 단위 성과용)
function updateMetaAdsTable(data) {
    const tableBody = $("#metaAdsBody");
    tableBody.empty();

    if (!data || !Array.isArray(data) || data.length === 0) {
        tableBody.append("<tr><td colspan='13'>데이터가 없습니다.</td></tr>");
        return;
    }

    data.forEach(row => {
        const newRow = `
            <tr>
                <td>${cleanData(row.company_name)}</td>
                <td>${cleanData(row.report_date)}</td>
                <td>${cleanData(row.total_spend)}</td>
                <td>${cleanData(row.total_clicks)}</td>
                <td>${cleanData(row.total_purchases)}</td>
                <td>${cleanData(row.roas)}%</td>
                <td>${cleanData(row.ctr)}%</td>
                <td>${cleanData(row.cpm)}</td>
                <td>${cleanData(row.conversion_rate)}%</td>
                <td>${cleanData(row.average_order_value)}</td>
                <td>${cleanData(row.cost_per_purchase)}</td>
                <td>${cleanData(row.cpc)}</td>
            </tr>
        `;
        tableBody.append(newRow);
    });

    console.log("[DEBUG] Meta Ads 테이블 렌더링 완료");
}
