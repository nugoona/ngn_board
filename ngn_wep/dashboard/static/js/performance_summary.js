$(document).ready(function () {
    console.log("[DEBUG] performance_summary.js 로드됨");
    console.log("[DEBUG] fetchPerformanceSummaryData 함수 존재:", typeof fetchPerformanceSummaryData);
    
    // 🔥 페이지 로드 시 즉시 실행
    console.log("[DEBUG] 페이지 로드 시 즉시 실행");
    fetchPerformanceSummaryData();

    $("#accountFilter, #periodFilter, #startDate, #endDate").change(debounce(function () {
        const period = $("#periodFilter").val();
        const endDate = $("#endDate").val()?.trim();

        if (period === "manual" && (!endDate || endDate === "")) {
            console.log("[DEBUG] 필터 변경 감지 - 직접 선택인데 종료일 없음 → fetch 중단");
            return;
        }

        console.log("[DEBUG] 필터 변경 감지 → performance_summary 실행");
        fetchPerformanceSummaryData();
    }, 300)); // 500ms → 300ms로 단축

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
    try {
        const startTime = performance.now();
        
        // 🔥 로딩 스피너 표시
        showLoading("#loadingOverlayPerformanceSummary");
        
        // 🔥 기존 필터 값 사용
        let companyName = $("#accountFilter").val() || "all";
        let period = $("#periodFilter").val() || "today";
        let startDate = $("#startDate").val()?.trim();
        let endDate = $("#endDate").val()?.trim();

        if (period === "manual" && (!endDate || endDate === "")) {
            console.log("[DEBUG] 직접 선택인데 종료일 없음 - 요청 중단");
            hideLoading("#loadingOverlayPerformanceSummary");
            return [];
        }

        const today = new Date().toISOString().split("T")[0];
        if (!startDate) startDate = today;
        if (!endDate) endDate = today;
        
        const response = await fetch('/dashboard/get_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                data_type: 'performance_summary',
                company_name: companyName,
                period: period,
                start_date: startDate,
                end_date: endDate,
                limit: 100,
                page: 1
            })
        });

        const endTime = performance.now();
        const clientTime = endTime - startTime;
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log("[DEBUG] 서버 응답:", data);
        console.log("[DEBUG] data.performance_summary 타입:", typeof data.performance_summary);
        console.log("[DEBUG] data.performance_summary 길이:", data.performance_summary ? data.performance_summary.length : "undefined");
        
        // 성능 정보 출력
        if (data.performance) {
            console.log('🚀 성능 측정 결과:');
            console.log(`- 클라이언트 측 시간: ${clientTime.toFixed(2)}ms`);
            console.log(`- 서버 측 총 시간: ${data.performance.total_execution_time}s`);
            console.log(`- 개별 함수 시간:`, data.performance.individual_times);
            console.log(`- 최적화 버전: ${data.performance.optimization_version}`);
        }
        
        if (!data || data.status !== "success" || !data.performance_summary) {
            console.error("[ERROR] 성과 요약 데이터 불러오기 실패:", data.error || "알 수 없는 오류");
            updatePerformanceSummaryCards([]);
            return [];
        }

            console.log("[DEBUG] performance_summary 데이터:", data.performance_summary);
    
    // 🔥 강제로 ad_media 요소 확인 및 업데이트
    const adMediaElement = document.getElementById("ad_media");
    console.log("[DEBUG] ad_media 요소 존재:", !!adMediaElement);
    if (adMediaElement) {
        console.log("[DEBUG] 현재 ad_media 텍스트:", adMediaElement.textContent);
    }
    
    updatePerformanceSummaryCards(data.performance_summary);
        
        if (data.latest_update) {
            updateUpdatedAtText(data.latest_update);
        } else {
            updateUpdatedAtText(null);
        }
        
        return data.performance_summary || [];
    } catch (error) {
        console.error('Error fetching performance summary data:', error);
        updatePerformanceSummaryCards([]);
        return [];
    } finally {
        // 🔥 로딩 완료
        hideLoading("#loadingOverlayPerformanceSummary");
    }
}

// 🔥 단순화된 로딩 함수들
function showLoading(target) {
    const element = document.querySelector(target);
    if (element) {
        element.style.cssText = `
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            background: rgba(255, 255, 255, 0.95) !important;
            backdrop-filter: blur(4px) !important;
        `;
        console.log(`[DEBUG] 로딩 스피너 강제 표시: ${target}`);
    }
}

function hideLoading(target) {
    const element = document.querySelector(target);
    if (element) {
        element.style.cssText = `
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        `;
        console.log(`[DEBUG] 로딩 스피너 강제 숨김: ${target}`);
    }
}

function updatePerformanceSummaryCards(data) {
    console.log("[DEBUG] updatePerformanceSummaryCards() 실행");
    console.log("[DEBUG] 받은 데이터:", data);

    if (!data || !data.length) {
        console.warn("[WARN] performance_summary 데이터 없음. '-'로 표시합니다.");
        const fields = [
            "site_revenue", "total_visitors", "total_orders", "ad_spend_ratio", 
            "ad_media", "ad_spend", "roas_percentage", "avg_cpc", 
            "total_purchases", "total_purchase_value"
        ];
        fields.forEach(field => setCardValue(field, "-"));
        return;
    }

    const row = data[0];
    console.log("[DEBUG] 최종 반영할 데이터(row):", row);
    console.log("[DEBUG] ad_media 값:", row.ad_media);

    // 🔥 방문당 조회 대신 주문수 사용
    setCardValue("site_revenue", row.site_revenue);
    setCardValue("total_visitors", row.total_visitors);
    setCardValue("total_orders", row.total_orders); // ← 주문수
    setCardValue("ad_spend_ratio", row.ad_spend_ratio, 2, "%");
    
    // 🔥 진행중인 광고 표시 로직 개선
    const adMedia = row.ad_media || "없음";
    console.log("[DEBUG] ad_media 최종 값:", adMedia);
    console.log("[DEBUG] row.ad_media 원본 값:", row.ad_media);
    setCardValue("ad_media", adMedia);
    
    setCardValue("ad_spend", row.ad_spend);
    setCardValue("roas_percentage", row.roas_percentage, 2, "%");
    setCardValue("avg_cpc", row.avg_cpc, 0);
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

    console.log(`[DEBUG] setCardValue - ${cardId}:`, rawValue);
    console.log(`[DEBUG] setCardValue - ${cardId} 타입:`, typeof rawValue);

    // null 또는 undefined → "-"
    if (rawValue === null || rawValue === undefined) {
        console.log(`[DEBUG] setCardValue - ${cardId}: null/undefined 처리`);
        el.text("-");
        return;
    }

    // 🔥 '없음' 상태 특별 처리
    if (rawValue === "없음" || rawValue === "none") {
        console.log(`[DEBUG] setCardValue - ${cardId}: '없음' 처리`);
        el.text("없음");
        return;
    }
    
    // 🔥 'meta' 상태 특별 처리
    if (rawValue === "meta") {
        console.log(`[DEBUG] setCardValue - ${cardId}: 'meta' 처리`);
        el.text("meta");
        return;
    }

    // 숫자처럼 보이는 문자열도 처리
    let numValue = rawValue;
    if (typeof rawValue === "string") {
        numValue = parseFloat(rawValue);
        if (isNaN(numValue)) {
            el.text("-");
            return;
        }
    }

    // 🔥 K 표시 제거하고 실제 숫자 그대로 표시
    let formattedValue;
    if (numValue === 0) {
        formattedValue = "0";
    } else {
        formattedValue = numValue.toFixed(decimal);
    }

    // 천 단위 콤마 추가
    if (numValue >= 1000) {
        const parts = formattedValue.split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        formattedValue = parts.join('.');
    }

    el.text(formattedValue + suffix);
}

function updateUpdatedAtText(updatedAtStr) {
    const updatedAtElement = $("#updatedAtText");
    if (!updatedAtElement.length) {
        console.warn("[WARN] updateUpdatedAtText() - #updatedAtText 요소 없음");
        return;
    }

    if (!updatedAtStr) {
        updatedAtElement.text("최종 업데이트: -");
        return;
    }

    try {
        const updatedAt = new Date(updatedAtStr);
        const now = new Date();
        const diffMs = now - updatedAt;
        const diffMins = Math.floor(diffMs / (1000 * 60));

        let timeText;
        if (diffMins < 1) {
            timeText = "방금 전";
        } else if (diffMins < 60) {
            timeText = `${diffMins}분 전`;
        } else {
            const diffHours = Math.floor(diffMins / 60);
            timeText = `${diffHours}시간 전`;
        }

        updatedAtElement.text(`최종 업데이트: ${timeText}`);
        console.log(`[DEBUG] 업데이트 시간 설정: ${timeText} (${updatedAtStr})`);
    } catch (error) {
        console.error("[ERROR] 업데이트 시간 파싱 오류:", error);
        updatedAtElement.text("최종 업데이트: -");
    }
}
