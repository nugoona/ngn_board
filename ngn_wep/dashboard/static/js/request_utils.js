// File: static/js/request_utils.js

// ✅ 요청 식별자 전역 레지스트리
const requestRegistry = {};

// ✅ 최신 요청만 허용하는 AJAX 래퍼
export function latestAjaxRequest(key, ajaxOptions, onSuccess) {
    if (!requestRegistry[key]) requestRegistry[key] = { id: 0 };
    const requestId = ++requestRegistry[key].id;

    const originalSuccess = ajaxOptions.success;
    ajaxOptions.success = function (res, status, xhr) {
        if (requestId !== requestRegistry[key].id) {
            console.warn(`[SKIP] ${key} 오래된 응답 무시됨`);
            return;
        }
        if (onSuccess) onSuccess(res, status, xhr);
        if (originalSuccess) originalSuccess(res, status, xhr);
    };

    const originalError = ajaxOptions.error;
    ajaxOptions.error = function (xhr, status, error) {
        if (requestId === requestRegistry[key].id && originalError) {
            originalError(xhr, status, error);
        }
    };

    $.ajax(ajaxOptions);
}

// ✅ 페이지, 필터 입력값 기반으로 요청 데이터 생성
export function getRequestData(page, extra = {}) {
    let companyName = $("#accountFilter").val() || "all";
    let period = $("#periodFilter").val() || "today";
    let startDate = $("#startDate").val()?.trim() || new Date().toISOString().split("T")[0];
    let endDate = $("#endDate").val()?.trim() || new Date().toISOString().split("T")[0];

    const base = {
        company_name: companyName,
        period: period,
        start_date: startDate,
        end_date: endDate,
        page: page,
        limit: 1000,
    };

    return { ...base, ...extra };
}
