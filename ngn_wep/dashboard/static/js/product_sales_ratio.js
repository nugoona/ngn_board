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
  
  // 날짜 정보가 없으면 오늘 날짜로 설정
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
      renderProductSalesRatioChart();
      setupPagination_ratio();
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
  const top5 = [...allProductSalesRatioData]
    .sort((a, b) => b.sales_ratio_percent - a.sales_ratio_percent)
    .slice(0, 5);

  const labels = top5.map(d => d.cleaned_product_name);
  const values = top5.map(d => d.sales_ratio_percent);
  const actualSales = top5.map(d => d.item_product_sales);

  // ✅ 기존 캔버스 제거 후 새로 생성
  $("#productSalesRatioChart").replaceWith('<canvas id="productSalesRatioChart"></canvas>');
  const canvas = document.getElementById("productSalesRatioChart");
  const ctx = canvas.getContext("2d");

  if (chartInstance_ratio) {
    chartInstance_ratio.destroy();
  }

  chartInstance_ratio = new Chart(ctx, {
    type: "pie",
    data: {
      labels,
      datasets: [{
        label: "매출 비중",
        data: values,
        backgroundColor: [
          "#36A2EB", "#FF6384", "#FFB347", "#FFD700", "#20B2AA"
        ]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: {
        padding: { top: 30, bottom: 35, left: 70, right: 50 }
      },
      animation: {
        animateRotate: true,
        animateScale: true,
        duration: 1000,
        easing: 'easeOutCubic'
      },
      plugins: {
        legend: {
          position: "right",
          labels: {
            boxWidth: 20,
            font: { size: 18 },
            padding: 20
          }
        },
        tooltip: {
          bodyFont: { size: 18 },
          callbacks: {
            label: function (ctx) {
              const idx = ctx.dataIndex;
              const sales = actualSales[idx] || 0;
              return `${labels[idx]}: ₩${sales.toLocaleString()}`;
            }
          }
        },
        datalabels: {
          formatter: (value) => `${value.toFixed(1)}%`,
          color: "#000",
          font: { weight: "bold", size: 18 },
          anchor: "end",
          align: "end",
          offset: 12,
          clamp: true
        }
      }
    },
    plugins: [ChartDataLabels]
  });
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

// ✅ 토글 버튼 제어
$("#toggleProductSalesRatioChart").on("click", function () {
  const chartContainer = $("#productSalesRatioChartContainer");
  const isVisible = chartContainer.is(":visible");

  chartContainer.toggle();
  $(this).text(isVisible ? "상위 TOP5 차트 보기" : "상위 TOP5 차트 숨기기");

  if (!isVisible) {
    setTimeout(() => renderProductSalesRatioChart(), 10);
  }
});
