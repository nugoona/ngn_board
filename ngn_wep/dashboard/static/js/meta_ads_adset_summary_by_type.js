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
    tr.append(`<td style="text-align: center;">${row.type || "-"}</td>`);
    tr.append(`<td style="text-align: center;">${spend.toLocaleString()}</td>`);
    tr.append(`<td style="text-align: center;">${cpm.toFixed(0)}</td>`);
    tr.append(`<td style="text-align: center;">${cpc.toFixed(0)}</td>`);
    tr.append(`<td style="text-align: center;">${purchases.toLocaleString()}</td>`);
    tr.append(`<td style="text-align: center;">${roas.toFixed(1)}%</td>`);
    
    tbody.append(tr);
  });

  // 합계 행 추가
  const totalCpm = totalImpressions > 0 ? (totalSpend / totalImpressions) * 1000 : 0;
  const totalCpc = totalClicks > 0 ? totalSpend / totalClicks : 0;
  const totalRoas = totalSpend > 0 ? (totalPurchaseValue / totalSpend) * 100 : 0;

  const totalTr = $("<tr style='font-weight: bold; background-color: #f3f4f6;'></tr>");
  totalTr.append(`<td style="text-align: center;">총합</td>`);
  totalTr.append(`<td style="text-align: center;">${totalSpend.toLocaleString()}</td>`);
  totalTr.append(`<td style="text-align: center;">${totalCpm.toFixed(0)}</td>`);
  totalTr.append(`<td style="text-align: center;">${totalCpc.toFixed(0)}</td>`);
  totalTr.append(`<td style="text-align: center;">${totalPurchases.toLocaleString()}</td>`);
  totalTr.append(`<td style="text-align: center;">${totalRoas.toFixed(1)}%</td>`);
  
  tbody.append(totalTr);
}

function renderMetaAdsAdsetSummaryChart(data, totalSpendSum) {
  const chartDom = document.getElementById('metaAdsAdsetSummaryChart');
  if (!chartDom) return;
  
  // 기존 차트 인스턴스 제거
  if (window.echartsMetaAdsAdsetSummary) {
    window.echartsMetaAdsAdsetSummary.dispose();
  }

  // 총 지출 계산
  totalSpendSum = totalSpendSum || data.reduce((sum, row) => sum + (row.total_spend || 0), 0);

  // 데이터가 없는 경우 빈 차트 표시
  if (!data || data.length === 0 || totalSpendSum === 0) {
    console.log("[DEBUG] 빈 차트 렌더링");
    const myChart = echarts.init(chartDom, null, {renderer: 'svg'});
    window.echartsMetaAdsAdsetSummary = myChart;
    
    const option = {
      title: {
        text: '목표별 지출 비중',
        left: 'center',
        top: 20,
        textStyle: {
          fontSize: 22,
          fontWeight: '700',
          fontFamily: 'Pretendard, sans-serif',
          color: '#ffffff'
        },
        backgroundColor: '#1e293b',
        borderRadius: 6,
        padding: [12, 24],
        shadowBlur: 8,
        shadowColor: 'rgba(0, 0, 0, 0.15)',
        shadowOffsetX: 2,
        shadowOffsetY: 2
      },
             series: [{
         type: 'pie',
         radius: ['25%', '65%'],
         center: ['50%', '60%'],
        data: [{ value: 100, name: '데이터 없음' }],
        color: ['#e5e7eb'],
        label: {
          show: false
        }
      }]
    };
    myChart.setOption(option);
    return;
  }

  console.log("[DEBUG] 실제 데이터로 차트 렌더링");
  
  const chartData = data.map(row => ({
    value: totalSpendSum ? (row.total_spend / totalSpendSum * 100) : 0,
    name: row.type || "-",
    actualSpend: row.total_spend || 0
  }));

  // ECharts 인스턴스 생성
  const myChart = echarts.init(chartDom, null, {renderer: 'svg'});
  window.echartsMetaAdsAdsetSummary = myChart;

  const option = {
    title: {
      text: '목표별 지출 비중',
      left: 'center',
      top: 20,
      textStyle: {
        fontSize: 22,
        fontWeight: '700',
        fontFamily: 'Pretendard, sans-serif',
        color: '#ffffff'
      },
      backgroundColor: '#1e293b',
      borderRadius: 6,
      padding: [12, 24],
      shadowBlur: 8,
      shadowColor: 'rgba(0, 0, 0, 0.15)',
      shadowOffsetX: 2,
      shadowOffsetY: 2
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        const actualSpend = params.data.actualSpend || 0;
        const formattedSpend = actualSpend.toLocaleString();
        return `${params.name}<br/>₩${formattedSpend} (${params.value}%)`;
      }
    },
    graphic: [{
      type: 'line',
      left: 'center',
      top: 70,
      shape: {
        x1: -80,
        y1: 0,
        x2: 80,
        y2: 0
      },
      style: {
        stroke: '#e2e8f0',
        lineWidth: 2,
        shadowBlur: 2,
        shadowColor: 'rgba(0, 0, 0, 0.1)'
      }
    }],
          series: [{
        name: '지출 비중',
        type: 'pie',
        radius: ['25%', '65%'],
        center: ['50%', '60%'],
      data: chartData,
      color: ['#4e73df', '#f6c23e', '#36b9cc', '#e74a3b', '#6f42c1'],
      label: {
        show: true,
        position: 'outside',
        align: 'center',
        formatter: function(params) {
          return `{percentage|${params.value.toFixed(1)}%}\n{goalName|${params.name}}`;
        },
        fontSize: 14,
        fontFamily: 'Pretendard, sans-serif',
        backgroundColor: 'transparent',
        borderRadius: 8,
        padding: [0, 0],
        borderColor: 'transparent',
        borderWidth: 0,
        shadowBlur: 4,
        shadowColor: 'rgba(0, 0, 0, 0.3)',
        shadowOffsetX: 2,
        shadowOffsetY: 2,
        rich: {
          percentage: {
            fontSize: 24,
            fontWeight: 'bold',
            color: '#000',
            backgroundColor: '#ffffff',
            borderRadius: [8, 8, 0, 0],
            padding: [8, 12, 4, 12],
            textAlign: 'center',
            borderColor: '#e2e8f0',
            borderWidth: 1
          },
          goalName: {
            fontSize: 18,
            fontWeight: '600',
            color: '#ffffff',
            backgroundColor: '#4a5568',
            borderRadius: [0, 0, 8, 8],
            padding: [4, 12, 8, 12],
            textAlign: 'center',
            borderColor: '#4a5568',
            borderWidth: 1
          }
        }
      },
      labelLine: {
        show: true,
        length: 10,
        length2: 15,
        smooth: true,
        lineStyle: {
          width: 2,
          color: '#cbd5e1',
          shadowBlur: 3,
          shadowColor: 'rgba(0, 0, 0, 0.1)'
        }
      },
      itemStyle: {
        shadowBlur: 8,
        shadowOffsetX: 2,
        shadowOffsetY: 2,
        shadowColor: 'rgba(0, 0, 0, 0.1)'
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 15,
          shadowOffsetX: 4,
          shadowOffsetY: 4,
          shadowColor: 'rgba(0, 0, 0, 0.2)'
        }
      }
    }]
  };
  myChart.setOption(option);
}
