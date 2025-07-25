let chartInstance_platform = null;
let platformSalesRatioData = [];

function fetchPlatformSalesRatio() {
  const company = $("#accountFilter").val(); 
  const period = $("#periodSelector").val();
  const startDate = $("#startDate").val();
  const endDate = $("#endDate").val();

  if (period === "manual" && !endDate) {
    console.warn("[SKIP] 종료일 누락 - 플랫폼 매출 비중 차트 실행 중단");
    return;
  }

  const requestData = getRequestData(1, {
    data_type: "platform_sales_ratio"
  });


  console.log("[DEBUG] 플랫폼 매출 비중 요청:", requestData);
  showLoading("#loadingOverlayPlatformSalesRatio");

  latestAjaxRequest("platform_sales_ratio", {
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(requestData),
    error: function (xhr, status, error) {
      hideLoading("#loadingOverlayPlatformSalesRatio");
      console.error("[ERROR] 플랫폼 매출 비중 오류:", status, error);
    }
  }, function (res) {
    hideLoading("#loadingOverlayPlatformSalesRatio");

    if (res.status === "success") {
      platformSalesRatioData = res.platform_sales_ratio || [];
      renderPlatformSalesRatioChart();
    } else {
      console.warn("[WARN] 플랫폼 매출 비중 응답 없음", res);
    }
  });
}

function renderPlatformSalesRatioChart() {
  console.log("[DEBUG] renderPlatformSalesRatioChart 호출됨");
  
  // Chart.js가 로드되었는지 확인
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js not loaded, retrying in 500ms...');
    setTimeout(() => renderPlatformSalesRatioChart(), 500);
    return;
  }

  const chartContainer = document.getElementById("platformSalesRatioChart");
  console.log("[DEBUG] 차트 컨테이너:", chartContainer);

  if (!chartContainer) {
    console.error("[ERROR] platformSalesRatioChart 컨테이너를 찾을 수 없습니다!");
    return;
  }

  // 기존 차트 인스턴스 제거
  if (chartInstance_platform) {
    chartInstance_platform.destroy();
  }

  // 데이터가 없거나 총 매출이 0인 경우 빈 차트 표시
  if (!platformSalesRatioData || platformSalesRatioData.length === 0) {
    console.log("[DEBUG] 빈 차트 렌더링");
    
    const emptyCtx = chartContainer.getContext('2d');
    chartInstance_platform = new Chart(emptyCtx, {
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
  
  const top5 = [...platformSalesRatioData]
    .sort((a, b) => b.total_sales - a.total_sales)
    .slice(0, 5);

  console.log("[DEBUG] 플랫폼 매출 비중 top5 데이터:", top5);

  // ✅ 플랫폼명 한글 매핑
  const labels = top5.map(item => {
    switch (item.platform) {
      case "site_official": return "자사몰";
      case "musinsa": return "무신사";
      default: return item.platform;
    }
  });
  const values = top5.map(item => item.sales_ratio_percent);
  const actualSales = top5.map(item => item.total_sales);

  console.log("[DEBUG] 플랫폼 매출 비중 차트 데이터:", { labels, values, actualSales });

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
  chartInstance_platform = new Chart(ctx, {
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

  console.log("[DEBUG] 플랫폼별 매출 요약 차트 렌더링 완료");
}
