// 🔥 캐시 무효화용 임시 주석 - 2024-01-27
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

let chartInstance_product = null;
let allProductSalesRatioData = [];
let currentPage_product = 1;

function fetchProductSalesRatio() {
  const company = $("#accountFilter").val();
  const period = $("#periodSelector").val();
  const startDate = $("#startDate").val();
  const endDate = $("#endDate").val();

  if (period === "manual" && !endDate) {
    console.warn("[SKIP] 종료일 누락 - 상품 매출 비중 차트 실행 중단");
    return;
  }

  const requestData = getRequestData(1, {
    data_type: "product_sales_ratio"
  });

  console.log("[DEBUG] 상품 매출 비중 요청:", requestData);
  
  // 로딩 오버레이가 있는 경우에만 표시
  const loadingOverlay = $("#loadingOverlayProductSalesRatio");
  if (loadingOverlay.length > 0) {
    showLoading("#loadingOverlayProductSalesRatio");
  }

  latestAjaxRequest("product_sales_ratio", {
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(requestData),
    error: function (xhr, status, error) {
      if (loadingOverlay.length > 0) {
        hideLoading("#loadingOverlayProductSalesRatio");
      }
      console.error("[ERROR] 상품 매출 비중 오류:", status, error);
    }
  }, function (res) {
    if (loadingOverlay.length > 0) {
      hideLoading("#loadingOverlayProductSalesRatio");
    }

    if (res.status === "success") {
      allProductSalesRatioData = res.product_sales_ratio || [];
      console.log("[DEBUG] 상품 매출 비중 데이터 수신:", allProductSalesRatioData);
      renderProductSalesRatioTable(1);
      setupPagination_ratio();
      // 🔥 차트도 함께 업데이트
      renderProductSalesRatioChart();
    } else {
      console.warn("[WARN] 상품 매출 비중 응답 없음", res);
      allProductSalesRatioData = [];
      // 🔥 데이터가 없을 때도 차트 업데이트
      renderProductSalesRatioChart();
    }
  });
}

// 테이블 렌더링 함수 추가
function renderProductSalesRatioTable(page) {
  console.log("[DEBUG] renderProductSalesRatioTable 호출됨");
  
  const tbody = $("#productSalesRatioTableBody");
  if (tbody.length === 0) {
    console.warn("[WARN] productSalesRatioTableBody 요소를 찾을 수 없습니다.");
    return;
  }
  
  tbody.empty();

  if (!allProductSalesRatioData || allProductSalesRatioData.length === 0) {
    tbody.append("<tr><td colspan='6'>데이터가 없습니다.</td></tr>");
    return;
  }

  // 🔥 5개씩 표시로 변경
  const itemsPerPage = 5;
  const start = (page - 1) * itemsPerPage;
  const end = start + itemsPerPage;
  const pageData = allProductSalesRatioData.slice(start, end);

  pageData.forEach(item => {
    const tr = $("<tr></tr>");
    tr.append(`<td>${item.report_period || "-"}</td>`);
    tr.append(`<td>${item.company_name || "-"}</td>`);
    tr.append(`<td>${item.cleaned_product_name || item.product_name || "-"}</td>`);
    tr.append(`<td>${(item.item_quantity || 0).toLocaleString()}</td>`);
    tr.append(`<td>${(item.item_product_sales || 0).toLocaleString()}</td>`);
    tr.append(`<td>${(item.sales_ratio_percent || 0).toFixed(1)}%</td>`);
    tbody.append(tr);
  });
}

// 페이지네이션 설정 - UI 개선
function setupPagination_ratio() {
  // 🔥 5개씩 표시로 변경
  const itemsPerPage = 5;
  const totalPages = Math.ceil(allProductSalesRatioData.length / itemsPerPage);
  
  const paginationContainer = $("#pagination_product_sales_ratio");
  if (paginationContainer.length === 0) {
    console.warn("[WARN] pagination_product_sales_ratio 요소를 찾을 수 없습니다.");
    return;
  }
  
  paginationContainer.empty();
  
  if (totalPages <= 1) return;
  
  // 이전/다음 버튼 스타일
  const prevBtn = $(`<button class="pagination-btn">이전</button>`);
  const nextBtn = $(`<button class="pagination-btn">다음</button>`);

  if (currentPage_product === 1) {
    prevBtn.prop("disabled", true).addClass("disabled");
  } else {
    prevBtn.click(() => {
      currentPage_product--;
      renderProductSalesRatioTable(currentPage_product);
      setupPagination_ratio();
    });
  }

  if (currentPage_product === totalPages) {
    nextBtn.prop("disabled", true).addClass("disabled");
  } else {
    nextBtn.click(() => {
      currentPage_product++;
      renderProductSalesRatioTable(currentPage_product);
      setupPagination_ratio();
    });
  }

  paginationContainer.append(prevBtn);
  paginationContainer.append(`<span class="pagination-info">${currentPage_product} / ${totalPages}</span>`);
  paginationContainer.append(nextBtn);
  
  console.log("[DEBUG] 페이지네이션 생성 완료:", {
    totalItems: allProductSalesRatioData.length,
    totalPages: totalPages,
    currentPage: currentPage_product,
    itemsPerPage: itemsPerPage
  });
}

function changePage_ratio(page) {
  currentPage_product = page;
  renderProductSalesRatioTable(page);
  setupPagination_ratio();
}

function renderProductSalesRatioChart() {
  console.log("[DEBUG] renderProductSalesRatioChart 호출됨");
  
  // DOM이 준비되었는지 확인
  const chartContainer = document.getElementById("productSalesRatioChart");
  const legendContainer = document.getElementById("productLegendItems");
  
  console.log("[DEBUG] 차트 컨테이너:", chartContainer);
  console.log("[DEBUG] 차트 컨테이너 스타일:", chartContainer ? {
    display: chartContainer.style.display,
    height: chartContainer.style.height,
    width: chartContainer.style.width,
    visibility: chartContainer.style.visibility
  } : "컨테이너 없음");

  if (!chartContainer) {
    console.error("[ERROR] productSalesRatioChart 컨테이너를 찾을 수 없습니다!");
    // DOM이 아직 준비되지 않았을 수 있으므로 재시도
    setTimeout(() => renderProductSalesRatioChart(), 100);
    return;
  }

  // ApexCharts가 로드되었는지 확인
  if (typeof ApexCharts === 'undefined') {
    console.warn('ApexCharts not loaded, retrying in 100ms...');
    setTimeout(() => renderProductSalesRatioChart(), 100);
    return;
  }

  // 기존 차트 인스턴스 제거
  if (chartInstance_product && typeof chartInstance_product.destroy === 'function') {
    chartInstance_product.destroy();
  }

  // 데이터가 없거나 총 매출이 0인 경우 빈 차트 표시
  if (!allProductSalesRatioData || allProductSalesRatioData.length === 0) {
    console.log("[DEBUG] 빈 차트 렌더링");
    
    // 빈 범례 표시
    if (legendContainer) {
      legendContainer.innerHTML = '<div class="legend-item"><div class="legend-text">데이터가 없습니다</div></div>';
    }
    
    // 빈 파이 차트 생성
    chartInstance_product = new ApexCharts(document.getElementById("productSalesRatioChart"), {
      chart: {
        type: 'pie',
        height: 350
      },
      series: [100],
      labels: ['데이터 없음'],
      colors: ['#e2e8f0'],
      dataLabels: {
        enabled: false
      },
      tooltip: {
        enabled: false
      }
    });
    chartInstance_product.render();
    console.log("[DEBUG] 빈 차트 렌더링 완료");
    return;
  }

  console.log("[DEBUG] 실제 데이터로 차트 렌더링");
  console.log("[DEBUG] 전체 데이터 개수:", allProductSalesRatioData.length);
  
  // 🔥 상위 5개 상품만 선택 (매출 비중 기준으로 정렬)
  const sortedData = [...allProductSalesRatioData].sort((a, b) => {
    const ratioA = a.sales_ratio_percent || a.sales_ratio || 0;
    const ratioB = b.sales_ratio_percent || b.sales_ratio || 0;
    return ratioB - ratioA; // 내림차순 정렬
  });
  
  const top5Data = sortedData.slice(0, 5);
  const labels = top5Data.map(item => item.cleaned_product_name || item.product_name || "-");
  const values = top5Data.map(item => item.sales_ratio_percent || item.sales_ratio || 0);
  const actualSales = top5Data.map(item => item.item_product_sales || item.total_sales || 0);
  const colors = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'];
  
  console.log("[DEBUG] 상위 5개 데이터:", top5Data);
  console.log("[DEBUG] 차트 데이터:", { labels, values, actualSales });

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

  // 파이 차트 생성
  console.log("[DEBUG] createPieChart 호출 전 - series:", values, "labels:", labels);
  
  chartInstance_product = new ApexCharts(document.getElementById("productSalesRatioChart"), {
    chart: {
      type: 'pie',
      height: 350
    },
    series: values,
    labels: labels,
    colors: colors,
    dataLabels: {
      enabled: true,
      formatter: function(val) {
        return val.toFixed(1) + '%';
      }
    },
    tooltip: {
      theme: 'light',
      custom: function({ series, seriesIndex, w }) {
        const label = w.globals.labels[seriesIndex];
        const value = series[seriesIndex];
        let salesInfo = '';
        if (actualSales && actualSales[seriesIndex]) {
          const sales = actualSales[seriesIndex];
          const formattedSales = typeof sales === 'number' ? sales.toLocaleString() : sales;
          salesInfo = `<div style="font-weight:600;font-size:15px;color:#6366f1;margin-bottom:4px;">₩${formattedSales}</div>`;
        }
        return `<div style="background:#fff;border-radius:12px;padding:12px 16px;box-shadow:0 4px 16px rgba(0,0,0,0.10);font-family:'Pretendard',sans-serif;max-width:300px;font-size:14px;">
          <div style="font-weight:600;font-size:14px;color:#1e293b;margin-bottom:8px;line-height:1.4;">${label}</div>
          ${salesInfo}
          <div style="font-weight:500;font-size:13px;color:#64748b;">${typeof value === 'number' ? value.toFixed(1) : '0.0'}%</div>
        </div>`;
      }
    }
  });
  chartInstance_product.render();

  console.log("[DEBUG] createPieChart 호출 후 - chartInstance:", chartInstance_product);
  console.log("[DEBUG] 상품 매출 비중 차트 렌더링 완료");
}

// 토글 버튼 이벤트
$(document).ready(function() {
  $("#toggleProductSalesRatioChart").on("click", function() {
    const $container = $("#productSalesRatioChartContainer");
    const isVisible = $container.is(":visible");
    console.log("[DEBUG] 토글 버튼 클릭 - 현재 상태:", isVisible);
    
    $container.toggle();
    $(this).text(isVisible ? "상위 TOP5 차트 보기" : "상위 TOP5 차트 숨기기");
    
    if (!isVisible) {
      console.log("[DEBUG] 차트 표시 - 렌더링 시작");
      // DOM이 완전히 표시된 후 차트 렌더링
      setTimeout(() => {
        renderProductSalesRatioChart();
      }, 100);
    }
  });
});



// 전역 함수로 노출
window.fetchProductSalesRatio = fetchProductSalesRatio;
