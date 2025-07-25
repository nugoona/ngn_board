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
  
  // ApexCharts가 로드되었는지 확인
  if (typeof ApexCharts === 'undefined') {
    console.warn('ApexCharts not loaded, retrying in 100ms...');
    setTimeout(() => renderPlatformSalesRatioChart(), 100);
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
    
    chartInstance_platform = new ApexCharts(chartContainer, {
      series: [100],
      chart: {
        type: 'pie',
        height: 400,
        fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif'
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
        position: 'right',
        fontSize: '14px',
        fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
        fontWeight: 500
      }
    });
    
    chartInstance_platform.render();
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
  chartInstance_platform = new ApexCharts(chartContainer, options);
  chartInstance_platform.render();

  console.log("[DEBUG] 플랫폼별 매출 요약 차트 렌더링 완료");
}
