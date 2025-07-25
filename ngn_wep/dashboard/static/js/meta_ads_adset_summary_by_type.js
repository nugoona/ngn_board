// File: static/js/meta_ads_adset_summary_by_type.js

import { resolveDateRange } from "./meta_ads_utils.js";
// showLoading/hideLoading 함수는 common.js에서 정의됨
import { metaAdsState } from "./meta_ads_state.js";

const $ = window.$;
let typePieChartInstance = null;
let adsetSummaryRequest = null;

// ✅ 파라미터 기본값 추가: {} → undefined 방지
export function fetchMetaAdsAdsetSummaryByType({ period, start_date, end_date, account_id } = {}) {
  // 순차 실행이므로 abort 제거
  // if (adsetSummaryRequest) {
  //   adsetSummaryRequest.abort();
  // }

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

            console.log("[DEBUG] Ajax 응답 전체:", res);
            console.log("[DEBUG] res.data:", res?.data);
            console.log("[DEBUG] res.status:", res?.status);

            const typeSummary = res?.data?.type_summary || [];
            const totalSpendSum = res?.data?.total_spend_sum || 0;

            console.log("[DEBUG] 캠페인 목표별 요약 응답:", typeSummary, totalSpendSum);
            console.log("[DEBUG] typeSummary 길이:", typeSummary.length);
            console.log("[DEBUG] totalSpendSum 값:", totalSpendSum);

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
  console.log("[DEBUG] renderMetaAdsAdsetSummaryChart 호출됨", { data, totalSpendSum });
  
  // Chart.js가 로드되었는지 확인
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js not loaded, retrying in 500ms...');
    setTimeout(() => renderMetaAdsAdsetSummaryChart(data, totalSpendSum), 500);
    return;
  }

  const chartContainer = document.getElementById("metaAdsAdsetSummaryChart");
  console.log("[DEBUG] 차트 컨테이너:", chartContainer);

  if (!chartContainer) {
    console.error("[ERROR] metaAdsAdsetSummaryChart 컨테이너를 찾을 수 없습니다!");
    return;
  }

  // 기존 차트 인스턴스 제거
  if (typePieChartInstance) {
    typePieChartInstance.destroy();
  }

  console.log("[DEBUG] 차트 컨테이너 표시됨");

  // 데이터가 없거나 총 지출이 0인 경우 빈 차트 표시
  if (!data || data.length === 0 || totalSpendSum === 0) {
    console.log("[DEBUG] 빈 차트 렌더링");
    
    const emptyCtx = chartContainer.getContext('2d');
    typePieChartInstance = new Chart(emptyCtx, {
      type: 'doughnut',
      data: {
        labels: ['데이터 없음'],
        datasets: [{
          data: [100],
          backgroundColor: ['#e5e7eb'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            enabled: false
          }
        },
        animation: {
          animateRotate: true,
          animateScale: true,
          duration: 1000,
          easing: 'easeOutQuart'
        }
      }
    });
    
    console.log("[DEBUG] 빈 차트 렌더링 완료");
    return;
  }

  console.log("[DEBUG] 실제 데이터로 차트 렌더링");
  const labels = data.map(row => row.type || "-");
  const values = data.map(row => totalSpendSum ? (row.total_spend / totalSpendSum * 100) : 0);
  console.log("[DEBUG] 차트 데이터:", { labels, values });

  // 모던한 색상 팔레트
  const colors = [
    '#3b82f6', // blue
    '#f59e0b', // amber
    '#10b981', // emerald
    '#ef4444', // red
    '#8b5cf6', // violet
    '#06b6d4', // cyan
    '#84cc16', // lime
    '#f97316'  // orange
  ];

  const ctx = chartContainer.getContext('2d');
  typePieChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: colors.slice(0, labels.length),
        borderWidth: 0,
        hoverBorderWidth: 2,
        hoverBorderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: {
        padding: 20
      },
      plugins: {
        legend: {
          position: 'right',
          labels: {
            font: {
              family: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
              size: 14,
              weight: '500'
            },
            color: '#374151',
            padding: 20,
            usePointStyle: true,
            pointStyle: 'circle',
            generateLabels: function(chart) {
              const data = chart.data;
              if (data.labels.length && data.datasets.length) {
                return data.labels.map((label, i) => {
                  const value = data.datasets[0].data[i];
                  const color = data.datasets[0].backgroundColor[i];
                  return {
                    text: `${label} (${value.toFixed(1)}%)`,
                    fillStyle: color,
                    strokeStyle: color,
                    pointStyle: 'circle',
                    hidden: false,
                    index: i
                  };
                });
              }
              return [];
            }
          }
        },
        tooltip: {
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          titleColor: '#1e293b',
          bodyColor: '#374151',
          borderColor: 'rgba(226, 232, 240, 0.8)',
          borderWidth: 1,
          cornerRadius: 12,
          displayColors: true,
          titleFont: {
            family: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
            size: 14,
            weight: '600'
          },
          bodyFont: {
            family: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
            size: 13,
            weight: '500'
          },
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.parsed;
              return `${label}: ${value.toFixed(1)}%`;
            }
          }
        }
      },
      animation: {
        animateRotate: true,
        animateScale: true,
        duration: 1200,
        easing: 'easeOutQuart',
        onProgress: function(animation) {
          // 애니메이션 진행 중 추가 효과
        },
        onComplete: function(animation) {
          console.log("[DEBUG] 차트 애니메이션 완료");
        }
      },
      cutout: '60%',
      radius: '90%'
    }
  });

  console.log("[DEBUG] 캠페인 목표별 차트 렌더링 완료");
}
