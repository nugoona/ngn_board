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
  // ApexCharts가 로드되었는지 확인
  if (typeof ApexCharts === 'undefined') {
    console.warn('ApexCharts not loaded, retrying in 100ms...');
    setTimeout(() => renderMetaAdsAdsetSummaryChart(data, totalSpendSum), 100);
    return;
  }

  const chartContainer = document.getElementById("metaAdsAdsetSummaryChart");

  if (typePieChartInstance) {
    typePieChartInstance.destroy();
  }

  if (totalSpendSum === 0) {
    chartContainer.style.display = "none";
    return;
  } else {
    chartContainer.style.display = "block";
  }

  const labels = data.map(row => row.type || "-");
  const values = data.map(row => totalSpendSum ? (row.total_spend / totalSpendSum * 100) : 0);

  // ApexCharts 옵션 설정
  const options = {
    series: values,
    chart: {
      type: 'pie',
      height: 400,
      fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
      animations: {
        enabled: true,
        easing: 'easeinout',
        speed: 800,
        animateGradually: {
          enabled: true,
          delay: 150
        },
        dynamicAnimation: {
          enabled: true,
          speed: 350
        }
      }
    },
    labels: labels,
    colors: ['#4e73df', '#f6c23e', '#36b9cc', '#e74a3b', '#6f42c1'],
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
            show: false,
            name: {
              show: true,
              fontSize: '22px',
              fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
              fontWeight: 600,
              color: undefined,
              offsetY: -10
            },
            value: {
              show: true,
              fontSize: '16px',
              fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
              fontWeight: 400,
              color: undefined,
              offsetY: 16,
              formatter: function (val) {
                return val.toFixed(1) + '%';
              }
            },
            total: {
              show: false,
              label: 'Total',
              fontSize: '16px',
              fontWeight: 600,
              formatter: function (w) {
                return w.globals.seriesTotals.reduce((a, b) => a + b, 0);
              }
            }
          }
        }
      }
    },
    dataLabels: {
      enabled: false // 내부 숫자 제거
    },
    legend: {
      position: 'left',
      fontSize: '14px',
      fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
      fontWeight: 600,
      markers: {
        radius: 6
      },
      itemMargin: {
        horizontal: 10,
        vertical: 5
      },
      formatter: function(seriesName, opts) {
        const value = opts.w.globals.series[opts.seriesIndex];
        return `${seriesName} ${Math.round(value)}%`;
      }
    },
    tooltip: {
      enabled: true,
      theme: 'light',
      style: {
        fontSize: '14px'
      },
      y: {
        formatter: function(value, { series, seriesIndex, dataPointIndex, w }) {
          return `${labels[seriesIndex]}: ${value.toFixed(1)}%`;
        }
      }
    },
    responsive: [
      {
        breakpoint: 768,
        options: {
          chart: {
            height: 300
          },
          legend: {
            position: 'bottom'
          }
        }
      }
    ]
  };

  // ApexCharts 인스턴스 생성
  typePieChartInstance = new ApexCharts(document.querySelector("#metaAdsAdsetSummaryChart"), options);
  typePieChartInstance.render();
}
