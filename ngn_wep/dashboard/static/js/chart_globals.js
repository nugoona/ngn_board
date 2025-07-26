// 🔥 ApexCharts 파이 차트 공통 모듈
// 모든 파이 차트에서 일관된 디자인과 기능 제공

// 전역 차트 기본 설정
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

// 전역 툴팁 설정 - 심플하고 깔끔한 디자인
Apex.tooltip = {
  theme: 'light',
  style: {
    fontSize: '14px',
    fontFamily: 'Pretendard, sans-serif'
  },
  custom: function({ series, seriesIndex, w }) {
    const label = w.globals.labels[seriesIndex];
    const value = series[seriesIndex];
    
    // 매출 데이터가 있는 경우 (product_sales_ratio 차트용)
    let salesInfo = '';
    if (w.globals.actualSales && w.globals.actualSales[seriesIndex]) {
      const sales = w.globals.actualSales[seriesIndex];
      const formattedSales = typeof sales === 'number' ? sales.toLocaleString() : sales;
      salesInfo = `
        <div style="
          font-weight: 600;
          font-size: 15px;
          color: #6366f1;
          margin-bottom: 4px;
        ">₩${formattedSales}</div>
      `;
    }
    
    return `
      <div style="
        background: #ffffff;
        border: none;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
        font-family: 'Pretendard', sans-serif;
        max-width: 300px;
        font-size: 14px;
      ">
        <div style="
          font-weight: 600;
          font-size: 14px;
          color: #1e293b;
          margin-bottom: 8px;
          line-height: 1.4;
        ">${label}</div>
        ${salesInfo}
        <div style="
          font-weight: 500;
          font-size: 13px;
          color: #64748b;
        ">${typeof value === 'number' ? value.toFixed(1) : '0.0'}%</div>
      </div>
    `;
  }
};

// 전역 플롯 옵션 설정 - 파이 차트 공통
Apex.plotOptions = {
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
        show: false  // 🔥 중심 value 완전히 숨김
      }
    }
  }
};

// 전역 데이터 라벨 설정
Apex.dataLabels = {
  enabled: true,
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
  dropShadow: {
    enabled: false
  }
};

// 전역 범례 설정
Apex.legend = {
  show: false
};

// 전역 반응형 설정
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
  
  /* ApexCharts 툴팁 스타일 통일 */
  .apexcharts-tooltip {
    background: #ffffff !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15) !important;
    border: none !important;
    padding: 0 !important;
  }
  
  .apexcharts-tooltip-title {
    display: none !important;
  }
  
  .apexcharts-tooltip-y-group {
    display: none !important;
  }
  
  .apexcharts-tooltip-goals-group {
    display: none !important;
  }
  
  .apexcharts-tooltip-text {
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

  // 기본 옵션
  const defaultOptions = {
    chart: {
      type: 'pie',
      height: 350,
      fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
      animations: {
        enabled: false
      },
      background: 'transparent',
      dropShadow: {
        enabled: false
      }
    },
    colors: ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'],
    series: data.series || [],
    labels: data.labels || [],
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
            show: false  // 🔥 중심 value 완전히 숨김
          }
        }
      }
    },
    dataLabels: {
      enabled: true,
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
      dropShadow: {
        enabled: false
      }
    },
    legend: {
      show: false
    },
    tooltip: {
      enabled: true,
      theme: 'light',
      style: {
        fontSize: '14px',
        fontFamily: 'Pretendard, sans-serif'
      }
    },
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

  // 사용자 옵션과 병합
  const finalOptions = { ...defaultOptions, ...options };
  
  // 매출 데이터가 있는 경우 전역 변수에 저장
  if (data.actualSales) {
    finalOptions.globals = {
      actualSales: data.actualSales
    };
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

console.log('[DEBUG] 차트 전역 모듈 로드 완료'); 