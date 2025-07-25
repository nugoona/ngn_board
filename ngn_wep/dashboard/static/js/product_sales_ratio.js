// resolveDateRange 함수 정의 (meta_ads_utils.js에서 가져옴)
function resolveDateRange(period) {
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, "0");
  const dd = String(today.getDate()).padStart(2, "0");

  let start = `${yyyy}-${mm}-${dd}`;
  let end = start;

  if (period === "yesterday") {
    const y = new Date(today);
    y.setDate(y.getDate() - 1);
    start = y.toISOString().slice(0, 10);
    end = y.toISOString().slice(0, 10);
  } else if (period === "last7days") {
    const s = new Date(today);
    s.setDate(s.getDate() - 7);
    start = s.toISOString().slice(0, 10);
  } else if (period === "last_month") {
    const s = new Date(today);
    s.setMonth(s.getMonth() - 1);
    s.setDate(1);
    const e = new Date(s.getFullYear(), s.getMonth() + 1, 0);
    start = s.toISOString().slice(0, 10);
    end = e.toISOString().slice(0, 10);
  }

  return { start, end };
}

let currentPage_ratio = 1;
const limit_ratio = 10;
let chartInstance_ratio = null;
let allProductSalesRatioData = [];

function fetchProductSalesRatio(requestData) {
  // requestData가 없으면 현재 필터값으로 생성
  if (!requestData) {
    requestData = getRequestData(1, {
      data_type: "product_sales_ratio"
    });
  }
  
  // period가 manual이 아닌 경우 날짜를 resolveDateRange로 계산
  if (requestData.period !== "manual") {
    const resolved = resolveDateRange(requestData.period);
    requestData.start_date = resolved.start;
    requestData.end_date = resolved.end;
  }
  
  // 날짜 정보가 없으면 오늘 날짜로 설정 (fallback)
  if (!requestData.start_date || !requestData.end_date) {
    const today = new Date().toISOString().split("T")[0];
    requestData.start_date = requestData.start_date || today;
    requestData.end_date = requestData.end_date || today;
  }
  
  if (requestData.period === "manual" && !requestData.end_date) {
    console.warn("[SKIP] 종료일 누락 - 상품군 매출 비중 요청 생략");
    return;
  }

  console.log("[DEBUG] 상품군 매출 비중 요청 데이터:", requestData);
  showLoading("#loadingOverlayProductSalesRatio");

  latestAjaxRequest("product_sales_ratio", {
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify({
      ...requestData,
      data_type: "product_sales_ratio"
    }),
    error: function (xhr, status, error) {
      hideLoading("#loadingOverlayProductSalesRatio");
      console.error("[ERROR] 상품군 매출 비중 오류:", status, error);
    }
  }, function (res) {
    hideLoading("#loadingOverlayProductSalesRatio");

    console.log("[DEBUG] 상품군 매출 비중 응답 결과:", res);
    if (res.status === "success") {
      allProductSalesRatioData = res.product_sales_ratio || [];

      if (!Array.isArray(allProductSalesRatioData) || allProductSalesRatioData.length === 0) {
        console.warn("[WARN] 상품군 매출 비중 데이터 없음");
        $("#productSalesRatioTableBody").html(`<tr><td colspan="6">데이터가 없습니다.</td></tr>`);
        $("#productSalesRatioChart").replaceWith('<canvas id="productSalesRatioChart"></canvas>');
        return;
      }

      currentPage_ratio = 1;
      renderProductSalesRatioTable(currentPage_ratio);
      setupPagination_ratio();
      
      // ✅ 초기에는 차트 숨김 상태 유지 (토글 버튼 클릭 시에만 표시)
      console.log("[DEBUG] 📊 데이터 로딩 완료, 초기 상태는 차트 숨김");
    } else {
      console.warn("[WARN] 상품군 매출 비중 응답 실패", res);
    }
  });
}

function renderProductSalesRatioTable(page) {
  const tbody = $("#productSalesRatioTableBody");
  tbody.empty();

  const start = (page - 1) * limit_ratio;
  const end = start + limit_ratio;
  const pageData = allProductSalesRatioData.slice(start, end);

  if (pageData.length === 0) {
    tbody.append("<tr><td colspan='6'>데이터가 없습니다.</td></tr>");
    return;
  }

  pageData.forEach(row => {
    const tr = $("<tr></tr>");
    tr.append(`<td>${row.report_period || "-"}</td>`);
    tr.append(`<td>${row.company_name || "-"}</td>`);
    tr.append(`<td>${row.cleaned_product_name || "-"}</td>`);
    tr.append(`<td>${row.item_quantity || 0}</td>`);
    tr.append(`<td>${cleanData(row.item_product_sales)}</td>`);
    tr.append(`<td>${(row.sales_ratio_percent || 0).toFixed(1)}%</td>`);
    tbody.append(tr);
  });
}

function renderProductSalesRatioChart() {
  // ApexCharts가 로드되었는지 확인
  if (typeof ApexCharts === 'undefined') {
    console.warn('ApexCharts not loaded, retrying in 100ms...');
    setTimeout(renderProductSalesRatioChart, 100);
    return;
  }

  // 차트 컨테이너 존재 확인
  const chartContainer = document.querySelector("#productSalesRatioChart");
  if (!chartContainer) {
    console.error("[ERROR] 차트 컨테이너를 찾을 수 없음: #productSalesRatioChart");
    return;
  }

  // 데이터 확인
  if (!Array.isArray(allProductSalesRatioData) || allProductSalesRatioData.length === 0) {
    console.warn("[WARN] 차트 데이터가 없음");
    return;
  }

  const top5 = [...allProductSalesRatioData]
    .sort((a, b) => b.sales_ratio_percent - a.sales_ratio_percent)
    .slice(0, 5);

  console.log("[DEBUG] 상품 매출 비중 top5 데이터:", top5);

  const labels = top5.map(d => d.cleaned_product_name);
  const values = top5.map(d => d.sales_ratio_percent);
  const actualSales = top5.map(d => d.item_product_sales);  // 원본 숫자 값 유지

  console.log("[DEBUG] 상품 매출 비중 차트 데이터:", {
    labels,
    values,
    actualSales
  });

  // 기존 차트 인스턴스 제거
  if (chartInstance_ratio) {
    chartInstance_ratio.destroy();
  }

  // 차트 컨테이너 초기화
  chartContainer.innerHTML = '';

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
    colors: ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'],
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
      position: 'right',
      fontSize: '14px',
      fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
      fontWeight: 500,
      markers: {
        radius: 6
      },
      itemMargin: {
        horizontal: 10,
        vertical: 5
      },
      formatter: function(seriesName, opts) {
        const value = opts.w.globals.series[opts.seriesIndex];
        return `${seriesName} (${value.toFixed(1)}%)`;
      }
    },
    tooltip: {
      enabled: true,
      theme: 'light',
      style: {
        fontSize: '14px'
      },
      custom: function({ series, seriesIndex, dataPointIndex, w }) {
        const sales = actualSales[seriesIndex] || 0;
        const percentage = series[seriesIndex];
        const label = labels[seriesIndex];
        const formattedSales = typeof sales === 'number' ? sales.toLocaleString() : sales;
        return `<div class="custom-tooltip" style="
          background: rgba(255, 255, 255, 0.98);
          border: 1px solid rgba(99, 102, 241, 0.2);
          border-radius: 12px;
          padding: 12px 16px;
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
          font-family: 'Pretendard', sans-serif;
        ">
          <div class="tooltip-label" style="
            font-weight: 600;
            font-size: 14px;
            color: #374151;
            margin-bottom: 4px;
            line-height: 1.4;
          ">${label}</div>
          <div class="tooltip-value" style="
            font-weight: 500;
            font-size: 13px;
            color: #6366f1;
          ">₩${formattedSales} (${percentage.toFixed(1)}%)</div>
        </div>`;
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
  chartInstance_ratio = new ApexCharts(chartContainer, options);
  chartInstance_ratio.render();
  
  console.log("[DEBUG] 상품 매출 비중 차트 렌더링 완료");
}

function setupPagination_ratio() {
  const pagination = $("#pagination_product_sales_ratio");
  pagination.empty();

  const totalPages = Math.ceil(allProductSalesRatioData.length / limit_ratio);
  if (totalPages <= 1) return;

  const prevBtn = $('<button class="pagination-btn">이전</button>');
  if (currentPage_ratio === 1) {
    prevBtn.prop("disabled", true).addClass("disabled");
  } else {
    prevBtn.click(() => {
      currentPage_ratio--;
      renderProductSalesRatioTable(currentPage_ratio);
      setupPagination_ratio();
    });
  }

  const nextBtn = $('<button class="pagination-btn">다음</button>');
  if (currentPage_ratio === totalPages) {
    nextBtn.prop("disabled", true).addClass("disabled");
  } else {
    nextBtn.click(() => {
      currentPage_ratio++;
      renderProductSalesRatioTable(currentPage_ratio);
      setupPagination_ratio();
    });
  }

  const pageInfo = $(`<span class="pagination-info">${currentPage_ratio} / ${totalPages}</span>`);
  pagination.append(prevBtn, pageInfo, nextBtn);
}

// ✅ 토글 버튼 제어 - DOMContentLoaded 이벤트로 변경
$(document).ready(function() {
  $("#toggleProductSalesRatioChart").on("click", function () {
    const chartContainer = $("#productSalesRatioChartContainer");
    const isVisible = chartContainer.is(":visible");
    chartContainer.toggle();
    $(this).text(isVisible ? "상위 TOP5 차트 보기" : "상위 TOP5 차트 숨기기");
    if (!isVisible) {
      console.log("[DEBUG] 상품 매출 비중 차트 토글 - 차트 렌더링 시작");
      renderProductSalesRatioChart();
    }
  });
});



// 전역 함수로 노출
window.fetchProductSalesRatio = fetchProductSalesRatio;
