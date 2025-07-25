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
  // ApexCharts가 로드되었는지 확인
  if (typeof ApexCharts === 'undefined') {
    console.warn('ApexCharts not loaded, retrying in 100ms...');
    setTimeout(renderPlatformSalesRatioChart, 100);
    return;
  }

  const top5 = [...platformSalesRatioData]
    .sort((a, b) => b.sales - a.sales)
    .slice(0, 5);

  // ✅ 플랫폼명 한글 매핑
  const labels = top5.map(item => {
    switch (item.platform) {
      case "site_official": return "자사몰";
      case "musinsa": return "무신사";
      default: return item.platform;
    }
  });
  const values = top5.map(item => item.sales_ratio_percent);
  const actualSales = top5.map(item => item.sales);  // ✅ 실제 매출

  // 기존 차트 인스턴스 제거
  if (chartInstance_platform) chartInstance_platform.destroy();

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
          const sales = actualSales[seriesIndex] || 0;
          return `${labels[seriesIndex]}: ₩${sales.toLocaleString()} (${value.toFixed(1)}%)`;
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
  chartInstance_platform = new ApexCharts(document.querySelector("#platformSalesRatioChart"), options);
  chartInstance_platform.render();
}
