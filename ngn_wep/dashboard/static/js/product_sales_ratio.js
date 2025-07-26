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
    } else {
      console.warn("[WARN] 상품 매출 비중 응답 없음", res);
      allProductSalesRatioData = [];
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

  // 🔥 10개씩 표시로 변경
  const itemsPerPage = 10;
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
  // 🔥 10개씩 표시로 변경
  const itemsPerPage = 10;
  const totalPages = Math.ceil(allProductSalesRatioData.length / itemsPerPage);
  
  const paginationContainer = $("#pagination_product_sales_ratio");
  if (paginationContainer.length === 0) {
    console.warn("[WARN] pagination_product_sales_ratio 요소를 찾을 수 없습니다.");
    return;
  }
  
  paginationContainer.empty();
  
  if (totalPages <= 1) return;
  
  // 🔥 페이지네이션 UI 개선 - 깔끔한 스타일
  const paginationHtml = `
    <div class="pagination-wrapper" style="
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      margin-top: 20px;
      font-family: 'Pretendard', sans-serif;
    ">
  `;
  
  // 이전 버튼
  if (currentPage_product > 1) {
    paginationHtml += `
      <button class="pagination-btn" onclick="changePage_ratio(${currentPage_product - 1})" style="
        padding: 8px 12px;
        border: 1px solid #e2e8f0;
        background: #ffffff;
        color: #475569;
        border-radius: 6px;
        cursor: pointer;
        font-size: 14px;
        transition: all 0.2s;
      " onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='#ffffff'">
        이전
      </button>
    `;
  }
  
  // 페이지 번호 - 최대 5개까지만 표시
  const maxVisiblePages = 5;
  let startPage = Math.max(1, currentPage_product - Math.floor(maxVisiblePages / 2));
  let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
  
  if (endPage - startPage + 1 < maxVisiblePages) {
    startPage = Math.max(1, endPage - maxVisiblePages + 1);
  }
  
  for (let i = startPage; i <= endPage; i++) {
    const isActive = i === currentPage_product;
    const btnStyle = isActive ? `
      background: #6366f1;
      color: #ffffff;
      border: 1px solid #6366f1;
    ` : `
      background: #ffffff;
      color: #475569;
      border: 1px solid #e2e8f0;
    `;
    
    paginationHtml += `
      <button class="pagination-btn ${isActive ? 'active' : ''}" onclick="changePage_ratio(${i})" style="
        padding: 8px 12px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 14px;
        font-weight: ${isActive ? '600' : '400'};
        transition: all 0.2s;
        min-width: 40px;
        ${btnStyle}
      " onmouseover="${!isActive ? `this.style.background='#f8fafc'` : ''}" onmouseout="${!isActive ? `this.style.background='#ffffff'` : ''}">
        ${i}
      </button>
    `;
  }
  
  // 다음 버튼
  if (currentPage_product < totalPages) {
    paginationHtml += `
      <button class="pagination-btn" onclick="changePage_ratio(${currentPage_product + 1})" style="
        padding: 8px 12px;
        border: 1px solid #e2e8f0;
        background: #ffffff;
        color: #475569;
        border-radius: 6px;
        cursor: pointer;
        font-size: 14px;
        transition: all 0.2s;
      " onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='#ffffff'">
        다음
      </button>
    `;
  }
  
  paginationHtml += `
    </div>
    <div style="
      text-align: center;
      margin-top: 8px;
      font-size: 13px;
      color: #64748b;
      font-family: 'Pretendard', sans-serif;
    ">
      ${allProductSalesRatioData.length}개 중 ${(currentPage_product - 1) * itemsPerPage + 1}-${Math.min(currentPage_product * itemsPerPage, allProductSalesRatioData.length)}개 표시
    </div>
  `;
  
  paginationContainer.html(paginationHtml);
}

// 전역 변수로 currentPage_product 선언 (한 번만)
let currentPage_product = 1;

function changePage_ratio(page) {
  currentPage_product = page;
  renderProductSalesRatioTable(page);
  setupPagination_ratio();
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
  const legendContainer = document.getElementById("productLegendItems");
  
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
    
    // 빈 범례 표시
    if (legendContainer) {
      legendContainer.innerHTML = '<div class="legend-item"><div class="legend-text">데이터가 없습니다</div></div>';
    }
    
    chartInstance_product = new ApexCharts(chartContainer, {
      series: [100],
      chart: {
        type: 'pie',
        height: 350,
        fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
        animations: {
          enabled: false
        },
        // 🔥 배경 투명하게 설정
        background: 'transparent',
        dropShadow: {
          enabled: false
        }
      },
      labels: ['데이터 없음'],
      colors: ['#e5e7eb'],
      plotOptions: {
        pie: {
          donut: {
            size: '65%',
            // 🔥 도넛 배경을 완전히 투명하게
            background: 'transparent'
          }
        }
      },
      legend: {
        show: false
      },
      dataLabels: {
        enabled: false
      },
      // 🔥 Flat하고 깔끔한 툴팁 디자인
      tooltip: {
        enabled: false
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
  const colors = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'];
  
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

  // 🔥 ApexCharts 옵션 설정 - Flat하고 깔끔한 디자인으로 개선
  const options = {
    series: values,
    chart: {
      type: 'pie',
      height: 350,
      fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
      animations: {
        enabled: false
      },
      // 🔥 배경 투명하게 설정
      background: 'transparent',
      dropShadow: {
        enabled: false
      }
    },
    labels: labels,
    colors: colors,
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
          // 🔥 도넛 배경을 완전히 투명하게
          background: 'transparent',
          labels: {
            show: true,
            name: {
              show: false
            },
            value: {
              show: true,
              fontSize: '16px',
              fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
              fontWeight: 700,
              color: '#1e293b',
              offsetY: 0,
              formatter: function (val) {
                return typeof val === 'number' ? val.toFixed(1) + '%' : '0.0%';
              }
            },
            total: {
              show: false
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
      // 🔥 그림자 효과 제거하여 flat하게
      dropShadow: {
        enabled: false
      }
    },
    legend: {
      show: false
    },
    // 🔥 Flat하고 깔끔한 툴팁 디자인
    tooltip: {
      enabled: true,
      theme: 'light',
      style: {
        fontSize: '14px',
        fontFamily: 'Pretendard, sans-serif'
      },
      custom: function({ series, seriesIndex, dataPointIndex, w }) {
        const sales = actualSales[seriesIndex] || 0;
        const percentage = series[seriesIndex];
        const label = labels[seriesIndex];
        const formattedSales = typeof sales === 'number' ? sales.toLocaleString() : sales;
        return `<div style="
          background: #ffffff;
          border: none;
          border-radius: 8px;
          padding: 12px 16px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
          font-family: 'Pretendard', sans-serif;
          max-width: 280px;
          font-size: 14px;
        ">
          <div style="
            font-weight: 600;
            font-size: 14px;
            color: #1e293b;
            margin-bottom: 6px;
            line-height: 1.4;
          ">${label}</div>
          <div style="
            font-weight: 600;
            font-size: 15px;
            color: #6366f1;
            margin-bottom: 4px;
          ">₩${formattedSales}</div>
          <div style="
            font-weight: 500;
            font-size: 13px;
            color: #64748b;
          ">${percentage.toFixed(1)}%</div>
        </div>`;
      }
    },
    // 🔥 반응형 설정 개선
    responsive: [
      {
        breakpoint: 768,
        options: {
          chart: {
            height: 300
          },
          dataLabels: {
            fontSize: '12px'
          }
        }
      }
    ]
  };

  // ApexCharts 인스턴스 생성
  chartInstance_product = new ApexCharts(chartContainer, options);
  chartInstance_product.render();

  console.log("[DEBUG] 상품 매출 비중 차트 렌더링 완료");
}

// 토글 버튼 이벤트
$(document).ready(function() {
  $("#toggleProductSalesRatioChart").on("click", function() {
    const $container = $("#productSalesRatioChartContainer");
    const isVisible = $container.is(":visible");
    $container.toggle();
    $(this).text(isVisible ? "상위 TOP5 차트 보기" : "상위 TOP5 차트 숨기기");
    if (!isVisible) {
      renderProductSalesRatioChart();
    }
  });
});



// 전역 함수로 노출
window.fetchProductSalesRatio = fetchProductSalesRatio;
