// File: static/js/meta_ads_adset_summary_by_type.js

console.log("[DEBUG] 🔥 meta_ads_adset_summary_by_type.js 로드됨");

import { resolveDateRange } from "./meta_ads_utils.js";
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

  try {
    if (typeof showLoading === 'function') {
      showLoading("#loadingOverlayTypeSummary");
    }
  } catch (e) {
    console.warn("[WARN] showLoading 함수 호출 실패:", e);
  }

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
            try {
              if (typeof hideLoading === 'function') {
                hideLoading("#loadingOverlayTypeSummary");
              }
            } catch (e) {
              console.warn("[WARN] hideLoading 함수 호출 실패:", e);
            }

            const typeSummary = res?.data?.type_summary || [];
            const totalSpendSum = res?.data?.total_spend_sum || 0;

            console.log("[DEBUG] 캠페인 목표별 요약 응답:", typeSummary, totalSpendSum);

            renderMetaAdsAdsetSummaryTable(typeSummary);
            renderMetaAdsAdsetSummaryChart(typeSummary, totalSpendSum);
          },
          error: function (err) {
            try {
              if (typeof hideLoading === 'function') {
                hideLoading("#loadingOverlayTypeSummary");
              }
            } catch (e) {
              console.warn("[WARN] hideLoading 함수 호출 실패:", e);
            }
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

  let totalSpend = 0;
  let totalImpressions = 0;
  let totalClicks = 0;
  let totalPurchases = 0;
  let totalPurchaseValue = 0;

  data.forEach(row => {
    const CPM       = row.CPM ? Math.round(row.CPM).toLocaleString() : "0";
    const CPC       = row.CPC ? Math.round(row.CPC).toLocaleString() : "0";
    const spend     = row.total_spend ? row.total_spend.toLocaleString() : "0";
    const purchases = row.total_purchases || 0;
    const ROAS      = row.ROAS ? Math.round(row.ROAS * 100).toLocaleString() + "%" : "0%";

    totalSpend += row.total_spend || 0;
    totalImpressions += row.total_impressions || 0;
    totalClicks += row.total_clicks || 0;
    totalPurchases += row.total_purchases || 0;
    totalPurchaseValue += row.total_purchase_value || 0;

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

  // 총합 로우 추가
  const totalCPM = totalImpressions > 0 ? Math.round((totalSpend / totalImpressions) * 1000).toLocaleString() : "0";
  const totalCPC = totalClicks > 0 ? Math.round(totalSpend / totalClicks).toLocaleString() : "0";
  const totalROAS = totalSpend > 0 ? Math.round((totalPurchaseValue / totalSpend) * 100).toLocaleString() + "%" : "0%";

  const totalHtml = `
    <tr style="font-weight: bold; background-color: #f3f4f6;">
      <td>총합</td>
      <td>${totalSpend.toLocaleString()}</td>
      <td>${totalCPM}</td>
      <td>${totalCPC}</td>
      <td>${totalPurchases}</td>
      <td>${totalROAS}</td>
    </tr>
  `;
  $tbody.append(totalHtml);
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
          fontSize: 16,
          fontWeight: 'bold',
          color: '#333'
        }
      },
      series: [{
        type: 'pie',
        radius: ['30%', '70%'],
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
    name: row.type || "-"
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
        fontSize: 16,
        fontWeight: 'bold',
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    series: [{
      name: '지출 비중',
      type: 'pie',
      radius: ['30%', '70%'],
      center: ['50%', '60%'],
      data: chartData,
      color: ['#4e73df', '#f6c23e', '#36b9cc', '#e74a3b', '#6f42c1'],
      label: {
        show: true,
        formatter: '{b}: {d}%'
      },
      labelLine: {
        show: true
      }
    }]
  };
  myChart.setOption(option);
}
