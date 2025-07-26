// 파이 차트 전용 기본 옵션
export const pieDefaults = {
  plotOptions: {
    pie: { 
      donut: { 
        labels: { 
          value: { show: false } 
        } 
      } 
    }
  },
  dataLabels: {
    enabled: true,
    formatter: v => v.toFixed(1) + '%'
  },
  tooltip: { 
    theme: 'light', 
    custom: pieTooltip 
  }
};

// 파이 차트 커스텀 툴팁 함수
function pieTooltip({ series, seriesIndex, w }) {
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