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
  
  // 로딩 오버레이가 있는 경우에만 표시
  const loadingOverlay = $("#loadingOverlayPlatformSalesRatio");
  if (loadingOverlay.length > 0) {
    showLoading("#loadingOverlayPlatformSalesRatio");
  }

  latestAjaxRequest("platform_sales_ratio", {
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(requestData),
    error: function (xhr, status, error) {
      if (loadingOverlay.length > 0) {
        hideLoading("#loadingOverlayPlatformSalesRatio");
      }
      console.error("[ERROR] 플랫폼 매출 비중 오류:", status, error);
    }
  }, function (res) {
    if (loadingOverlay.length > 0) {
      hideLoading("#loadingOverlayPlatformSalesRatio");
    }

    if (res.status === "success") {
      platformSalesRatioData = res.platform_sales_ratio || [];
      renderPlatformSalesRatioChart();
    } else {
      console.warn("[WARN] 플랫폼 매출 비중 응답 없음", res);
    }
  });
}

function renderPlatformSalesRatioChart() {
  const chartDom = document.getElementById('platformSalesRatioChart');
  if (!chartDom) return;
  
  // 기존 차트 인스턴스 제거
  if (window.echartsPlatformSalesRatio) {
    window.echartsPlatformSalesRatio.dispose();
  }

  // 데이터가 없는 경우 빈 차트 표시
  if (!platformSalesRatioData || platformSalesRatioData.length === 0) {
    console.log("[DEBUG] 빈 차트 렌더링");
    const myChart = echarts.init(chartDom, null, {renderer: 'svg'});
    window.echartsPlatformSalesRatio = myChart;
    
    const option = {
      title: {
        text: '플랫폼 상위 TOP5',
        left: 'center',
        top: 20,
        textStyle: {
          fontSize: 22,
          fontWeight: '700',
          fontFamily: 'Pretendard, sans-serif',
          color: '#ffffff'
        },
        backgroundColor: '#1e293b',
        borderRadius: 6,
        padding: [12, 24],
        shadowBlur: 8,
        shadowColor: 'rgba(0, 0, 0, 0.15)',
        shadowOffsetX: 2,
        shadowOffsetY: 2
      },
      series: [{
        type: 'pie',
        radius: ['30%', '55%'],
        center: ['50%', '60%'],
        data: [{ value: 100, name: '데이터 없음' }],
        color: ['#e5e7eb'],
        label: {
          show: false
        }
      }]
    };
    myChart.setOption(option);
    return;
  }

  console.log("[DEBUG] 실제 데이터로 차트 렌더링");
  
  // 데이터 준비 (상위 5개, 0 매출 제외)
  const sortedData = [...platformSalesRatioData]
    .filter(item => (item.total_sales || 0) > 0)
    .sort((a, b) => (b.sales_ratio_percent || b.sales_ratio || 0) - (a.sales_ratio_percent || a.sales_ratio || 0));
  const top5 = sortedData.slice(0, 5);
  
  // 플랫폼명 한글 매핑
  const platformNameMap = {
    'site_official': '자사몰',
    'musinsa': '무신사',
    '29cm': '29cm',
    'shopee': 'SHOPEE',
    'eql': 'EQL',
    'llud': 'LLUD',
    'hana': 'HANA',
    'heights': 'HEIGHTS',
    'zigzag': '지그재그',
    'ably': '에이블리'
  };
  
  // 테이블 데이터에서 실제 퍼센트를 가져와서 사용
  const data = top5.map(item => ({
    value: item.sales_ratio_percent || item.sales_ratio || 0, // 실제 퍼센트 값 사용
    name: platformNameMap[item.platform] || item.platform,
    actualSales: item.total_sales || 0 // 실제 매출액은 별도 저장
  }));

  // ECharts 인스턴스 생성
  const myChart = echarts.init(chartDom, null, {renderer: 'svg'});
  window.echartsPlatformSalesRatio = myChart;

  const option = {
    title: {
      text: '플랫폼 상위 TOP5',
      left: 'center',
      top: 20,
      textStyle: {
        fontSize: 22,
        fontWeight: '700',
        fontFamily: 'Pretendard, sans-serif',
        color: '#ffffff'
      },
      backgroundColor: '#1e293b',
      borderRadius: 6,
      padding: [12, 24],
      shadowBlur: 8,
      shadowColor: 'rgba(0, 0, 0, 0.15)',
      shadowOffsetX: 2,
      shadowOffsetY: 2
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        const actualSales = params.data.actualSales || 0;
        const formattedSales = actualSales.toLocaleString();
        return `${params.name}<br/>₩${formattedSales} (${params.value}%)`;
      }
    },
    graphic: [{
      type: 'line',
      left: 'center',
      top: 70,
      shape: {
        x1: -80,
        y1: 0,
        x2: 80,
        y2: 0
      },
      style: {
        stroke: '#e2e8f0',
        lineWidth: 2,
        shadowBlur: 2,
        shadowColor: 'rgba(0, 0, 0, 0.1)'
      }
    }],
    series: [{
      name: '매출 비중',
      type: 'pie',
      radius: ['30%', '55%'],
      center: ['50%', '60%'],
      roseType: 'area',
      data: data,
      color: ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'],
      label: {
        show: true,
        position: 'outside',
        formatter: function(params) {
          const colors = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'];
          const color = colors[params.dataIndex];
          return `{percentage|${params.value}%}\n{platformName|${params.name}}`;
        },
        fontSize: 14,
        fontFamily: 'Pretendard, sans-serif',
        backgroundColor: '#ffffff',
        borderRadius: 8,
        padding: [8, 12],
        borderColor: '#e2e8f0',
        borderWidth: 1,
        shadowBlur: 10,
        shadowColor: 'rgba(0, 0, 0, 0.1)',
        shadowOffsetX: 2,
        shadowOffsetY: 2,
        rich: {
          percentage: {
            fontSize: 26,
            fontWeight: '800',
            color: function(params) {
              const colors = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'];
              return colors[params.dataIndex];
            },
            padding: [0, 0, 4, 0]
          },
          platformName: {
            fontSize: 20,
            fontWeight: '800',
            color: '#1e293b',
            lineHeight: 20
          }
        }
      },
      labelLine: {
        show: true,
        length: 15,
        length2: 25,
        smooth: true,
        lineStyle: {
          width: 2,
          color: '#cbd5e1',
          shadowBlur: 3,
          shadowColor: 'rgba(0, 0, 0, 0.1)'
        }
      },
      itemStyle: {
        shadowBlur: 8,
        shadowOffsetX: 2,
        shadowOffsetY: 2,
        shadowColor: 'rgba(0, 0, 0, 0.1)'
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 15,
          shadowOffsetX: 4,
          shadowOffsetY: 4,
          shadowColor: 'rgba(0, 0, 0, 0.2)'
        }
      }
    }]
  };
  myChart.setOption(option);
}
