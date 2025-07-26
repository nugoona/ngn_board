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
  
  // ApexCharts가 로드되었는지 확인
  if (typeof ApexCharts === 'undefined') {
    console.warn('ApexCharts not loaded, retrying in 100ms...');
    setTimeout(() => renderMetaAdsAdsetSummaryChart(data, totalSpendSum), 100);
    return;
  }

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
    
    typePieChartInstance = new ApexCharts(chartContainer, {
      series: [100],
      chart: {
        type: 'pie',
        height: 350,
        fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
        animations: {
          enabled: false
        }
      },
      labels: ['데이터 없음'],
      colors: ['#e5e7eb'],
      plotOptions: {
        pie: {
          donut: {
            size: '65%',
            background: 'transparent'
          }
        }
      },
      legend: {
        show: false
      },
      dataLabels: {
        enabled: false
      }
    });
    
    typePieChartInstance.render();
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

  // ApexCharts 옵션 설정 - 직관적인 디자인으로 변경
  const options = {
    series: values,
    chart: {
      type: 'pie',
      height: 350,
      fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
      animations: {
        enabled: false
      }
    },
    labels: labels,
    colors: colors,
    plotOptions: {
      pie: {
        startAngle: 0,
        endAngle: 360,
        expandOnClick: true,
        offsetX: 0,
        offsetY: 0,
        customScale: 1,
        dataLabels: {
          offset: 0,
          minAngleToShowLabel: 10
        },
        donut: {
          size: '65%',
          background: 'transparent',
          labels: {
            show: true,
            name: {
              show: false
            },
            value: {
              show: true,
              fontSize: '16px',
              fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
              fontWeight: 700,
              color: '#1e293b',
              offsetY: 0,
              formatter: function (val) {
                return typeof val === 'number' ? val.toFixed(1) + '%' : '0.0%';
              }
            },
            total: {
              show: false
            }
          }
        }
      }
    },
    dataLabels: {
      enabled: true,
      formatter: function (val, opts) {
        return opts.w.globals.series[opts.seriesIndex].toFixed(1) + '%';
      },
      style: {
        fontSize: '14px',
        fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
        fontWeight: 600,
        colors: ['#ffffff']
      },
      dropShadow: {
        enabled: true,
        opacity: 0.3,
        blur: 3,
        left: 1,
        top: 1
      }
    },
    legend: {
      show: false
    },
    tooltip: {
      enabled: true,
      theme: 'light',
      custom: function({ series, seriesIndex, dataPointIndex, w }) {
        const spend = actualSpend[seriesIndex] || 0;
        const percentage = series[seriesIndex];
        const label = labels[seriesIndex];
        const formattedSpend = typeof spend === 'number' ? spend.toLocaleString() : spend;
        return `<div style="
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 12px 16px;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
          font-family: 'Pretendard', sans-serif;
          max-width: 280px;
        ">
          <div style="
            font-weight: 600;
            font-size: 14px;
            color: #1e293b;
            margin-bottom: 8px;
            border-bottom: 1px solid #f1f5f9;
            padding-bottom: 8px;
          ">${label}</div>
          <div style="
            font-weight: 600;
            font-size: 14px;
            color: #6366f1;
          ">₩${formattedSpend}</div>
          <div style="
            font-weight: 500;
            font-size: 13px;
            color: #475569;
            margin-top: 4px;
          ">${percentage.toFixed(1)}%</div>
        </div>`;
      }
    },
    responsive: [
      {
        breakpoint: 768,
        options: {
          chart: {
            height: 300
          }
        }
      }
    ]
  };

  // ApexCharts 인스턴스 생성
  typePieChartInstance = new ApexCharts(chartContainer, options);
  typePieChartInstance.render();

  console.log("[DEBUG] 캠페인 목표별 지출 비중 차트 렌더링 완료");
}
