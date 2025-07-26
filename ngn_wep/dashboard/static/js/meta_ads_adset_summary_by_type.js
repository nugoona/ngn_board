// File: static/js/meta_ads_adset_summary_by_type.js

import { showLoading, hideLoading, resolveDateRange } from "./meta_ads_utils.js";
import { metaAdsState } from "./meta_ads_state.js";

const $ = window.$;
let typePieChartInstance = null;
let adsetSummaryRequest = null;

// ✅ 파라미터 기본값 추가: {} → undefined 방지
export function fetchMetaAdsAdsetSummaryByType({ period, start_date, end_date, account_id } = {}) {
  if (adsetSummaryRequest) {
    adsetSummaryRequest.abort();
  }

  // ✅ 기간 보정 로직 추가 (manual 외엔 자동 계산)
  if ((!start_date || !end_date) && period !== "manual") {
    const resolved = resolveDateRange(period);
    start_date = resolved.start;
    end_date = resolved.end;
  }

  console.log("[DEBUG] fetchMetaAdsAdsetSummaryByType 호출됨", {
    accountId: account_id, period, startDate: start_date, endDate: end_date
  });

  if (!account_id) {
    console.warn("[SKIP] accountId 없음 - 빈 테이블/차트 렌더링");
    renderMetaAdsAdsetSummaryTable([]);
    renderMetaAdsAdsetSummaryChart([], 0);
    return;
  }

  showLoading("#loadingOverlayTypeSummary");

        const payload = {
          data_type: "meta_ads_adset_summary_by_type",
          account_id,
          period,
          start_date: start_date || null,
          end_date: end_date || null
        };

        adsetSummaryRequest = $.ajax({
          url: "/dashboard/get_data",
          method: "POST",
          contentType: "application/json",
          data: JSON.stringify(payload),
          success: function (res) {
            hideLoading("#loadingOverlayTypeSummary");

            const typeSummary = res?.data?.type_summary || [];
            const totalSpendSum = res?.data?.total_spend_sum || 0;

            console.log("[DEBUG] 캠페인 목표별 요약 응답:", typeSummary, totalSpendSum);

            renderMetaAdsAdsetSummaryTable(typeSummary);
            renderMetaAdsAdsetSummaryChart(typeSummary, totalSpendSum);
          },
          error: function (err) {
            hideLoading("#loadingOverlayTypeSummary");
            console.error("[ERROR] 캠페인 목표별 요약 로드 실패", err);
            $("#metaAdsAdsetSummaryTableBody").html('<tr><td colspan="6">데이터를 불러오는 중 오류가 발생했습니다.</td></tr>');
          }
        });
}

function renderMetaAdsAdsetSummaryTable(data) {
  const $tbody = $("#metaAdsAdsetSummaryTable tbody");
  $tbody.empty();

  if (!data || data.length === 0) {
    $tbody.append("<tr><td colspan='6'>데이터가 없습니다.</td></tr>");
    return;
  }

  data.forEach(row => {
    const CPM       = row.CPM ? Math.round(row.CPM).toLocaleString() : "0";
    const CPC       = row.CPC ? Math.round(row.CPC).toLocaleString() : "0";
    const spend     = row.total_spend ? row.total_spend.toLocaleString() : "0";
    const purchases = row.total_purchases || 0;
    const ROAS      = row.ROAS ? Math.round(row.ROAS * 100).toLocaleString() + "%" : "0%";

    const html = `
      <tr>
        <td>${row.type || "-"}</td>
        <td>${spend}</td>
        <td>${CPM}</td>
        <td>${CPC}</td>
        <td>${purchases}</td>
        <td>${ROAS}</td>
      </tr>
    `;
    $tbody.append(html);
  });
}

function renderMetaAdsAdsetSummaryChart(data, totalSpendSum) {
  const chartDom = document.getElementById('metaAdsAdsetSummaryChart');
  if (!chartDom) return;
  
  // 기존 차트 인스턴스 제거
  if (window.echartsMetaAdsAdsetSummary) {
    window.echartsMetaAdsAdsetSummary.dispose();
  }

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
