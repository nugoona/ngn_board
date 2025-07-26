// 🔥 ApexCharts 전역 스타일 설정
// 모든 파이 차트에서 일관된 디자인 적용

// 🔥 파이 차트 전용 전역 설정 (다른 차트 타입에는 영향 없음)
// 전역 차트 기본 설정은 제거하고 개별 차트에서 설정하도록 변경

// 🔥 파이 차트 전용 툴팁 함수 (전역 설정 대신 함수로 제공)
function getPieChartTooltip() {
  return {
    theme: 'light',
    style: {
      fontSize: '14px',
      fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif'
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
          backdrop-filter: blur(10px);
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
          ">${value.toFixed(1)}%</div>
        </div>
      `;
    }
  };
}

// 🔥 파이 차트 전용 플롯 옵션 함수
function getPieChartPlotOptions() {
  return {
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
  };
}

// 🔥 파이 차트 전용 데이터 라벨 함수
function getPieChartDataLabels() {
  return {
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
      enabled: false
    }
  };
}

// 🔥 파이 차트 전용 반응형 설정 함수
function getPieChartResponsive() {
  return [
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
}

// 🔥 CSS 스타일 주입 (동적으로 추가) - 파이 차트 전용
const apexChartsStyles = `
  /* 파이 차트 전용 툴팁 스타일 리셋 */
  .apexcharts-pie-chart .apexcharts-tooltip {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    padding: 0 !important;
  }
  
  .apexcharts-pie-chart .apexcharts-tooltip-title {
    display: none !important;
  }
  
  .apexcharts-pie-chart .apexcharts-tooltip-y-group {
    display: none !important;
  }
  
  .apexcharts-pie-chart .apexcharts-tooltip-goals-group {
    display: none !important;
  }
  
  .apexcharts-pie-chart .apexcharts-tooltip-text {
    display: none !important;
  }
  
  /* 차트 카드 스타일 */
  .chart-card {
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.05);
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
`;

// 스타일 주입 함수
function injectApexChartsStyles() {
  if (!document.getElementById('apexcharts-global-styles')) {
    const styleElement = document.createElement('style');
    styleElement.id = 'apexcharts-global-styles';
    styleElement.textContent = apexChartsStyles;
    document.head.appendChild(styleElement);
    console.log('[DEBUG] ApexCharts 전역 스타일 주입 완료');
  }
}

// DOM 로드 시 스타일 주입
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', injectApexChartsStyles);
} else {
  injectApexChartsStyles();
}

// 🔥 전역 함수로 노출
window.ApexChartsGlobalStyles = {
  injectStyles: injectApexChartsStyles,
  getPieChartTooltip: getPieChartTooltip,
  getPieChartPlotOptions: getPieChartPlotOptions,
  getPieChartDataLabels: getPieChartDataLabels,
  getPieChartResponsive: getPieChartResponsive,
  getDefaultPieChartOptions: function() {
    return {
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
      plotOptions: getPieChartPlotOptions(),
      dataLabels: getPieChartDataLabels(),
      legend: {
        show: false
      },
      tooltip: getPieChartTooltip(),
      responsive: getPieChartResponsive()
    };
  }
};

console.log('[DEBUG] ApexCharts 전역 스타일 설정 완료'); 