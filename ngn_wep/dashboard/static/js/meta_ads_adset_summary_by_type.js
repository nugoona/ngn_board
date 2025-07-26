// File: static/js/meta_ads_adset_summary_by_type.js

import { resolveDateRange } from "./meta_ads_utils.js";
// showLoading/hideLoading 함수는 common.js에서 정의됨
import { metaAdsState } from "./meta_ads_state.js";

const $ = window.$;
let typePieChartInstance = null;

export function fetchMetaAdsAdsetSummaryByType({ period, start_date, end_date, account_id } = {}) {
  console.log("[DEBUG] fetchMetaAdsAdsetSummaryByType 호출됨");

  const requestData = getRequestData(1, {
    data_type: "meta_ads_adset_summary_by_type",
    period: period,
    start_date: start_date,
    end_date: end_date,
    account_id: account_id
  });

  console.log("[DEBUG] 캠페인 목표별 성과 요약 요청:", requestData);
  
  // 로딩 오버레이가 있는 경우에만 표시
  const loadingOverlay = $("#loadingOverlayTypeSummary");
  if (loadingOverlay.length > 0) {
    showLoading("#loadingOverlayTypeSummary");
  }

  latestAjaxRequest("meta_ads_adset_summary_by_type", {
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(requestData),
    error: function (xhr, status, error) {
      if (loadingOverlay.length > 0) {
        hideLoading("#loadingOverlayTypeSummary");
      }
      console.error("[ERROR] 캠페인 목표별 성과 요약 오류:", status, error);
    }
  }, function (res) {
    if (loadingOverlay.length > 0) {
      hideLoading("#loadingOverlayTypeSummary");
    }

    if (res.status === "success") {
      const data = res.meta_ads_adset_summary_by_type || [];
      console.log("[DEBUG] 캠페인 목표별 성과 요약 데이터:", data);
      renderMetaAdsAdsetSummaryTable(data);
      renderMetaAdsAdsetSummaryChart(data);
    } else {
      console.warn("[WARN] 캠페인 목표별 성과 요약 응답 없음", res);
    }
  });
}

function renderMetaAdsAdsetSummaryTable(data) {
  console.log("[DEBUG] renderMetaAdsAdsetSummaryTable 호출됨");
  
  const tbody = $("#metaAdsAdsetSummaryTable tbody");
  if (tbody.length === 0) {
    console.warn("[WARN] metaAdsAdsetSummaryTable tbody 요소를 찾을 수 없습니다.");
    return;
  }
  
  tbody.empty();

  if (!data || data.length === 0) {
    tbody.append("<tr><td colspan='6'>데이터가 없습니다.</td></tr>");
    return;
  }

  let totalSpend = 0;
  let totalImpressions = 0;
  let totalClicks = 0;
  let totalPurchases = 0;
  let totalPurchaseValue = 0;

  data.forEach(row => {
    const spend = row.total_spend || 0;
    const impressions = row.total_impressions || 0;
    const clicks = row.total_clicks || 0;
    const purchases = row.total_purchases || 0;
    const purchaseValue = row.total_purchase_value || 0;
    
    const cpm = impressions > 0 ? (spend / impressions) * 1000 : 0;
    const cpc = clicks > 0 ? spend / clicks : 0;
    const roas = spend > 0 ? (purchaseValue / spend) * 100 : 0;

    totalSpend += spend;
    totalImpressions += impressions;
    totalClicks += clicks;
    totalPurchases += purchases;
    totalPurchaseValue += purchaseValue;

    const tr = $("<tr></tr>");
    tr.append(`<td>${row.type || "-"}</td>`);
    tr.append(`<td>${spend.toLocaleString()}</td>`);
    tr.append(`<td>${cpm.toFixed(0)}</td>`);
    tr.append(`<td>${cpc.toFixed(0)}</td>`);
    tr.append(`<td>${purchases.toLocaleString()}</td>`);
    tr.append(`<td>${roas.toFixed(1)}%</td>`);
    
    tbody.append(tr);
  });

  // 합계 행 추가
  const totalCpm = totalImpressions > 0 ? (totalSpend / totalImpressions) * 1000 : 0;
  const totalCpc = totalClicks > 0 ? totalSpend / totalClicks : 0;
  const totalRoas = totalSpend > 0 ? (totalPurchaseValue / totalSpend) * 100 : 0;

  const totalTr = $("<tr style='font-weight: bold; background-color: #f3f4f6;'></tr>");
  totalTr.append(`<td>총합</td>`);
  totalTr.append(`<td>${totalSpend.toLocaleString()}</td>`);
  totalTr.append(`<td>${totalCpm.toFixed(0)}</td>`);
  totalTr.append(`<td>${totalCpc.toFixed(0)}</td>`);
  totalTr.append(`<td>${totalPurchases.toLocaleString()}</td>`);
  totalTr.append(`<td>${totalRoas.toFixed(1)}%</td>`);
  
  tbody.append(totalTr);
}

function renderMetaAdsAdsetSummaryChart(data, totalSpendSum) {
  console.log("[DEBUG] renderMetaAdsAdsetSummaryChart 호출됨");
  
  const chartContainer = document.getElementById("metaAdsAdsetSummaryChart");
  const legendContainer = document.getElementById("campaignLegendItems");
  
  console.log("[DEBUG] 차트 컨테이너:", chartContainer);

  if (!chartContainer) {
    console.error("[ERROR] metaAdsAdsetSummaryChart 컨테이너를 찾을 수 없습니다!");
    return;
  }

  // 기존 차트 인스턴스 제거
  if (typePieChartInstance) {
    typePieChartInstance.destroy();
  }

  // 총 지출 계산
  totalSpendSum = totalSpendSum || data.reduce((sum, row) => sum + (row.total_spend || 0), 0);

  // 데이터가 없거나 총 지출이 0인 경우 빈 차트 표시
  if (!data || data.length === 0 || totalSpendSum === 0) {
    console.log("[DEBUG] 빈 차트 렌더링");
    
    // 빈 범례 표시
    if (legendContainer) {
      legendContainer.innerHTML = '<div class="legend-item"><div class="legend-text">데이터가 없습니다</div></div>';
    }
    
      // 🔥 공통 함수 사용
  if (typeof window.createEmptyPieChart !== 'function') {
    console.warn("[WARN] createEmptyPieChart 함수가 아직 로드되지 않았습니다. 100ms 후 재시도합니다.");
    setTimeout(() => renderMetaAdsAdsetSummaryChart(data, totalSpendSum), 100);
    return;
  }
  typePieChartInstance = window.createEmptyPieChart("metaAdsAdsetSummaryChart");
    console.log("[DEBUG] 빈 차트 렌더링 완료");
    return;
  }

  console.log("[DEBUG] 실제 데이터로 차트 렌더링");
  
  const labels = data.map(row => row.type || "-");
  const values = data.map(row => totalSpendSum ? (row.total_spend / totalSpendSum * 100) : 0);
  const actualSpend = data.map(row => row.total_spend || 0);
  const colors = ['#4e73df', '#f6c23e', '#36b9cc', '#e74a3b', '#6f42c1'];

  console.log("[DEBUG] 차트 데이터:", { labels, values, actualSpend });

  // 커스텀 범례 생성
  if (legendContainer) {
    legendContainer.innerHTML = '';
    labels.forEach((label, index) => {
      const legendItem = document.createElement('div');
      legendItem.className = 'legend-item';
      legendItem.innerHTML = `
        <div class="legend-marker" style="background-color: ${colors[index]}"></div>
        <div class="legend-text">${label}</div>
        <div class="legend-percentage">${values[index].toFixed(1)}%</div>
      `;
      legendContainer.appendChild(legendItem);
    });
  }

  // 🔥 공통 함수 사용
  if (typeof window.createPieChart !== 'function') {
    console.warn("[WARN] createPieChart 함수가 아직 로드되지 않았습니다. 100ms 후 재시도합니다.");
    setTimeout(() => renderMetaAdsAdsetSummaryChart(data, totalSpendSum), 100);
    return;
  }
  typePieChartInstance = window.createPieChart("metaAdsAdsetSummaryChart", {
    series: values,
    labels: labels,
    actualSales: actualSpend
  }, {
    colors: colors
  });

  console.log("[DEBUG] 캠페인 목표별 지출 비중 차트 렌더링 완료");
}
