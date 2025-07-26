// 막대 차트 전용 기본 옵션
export const barDefaults = {
  dataLabels: { 
    enabled: false 
  },
  tooltip: { 
    theme: 'light', 
    y: { 
      formatter: v => v.toLocaleString() 
    } 
  }
}; 