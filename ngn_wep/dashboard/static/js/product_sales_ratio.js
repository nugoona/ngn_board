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
      renderProductSalesRatioTable(1);
      setupPagination_ratio();
      // 차트는 버튼 클릭 시에만 렌더링
    } else {
      console.warn("[WARN] 주요 상품 매출 비중 응답 없음", res);
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
  
  // Chart.js가 로드되었는지 확인
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js not loaded, retrying in 500ms...');
    setTimeout(() => renderProductSalesRatioChart(), 500);
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
    
    const emptyCtx = chartContainer.getContext('2d');
    chartInstance_product = new Chart(emptyCtx, {
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
  
  // 상위 5개 상품만 선택
  const top5Data = allProductSalesRatioData.slice(0, 5);
  const labels = top5Data.map(item => item.product_name || "-");
  const values = top5Data.map(item => item.sales_ratio || 0);
  const actualSales = top5Data.map(item => item.total_sales || 0);
  
  console.log("[DEBUG] 차트 데이터:", { labels, values, actualSales });

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
  
  // Chart.js datalabels 플러그인 등록
  Chart.register(ChartDataLabels);
  
  chartInstance_product = new Chart(ctx, {
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
              const sales = actualSales[context.dataIndex] || 0;
              return [
                `${label}: ${value.toFixed(1)}%`,
                `매출: ₩${sales.toLocaleString()}`
              ];
            }
          }
        }
      },
      animation: {
        animateRotate: true,
        animateScale: true,
        duration: 600,
        easing: 'easeInOutQuart'
      },
      cutout: '60%',
      radius: '90%',
      plugins: {
        datalabels: {
          color: '#ffffff',
          font: {
            weight: 'bold',
            size: 14,
            family: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif'
          },
          formatter: function(value, context) {
            return value.toFixed(1) + '%';
          },
          textAlign: 'center',
          textBaseline: 'middle'
        }
      }
    }
  });

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
