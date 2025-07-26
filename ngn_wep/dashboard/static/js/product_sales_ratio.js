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

// ECharts 파이 차트 렌더링
function renderProductSalesRatioChart() {
  const chartDom = document.getElementById('productSalesRatioChart');
  if (!chartDom) return;
  // 기존 차트 인스턴스 제거
  if (window.echartsProductSalesRatio) {
    window.echartsProductSalesRatio.dispose();
  }

  // 데이터 준비 (상위 5개, 0 매출 제외)
  const sortedData = [...allProductSalesRatioData]
    .filter(item => (item.item_product_sales || item.total_sales || 0) > 0)
    .sort((a, b) => (b.item_product_sales || b.total_sales || 0) - (a.item_product_sales || a.total_sales || 0));
  const top5 = sortedData.slice(0, 5);
  const data = top5.map(item => ({
    value: item.item_product_sales || item.total_sales || 0,
    name: item.cleaned_product_name || item.product_name || '-'
  }));

  // ECharts 인스턴스 생성
  const myChart = echarts.init(chartDom, null, {renderer: 'svg'});
  window.echartsProductSalesRatio = myChart;

  const option = {
    color: ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'],
    series: [{
      type: 'pie',
      radius: ['55%', '80%'],
      avoidLabelOverlap: false,
      label: {
        show: true,
        position: 'outside',
        formatter: function(params) {
          // {b}: 상품명, {d}: 퍼센트, {c}: 매출액
          return `${params.name}\n${params.percent}%`;
        },
        fontSize: 15,
        fontFamily: 'Pretendard, sans-serif',
        color: '#222',
        alignTo: 'edge',
        bleedMargin: 10
      },
      labelLine: {
        show: true,
        length: 20,
        length2: 30,
        smooth: true
      },
      data: data
    }],
    tooltip: { show: false },
    animation: true
  };
  myChart.setOption(option);
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
