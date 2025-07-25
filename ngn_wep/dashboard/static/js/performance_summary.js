$(document).ready(function () {
    console.log("[DEBUG] performance_summary.js 로드됨");

    $("#accountFilter, #periodFilter, #startDate, #endDate").change(debounce(function () {
        const period = $("#periodFilter").val();
        const endDate = $("#endDate").val()?.trim();

        if (period === "manual" && (!endDate || endDate === "")) {
            console.log("[DEBUG] 필터 변경 감지 - 직접 선택인데 종료일 없음 → fetch 중단");
            return;
        }

        console.log("[DEBUG] 필터 변경 감지 → performance_summary 실행");
        fetchPerformanceSummaryData();
    }, 500));

    $("#applyFiltersBtn").click(function () {
        const period = $("#periodFilter").val();
        const endDate = $("#endDate").val()?.trim();

        if (period === "manual" && (!endDate || endDate === "")) {
            console.log("[DEBUG] 적용 버튼 클릭 - 직접 선택인데 종료일 없음 → fetch 중단");
            return;
        }

        console.log("[DEBUG] 적용 버튼 클릭 → performance_summary 실행");
        fetchPerformanceSummaryData();
    });
});

function debounce(func, delay) {
    let timeout;
    return function () {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(function () {
            func.apply(context, args);
        }, delay);
    };
}

async function fetchPerformanceSummaryData() {
    console.log("[DEBUG] fetchPerformanceSummaryData() 시작");

    let companyName = $("#accountFilter").val() || "all";
    let period = $("#periodFilter").val() || "today";
    let startDate = $("#startDate").val()?.trim();
    let endDate = $("#endDate").val()?.trim();

    if (period === "manual" && (!endDate || endDate === "")) {
        console.log("[DEBUG] (performance_summary) 직접 선택인데 종료일 없음 - 요청 및 로딩 중단");
        return;
    }

    // 🔥 사이트 성과 요약만 2중 로딩 스피너 (performance_summary.js에서 추가)
    toggleLoading(true);

    const today = new Date().toISOString().split("T")[0];
    if (!startDate) startDate = today;
    if (!endDate) endDate = today;

    const requestData = {
        service: "performance_summary",
        company_name: companyName,
        period: period,
        start_date: startDate,
        end_date: endDate
    };

    try {
        const response = await fetch("/dashboard/get_data", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(requestData)
        });

        const data = await response.json();
        console.log("[DEBUG] 서버 응답:", data);

        if (!data || data.status !== "success" || !data.performance_summary) {
            console.error("[ERROR] 성과 요약 데이터 불러오기 실패:", data.error || "알 수 없는 오류");
            updatePerformanceSummaryCards([]);
            updateUpdatedAtText(null);
            return;
        }

        updatePerformanceSummaryCards(data.performance_summary);

        if (data.latest_update) {
            updateUpdatedAtText(data.latest_update);
        } else {
            updateUpdatedAtText(null);
        }
    } catch (error) {
        console.error("[ERROR] 데이터 요청 중 오류 발생:", error);
        updateUpdatedAtText(null);
    } finally {
        // 🔥 사이트 성과 요약만 2중 로딩 스피너 (performance_summary.js에서 추가)
        toggleLoading(false);
        // 🔥 dashboard.js의 로딩 스피너도 함께 숨김 (연계성 유지)
        hideLoading("#loadingOverlayPerformanceSummary");
    }
}

function toggleLoading(isLoading) {
    if (isLoading) {
        showLoading("#loadingOverlayPerformanceSummary");
        // 🔥 모든 로딩 오버레이가 투명 배경이므로 JavaScript 설정 불필요
        $("#performanceSummaryWrapper").addClass("loading");
    } else {
        hideLoading("#loadingOverlayPerformanceSummary");
        $("#performanceSummaryWrapper").removeClass("loading");
    }
}

function updatePerformanceSummaryCards(data) {
    console.log("[DEBUG] updatePerformanceSummaryCards() 실행");

    if (!data || !data.length) {
        console.warn("[WARN] performance_summary 데이터 없음. '-'로 표시합니다.");
        const fields = [
            "site_revenue", "total_visitors", "product_views", "views_per_visit",
            "ad_spend_ratio", "ad_media", "ad_spend", "roas_percentage",
            "avg_cpc", "click_through_rate", "conversion_rate",
            "avg_order_value", "total_purchases", "total_purchase_value"
        ];
        fields.forEach(field => setCardValue(field, "-"));
        return;
    }

    const row = data[0];
    console.log("[DEBUG] 최종 반영할 데이터(row):", row);

    setCardValue("site_revenue", row.site_revenue);
    setCardValue("total_visitors", row.total_visitors);
    setCardValue("product_views", row.product_views);
    setCardValue("views_per_visit", row.views_per_visit, 2);
    setCardValue("ad_spend_ratio", row.ad_spend_ratio, 2, "%");
    setCardValue("ad_media", row.ad_media);
    setCardValue("ad_spend", row.ad_spend);
    setCardValue("roas_percentage", row.roas_percentage, 2, "%");
    setCardValue("avg_cpc", row.avg_cpc, 0);
    setCardValue("click_through_rate", row.click_through_rate, 2, "%");
    setCardValue("conversion_rate", row.conversion_rate, 2, "%");
    setCardValue("avg_order_value", row.avg_order_value);
    setCardValue("total_purchases", row.total_purchases);
    setCardValue("total_purchase_value", row.total_purchase_value);

    console.log("[DEBUG] performance_summary 카드 렌더링 완료");
}

function setCardValue(cardId, rawValue, decimal = 0, suffix = "") {
    const el = $("#" + cardId);
    if (!el.length) {
        console.warn(`[WARN] setCardValue() - 요소 #${cardId} 없음`);
        return;
    }

    // null 또는 undefined → "-"
    if (rawValue === null || rawValue === undefined) {
        el.text("-");
        return;
    }

    // 숫자처럼 보이는 문자열도 처리
    const numericValue = parseFloat(String(rawValue).replace(/[^\d.-]/g, ""));
    if (!isNaN(numericValue)) {
        let val = numericValue.toFixed(decimal);
        val = Number(val).toLocaleString(undefined, {
            minimumFractionDigits: decimal,
            maximumFractionDigits: decimal
        });
        el.text(val + suffix);
    } else {
        // 숫자가 아닌 값은 그대로 출력
        el.text(rawValue + suffix);
    }
}


function updateUpdatedAtText(updatedAtStr) {
  const el = $("#updatedAtText");
  if (!el.length) {
    console.warn("[WARN] #updatedAtText 요소가 존재하지 않음");
    return;
  }

  if (!updatedAtStr) {
    el.text("최종 업데이트: 정보 없음");
    return;
  }

  let kst = null;

  // ✅ 형식이 "2025-05-11-19-11"일 경우 → 수동 파싱
  const parts = updatedAtStr.split("-");
  if (parts.length === 5) {
    const [year, month, day, hour, minute] = parts.map(Number);
    kst = new Date(year, month - 1, day, hour, minute);
  } else {
    // ✅ ISO 형식인 경우
    const utc = new Date(updatedAtStr);
    if (!isNaN(utc.getTime())) {
      kst = new Date(utc.getTime() - 9 * 60 * 60 * 1000);  // UTC → KST
    }
  }

  if (!kst || isNaN(kst.getTime())) {
    el.text("최종 업데이트: " + updatedAtStr);
  } else {
    const formatted = `${kst.getFullYear()}년 ${kst.getMonth() + 1}월 ${kst.getDate()}일 ${kst.getHours()}시 ${kst.getMinutes().toString().padStart(2, '0')}분`;
    el.text(`최종 업데이트: ${formatted}`);
  }
}
