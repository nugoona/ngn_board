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

// 🔥 파이 차트 생성 공통 함수
window.createPieChart = async function(containerId, data, options = {}) {
  const chartContainer = document.getElementById(containerId);
  if (!chartContainer) {
    console.error(`[ERROR] 차트 컨테이너를 찾을 수 없습니다: ${containerId}`);
    return null;
  }

  try {
    const { pieDefaults } = await import('./chart_pie_defaults.js');
    
    const defaultOptions = {
      chart: {
        type: 'pie',
        height: 350,
        width: '100%'
      },
      colors: ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'],
      series: Array.isArray(data.series) ? data.series : [],
      labels: Array.isArray(data.labels) ? data.labels : []
    };

    const finalOptions = { ...defaultOptions, ...pieDefaults, ...options };
    
    // actualSales 데이터가 있으면 globals에 저장
    if (data.actualSales) {
      finalOptions.globals = { actualSales: data.actualSales };
    }
    
    const chartInstance = new ApexCharts(chartContainer, finalOptions);
    chartInstance.render();

    console.log(`[DEBUG] 파이 차트 생성 완료: ${containerId}`);
    return chartInstance;
  } catch (error) {
    console.error('[ERROR] 파이 차트 생성 실패:', error);
    return null;
  }
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

// 🔥 막대 차트 생성 함수
window.createBarChart = async function(containerId, data, options = {}) {
  const chartContainer = document.getElementById(containerId);
  if (!chartContainer) {
    console.error(`[ERROR] 차트 컨테이너를 찾을 수 없습니다: ${containerId}`);
    return null;
  }

  try {
    const { barDefaults } = await import('./chart_bar_defaults.js');
    
    const defaultOptions = {
      chart: {
        type: 'bar',
        height: 350
      },
      colors: ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'],
      series: data.series || [],
      xaxis: data.xaxis || { categories: [] }
    };

    const finalOptions = { ...defaultOptions, ...barDefaults, ...options };
    const chartInstance = new ApexCharts(chartContainer, finalOptions);
    chartInstance.render();

    console.log(`[DEBUG] 막대 차트 생성 완료: ${containerId}`);
    return chartInstance;
  } catch (error) {
    console.error('[ERROR] 막대 차트 생성 실패:', error);
    return null;
  }
};

// ✅ 차트 유틸 로드 완료 이벤트 디스패치
if (typeof window.createPieChart === 'function') {
  document.dispatchEvent(new Event('charts_ready'));
  console.log('[DEBUG] chart_globals.js charts_ready 이벤트 디스패치 완료');
} 