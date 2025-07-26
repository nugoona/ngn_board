// 🔥 ApexCharts 파이 차트 공통 모듈
// 모든 파이 차트에서 일관된 디자인과 기능 제공

// 🔥 ApexCharts 전역 설정 최소화
// 공통 베이스만 남기고 디테일 옵션은 모두 제거

Apex.chart = { 
  fontFamily: 'Pretendard, sans-serif', 
  toolbar: { show: false } 
};

Apex.responsive = [ 
  { 
    breakpoint: 768, 
    options: { 
      chart: { height: 300 } 
    } 
  } 
];

// 🔥 차트 종류별 옵션 분리 함수
function getChartOptions(type = 'default') {
  // 공통 옵션 (모든 차트) - 최소화
  const common = {
    chart: {
      fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
      toolbar: { show: false },
      animations: { enabled: false },
      background: 'transparent',
      dropShadow: { enabled: false }
    },
    responsive: [
      {
        breakpoint: 768,
        options: {
          chart: { height: 300 }
        }
      }
    ]
  };

  // 파이/도넛 차트 전용 옵션
  const pieOnly = (type === 'pie' || type === 'donut') ? {
    plotOptions: {
      pie: {
        startAngle: 0,
        endAngle: 360,
        expandOnClick: true,
        offsetX: 0,
        offsetY: 0,
        customScale: 1,
        dataLabels: {
          enabled: true, // 파이 차트에서만 활성화
          offset: 0,
          minAngleToShowLabel: 10,
          formatter: function (val, opts) {
            const value = opts.w.globals.series[opts.seriesIndex];
            return typeof value === 'number' ? value.toFixed(1) + '%' : '0.0%';
          },
          style: {
            fontSize: '14px',
            fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
            fontWeight: 600,
            colors: ['#ffffff']
          },
          dropShadow: { enabled: false }
        },
        donut: {
          size: '65%',
          background: 'transparent',
          labels: {
            show: false, // 🔥 도넛 차트 중앙 라벨 완전 제거
            value: { show: false }
          }
        }
      }
    },
    legend: {
      show: true,
      fontSize: '14px',
      itemMargin: { vertical: 6 },
      markers: { radius: 6 },
      labels: { colors: '#111' },
      formatter: function (label, opts) {
        const val = opts.w.globals.series[opts.seriesIndex];
        return `${label} ${typeof val === 'number' ? val.toFixed(1) : val}%`;
      }
    },
    tooltip: {
      enabled: true,
      theme: 'light',
      custom: function({ series, seriesIndex, w }) {
        const label = w.globals.labels[seriesIndex];
        const value = series[seriesIndex];
        let salesInfo = '';
        if (w.globals.actualSales && w.globals.actualSales[seriesIndex]) {
          const sales = w.globals.actualSales[seriesIndex];
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
  } : {};

  // 막대/선 차트 전용 옵션
  const barLineOnly = (type === 'bar' || type === 'line') ? {
    plotOptions: {
      bar: {
        dataLabels: {
          enabled: false // 막대 차트에서 기본적으로 비활성화
        }
      }
    },
    legend: {
      show: true,
      fontSize: '14px',
      itemMargin: { vertical: 6 },
      markers: { radius: 6 },
      labels: { colors: '#111' }
    },
    tooltip: {
      enabled: true,
      theme: 'light',
      style: {
        fontSize: '14px',
        fontFamily: 'Pretendard, sans-serif'
      }
    }
  } : {};

  // 🔥 개선된 병합 로직 - 다른 타입에 퍼지지 않도록
  const base = { ...common };
  if (type === 'pie' || type === 'donut') {
    Object.assign(base, pieOnly);
  }
  if (type === 'bar' || type === 'line') {
    Object.assign(base, barLineOnly);
  }
  return base;
}

// 🔥 CSS 스타일 주입
const chartStyles = `
  /* 차트 카드 스타일 */
  .chart-card {
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    padding: 24px;
    margin-bottom: 32px;
    border: 1px solid #f1f5f9;
  }
  
  /* 차트 컨테이너 스타일 */
  .chart-container {
    background: transparent;
    border-radius: 12px;
    padding: 16px;
  }
  
  /* 범례 스타일 */
  .legend-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
  }
  
  .legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'Pretendard', sans-serif;
    font-size: 14px;
    background: transparent !important;
    border-radius: 6px;
    box-shadow: none !important;
    padding: 8px 12px;
    margin: 0;
    transition: background 0.15s;
    border: none !important;
  }
  
  .legend-item:hover {
    background: #f3f4f6 !important;
    box-shadow: none !important;
  }
  
  .legend-marker {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    flex-shrink: 0;
  }
  
  .legend-text {
    flex: 1;
    color: #374151;
    font-weight: 500;
  }
  
  .legend-percentage {
    color: #6366f1;
    font-weight: 600;
    font-size: 13px;
  }
  
  /* ApexCharts 툴팁 스타일 통일 (파이/도넛 차트만) */
  .apexcharts-pie-chart .apexcharts-tooltip {
    background: #fff !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.10) !important;
    border: none !important;
    padding: 12px 16px !important;
    filter: none !important;
  }
  
  .apexcharts-pie-chart .apexcharts-tooltip-title,
  .apexcharts-pie-chart .apexcharts-tooltip-y-group,
  .apexcharts-pie-chart .apexcharts-tooltip-goals-group,
  .apexcharts-pie-chart .apexcharts-tooltip-text {
    display: none !important;
  }

  /* 범례 아이템 flat 스타일 강제 적용 */
  .chart-card .legend-item,
  .legend-container .legend-item,
  .pie-chart-modern .legend-item {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
  }

  .chart-card .legend-item:hover,
  .legend-container .legend-item:hover,
  .pie-chart-modern .legend-item:hover {
    background: #f1f5f9 !important;
    box-shadow: none !important;
  }

  .chart-card .legend-percentage,
  .legend-container .legend-percentage,
  .pie-chart-modern .legend-percentage {
    background: transparent !important;
    box-shadow: none !important;
    border: none !important;
  }
`;

// 스타일 주입 함수
function injectChartStyles() {
  if (!document.getElementById('chart-global-styles')) {
    const styleElement = document.createElement('style');
    styleElement.id = 'chart-global-styles';
    styleElement.textContent = chartStyles;
    document.head.appendChild(styleElement);
    console.log('[DEBUG] 차트 전역 스타일 주입 완료');
  }
}

// DOM 로드 시 스타일 주입
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', injectChartStyles);
} else {
  injectChartStyles();
}

// 🔥 파이 차트 생성 공통 함수
window.createPieChart = function(containerId, data, options = {}) {
  const chartContainer = document.getElementById(containerId);
  if (!chartContainer) {
    console.error(`[ERROR] 차트 컨테이너를 찾을 수 없습니다: ${containerId}`);
    return null;
  }

  const pieOptions = getChartOptions('pie');

  const defaultOptions = {
    chart: {
      type: 'pie',
      height: 350,
      width: '100%',
      ...(pieOptions.chart || {})
    },
    colors: ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'],
    series: Array.isArray(data.series) ? data.series : [],
    labels: Array.isArray(data.labels) ? data.labels : [],
    // ✅ 중첩 옵션은 올바른 키 아래에 배치
    plotOptions: pieOptions.plotOptions || {},
    dataLabels: pieOptions.dataLabels || {},
    legend: pieOptions.legend || {},
    tooltip: pieOptions.tooltip || {},
    responsive: pieOptions.responsive || []
  };

  // 사용자 옵션과 병합 (얕은 병합)
  const finalOptions = { ...defaultOptions, ...options };

  if (data.actualSales) {
    // ApexCharts 자체 옵션에는 globals 키가 없으므로 커스텀 속성으로 지정
    finalOptions.chart = finalOptions.chart || {};
    finalOptions.chart.fore = finalOptions.chart.fore || {};
    finalOptions.chart.fore.actualSales = data.actualSales; // 필요 시 consumer 측에서 사용
  }

  const chartInstance = new ApexCharts(chartContainer, finalOptions);
  chartInstance.render();

  console.log(`[DEBUG] 파이 차트 생성 완료: ${containerId}`);
  return chartInstance;
};

// 🔥 빈 차트 생성 함수
window.createEmptyPieChart = function(containerId) {
  return window.createPieChart(containerId, {
    series: [100],
    labels: ['데이터 없음']
  }, {
    colors: ['#e5e7eb'],
    dataLabels: {
      enabled: false
    },
    tooltip: {
      enabled: false
    }
  });
};

// 🔥 막대 차트 생성 함수 (추가)
window.createBarChart = function(containerId, data, options = {}) {
  const chartContainer = document.getElementById(containerId);
  if (!chartContainer) {
    console.error(`[ERROR] 차트 컨테이너를 찾을 수 없습니다: ${containerId}`);
    return null;
  }

  const barOptions = getChartOptions('bar');
  
  const defaultOptions = {
    chart: {
      type: 'bar',
      height: 350,
      ...barOptions.chart
    },
    colors: ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'],
    series: data.series || [],
    xaxis: data.xaxis || { categories: [] },
    ...barOptions.plotOptions,
    ...barOptions.dataLabels,
    ...barOptions.legend,
    ...barOptions.tooltip,
    ...barOptions.responsive
  };

  const finalOptions = { ...defaultOptions, ...options };
  const chartInstance = new ApexCharts(chartContainer, finalOptions);
  chartInstance.render();
  
  console.log(`[DEBUG] 막대 차트 생성 완료: ${containerId}`);
  return chartInstance;
};

console.log('[DEBUG] 차트 전역 모듈 로드 완료'); 

// ✅ 차트 유틸 로드 완료 이벤트 디스패치
if (typeof window.createPieChart === 'function') {
  document.dispatchEvent(new Event('charts_ready'));
  console.log('[DEBUG] chart_globals.js charts_ready 이벤트 디스패치 완료');
} 