// 🔥 ApexCharts 파이 차트 공통 모듈
// 모든 파이 차트에서 일관된 디자인과 기능 제공

// 전역 차트 기본 설정 (모든 차트 공통)
Apex.chart = {
  fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
  toolbar: { 
    show: false 
  },
  animations: {
    enabled: false
  },
  background: 'transparent',
  dropShadow: {
    enabled: false
  }
};

// 전역 데이터 라벨 설정 (모든 차트 공통)
Apex.dataLabels = {
  enabled: true,
  style: {
    fontSize: '14px',
    fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
    fontWeight: 600,
    colors: ['#ffffff']
  },
  dropShadow: {
    enabled: false
  }
};

// 전역 반응형 설정 (모든 차트 공통)
Apex.responsive = [
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
];

// 🔥 차트 종류별 옵션 분리 함수
export function getChartOptions(type = 'default') {
  // 공통 옵션 (모든 차트)
  const common = {
    chart: {
      fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
      toolbar: { show: false },
      animations: { enabled: false },
      background: 'transparent',
      dropShadow: { enabled: false }
    },
    dataLabels: {
      enabled: true,
      style: {
        fontSize: '14px',
        fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
        fontWeight: 600,
        colors: ['#ffffff']
      },
      dropShadow: { enabled: false }
    },
    responsive: [
      {
        breakpoint: 768,
        options: {
          chart: { height: 300 },
          dataLabels: { fontSize: '12px' }
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
          offset: 0,
          minAngleToShowLabel: 10,
          formatter: function (val, opts) {
            const value = opts.w.globals.series[opts.seriesIndex];
            return typeof value === 'number' ? value.toFixed(1) + '%' : '0.0%';
          }
        },
        donut: {
          size: '65%',
          background: 'transparent',
          labels: {
            show: true,
            value: { show: false } // 🔥 중심 value 완전 제거
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
          formatter: function (val, opts) {
            return typeof val === 'number' ? val.toLocaleString() : val;
          }
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

  return { ...common, ...pieOnly, ...barLineOnly };
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
    background: transparent;
    border-radius: 6px;
    box-shadow: none;
    padding: 0;
    margin: 0;
    transition: background 0.15s;
  }
  
  .legend-item:hover {
    background: #f3f4f6;
    box-shadow: none;
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

  // 파이 차트 전용 옵션 가져오기
  const pieOptions = getChartOptions('pie');
  
  // 기본 옵션
  const defaultOptions = {
    chart: {
      type: 'pie',
      height: 350,
      ...pieOptions.chart
    },
    colors: ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'],
    series: data.series || [],
    labels: data.labels || [],
    ...pieOptions.plotOptions,
    ...pieOptions.dataLabels,
    ...pieOptions.legend,
    ...pieOptions.tooltip,
    ...pieOptions.responsive
  };

  // 사용자 옵션과 병합
  const finalOptions = { ...defaultOptions, ...options };
  
  // 매출 데이터가 있는 경우 전역 변수에 저장
  if (data.actualSales) {
    finalOptions.globals = { actualSales: data.actualSales };
  }

  // 차트 인스턴스 생성
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