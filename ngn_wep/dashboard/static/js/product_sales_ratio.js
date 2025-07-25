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
let chartInstance_product = null;
let allProductSalesRatioData = [];

function fetchProductSalesRatio(requestData) {
  const company = $("#accountFilter").val(); 
  const period = $("#periodSelector").val();
  const startDate = $("#startDate").val();
  const endDate = $("#endDate").val();

  if (period === "manual" && !endDate) {
    console.warn("[SKIP] 종료일 누락 - 주요 상품 매출 비중 차트 실행 중단");
    return;
  }

  // requestData가 없으면 생성
  if (!requestData) {
    requestData = getRequestData(1, {
      data_type: "product_sales_ratio"
    });
  }

  console.log("[DEBUG] 주요 상품 매출 비중 요청:", requestData);
  showLoading("#loadingOverlayProductSalesRatio");

  latestAjaxRequest("product_sales_ratio", {
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(requestData),
    error: function (xhr, status, error) {
      hideLoading("#loadingOverlayProductSalesRatio");
      console.error("[ERROR] 주요 상품 매출 비중 오류:", status, error);
    }
  }, function (res) {
    hideLoading("#loadingOverlayProductSalesRatio");

    if (res.status === "success") {
      allProductSalesRatioData = res.product_sales_ratio || [];
      console.log("[DEBUG] 주요 상품 매출 비중 데이터 수신:", allProductSalesRatioData);
      renderProductSalesRatioTable(1);
      setupPagination_ratio();
      // 차트는 버튼 클릭 시에만 렌더링
    } else {
      console.warn("[WARN] 주요 상품 매출 비중 응답 없음", res);
      allProductSalesRatioData = [];
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
  console.log("[DEBUG] renderProductSalesRatioChart 호출됨");
  
  // ApexCharts가 로드되었는지 확인
  if (typeof ApexCharts === 'undefined') {
    console.warn('ApexCharts not loaded, retrying in 100ms...');
    setTimeout(() => renderProductSalesRatioChart(), 100);
    return;
  }

  const chartContainer = document.getElementById("productSalesRatioChart");
  console.log("[DEBUG] 차트 컨테이너:", chartContainer);

  if (!chartContainer) {
    console.error("[ERROR] productSalesRatioChart 컨테이너를 찾을 수 없습니다!");
    return;
  }

  // 기존 차트 인스턴스 제거
  if (chartInstance_product) {
    chartInstance_product.destroy();
  }

  // 데이터가 없거나 총 매출이 0인 경우 빈 차트 표시
  if (!allProductSalesRatioData || allProductSalesRatioData.length === 0) {
    console.log("[DEBUG] 빈 차트 렌더링");
    
    chartInstance_product = new ApexCharts(chartContainer, {
      series: [100],
      chart: {
        type: 'pie',
        height: 400,
        fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
        animations: {
          enabled: false // 애니메이션 제거
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
        position: 'left', // 왼쪽 정렬
        fontSize: '14px',
        fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
        fontWeight: 500
      }
    });
    
    chartInstance_product.render();
    console.log("[DEBUG] 빈 차트 렌더링 완료");
    return;
  }

  console.log("[DEBUG] 실제 데이터로 차트 렌더링");
  
  // 상위 5개 상품만 선택
  const top5Data = allProductSalesRatioData.slice(0, 5);
  const labels = top5Data.map(item => item.cleaned_product_name || item.product_name || "-");
  const values = top5Data.map(item => item.sales_ratio_percent || item.sales_ratio || 0);
  const actualSales = top5Data.map(item => item.item_product_sales || item.total_sales || 0);
  
  console.log("[DEBUG] 차트 데이터:", { labels, values, actualSales });

  // ApexCharts 옵션 설정
  const options = {
    series: values,
    chart: {
      type: 'pie',
      height: 400,
      fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
      animations: {
        enabled: false // 애니메이션 제거
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
                return typeof val === 'number' ? val.toFixed(1) + '%' : '0.0%';
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
      enabled: false // 내부 퍼센트 제거
    },
    legend: {
      position: 'left', // 왼쪽 정렬
      fontSize: '14px',
      fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
      fontWeight: 500,
      markers: {
        radius: 6,
        width: 12,
        height: 12
      },
      itemMargin: {
        horizontal: 15,
        vertical: 8
      },
      formatter: function(seriesName, opts) {
        const value = opts.w.globals.series[opts.seriesIndex];
        return `${seriesName} (${value.toFixed(1)}%)`;
      },
      onItemClick: {
        toggleDataSeries: false
      }
    },
    tooltip: {
      enabled: true,
      theme: 'light',
      style: {
        fontSize: '12px'
      },
      custom: function({ series, seriesIndex, dataPointIndex, w }) {
        const sales = actualSales[seriesIndex] || 0;
        const percentage = series[seriesIndex];
        const label = labels[seriesIndex];
        const formattedSales = typeof sales === 'number' ? sales.toLocaleString() : sales;
        return `<div class="custom-tooltip" style="
          background: rgba(255, 255, 255, 0.98);
          border: 1px solid rgba(99, 102, 241, 0.2);
          border-radius: 8px;
          padding: 8px 12px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          font-family: 'Pretendard', sans-serif;
          max-width: 200px;
        ">
          <div class="tooltip-label" style="
            font-weight: 600;
            font-size: 12px;
            color: #374151;
            margin-bottom: 2px;
            line-height: 1.3;
          ">${label}</div>
          <div class="tooltip-value" style="
            font-weight: 500;
            font-size: 11px;
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
  chartInstance_product = new ApexCharts(chartContainer, options);
  chartInstance_product.render();

  console.log("[DEBUG] 주요 상품 매출 비중 차트 렌더링 완료");
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

// ✅ 토글 버튼 이벤트 핸들러
$(document).ready(function() {
  $("#toggleProductSalesRatioChart").on("click", function() {
    const container = $("#productSalesRatioChartContainer");
    const button = $(this);
    
    if (container.is(":visible")) {
      // 차트 숨기기
      container.hide();
      button.text("상위 TOP5 차트 보기");
    } else {
      // 차트 보이기 및 렌더링
      container.show();
      button.text("상위 TOP5 차트 숨기기");
      
      // 차트가 처음 렌더링되는 경우에만 실행
      if (!chartInstance_product) {
        renderProductSalesRatioChart();
      }
    }
  });
});



// 전역 함수로 노출
window.fetchProductSalesRatio = fetchProductSalesRatio;
