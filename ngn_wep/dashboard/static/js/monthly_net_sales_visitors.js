let chartInstance = null;

function fetchMonthlyNetSalesVisitors() {
  const companyName = $("#accountFilter").val() || "all";

  showLoading("#loadingOverlayMonthlyChart");

  $.ajax({
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify({
      company_name: companyName,
      data_type: "monthly_net_sales_visitors"
    }),
    success: function (res) {
      hideLoading("#loadingOverlayMonthlyChart");

      if (res.status === "success" && res.monthly_net_sales_visitors) {
        renderMonthlyNetSalesVisitorsChart(res.monthly_net_sales_visitors);
        renderMonthlySummaryTable(res.monthly_net_sales_visitors);
      } else {
        console.warn("[WARN] 월별 매출/유입 데이터 없음", res);
      }
    },
    error: function (xhr, status, error) {
      hideLoading("#loadingOverlayMonthlyNetSalesVisitors");
      console.error("[ERROR] 월별 매출/유입 서버 오류:", status, error);
    }
  });
}

function renderMonthlyNetSalesVisitorsChart(rawData) {
  // ApexCharts가 로드되었는지 확인
  if (typeof ApexCharts === 'undefined') {
    console.warn('ApexCharts not loaded, retrying in 100ms...');
    setTimeout(() => renderMonthlyNetSalesVisitorsChart(rawData), 100);
    return;
  }

  const uniqueDataMap = {};
  rawData.forEach(item => {
    uniqueDataMap[item.date] = item;
  });
  const data = Object.values(uniqueDataMap).sort((a, b) => a.date.localeCompare(b.date));

  const labels = data.map(d => d.date);
  const netSales = data.map(d => d.net_sales);
  const totalVisitors = data.map(d => d.total_visitors);

  // 기존 차트 인스턴스 제거
  if (chartInstance) {
    chartInstance.destroy();
  }

  // ApexCharts 옵션 설정
  const options = {
    series: [
      {
        name: '매출',
        type: 'column',
        data: netSales,
        color: '#1e293b'
      },
      {
        name: '유입',
        type: 'line',
        data: totalVisitors,
        color: '#f59e0b'
      }
    ],
    chart: {
      height: 500,
      type: 'line',
      fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif',
      toolbar: {
        show: true,
        tools: {
          download: true,
          selection: false,
          zoom: true,
          zoomin: true,
          zoomout: true,
          pan: true,
          reset: true
        }
      },
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
    stroke: {
      width: [0, 4],
      curve: 'smooth'
    },
    plotOptions: {
      bar: {
        columnWidth: '60%',
        borderRadius: 8,
        dataLabels: {
          position: 'top'
        }
      }
    },
    fill: {
      opacity: [0.85, 1],
      gradient: {
        inverseColors: false,
        shade: 'light',
        type: "vertical",
        opacityFrom: 0.85,
        opacityTo: 0.55,
        stops: [0, 100, 100, 100]
      }
    },
    labels: labels,
    markers: {
      size: 6,
      colors: ['#f59e0b'],
      strokeColors: '#ffffff',
      strokeWidth: 2,
      hover: {
        size: 8
      }
    },
    yaxis: [
      {
        title: {
          text: '매출 (원)',
          style: {
            color: '#1e293b',
            fontSize: '14px',
            fontWeight: 600
          }
        },
        labels: {
          formatter: function(val) {
            return val.toLocaleString();
          },
          style: {
            colors: '#1e293b',
            fontSize: '12px'
          }
        }
      },
      {
        opposite: true,
        title: {
          text: '유입 (명)',
          style: {
            color: '#f59e0b',
            fontSize: '14px',
            fontWeight: 600
          }
        },
        labels: {
          formatter: function(val) {
            return val.toLocaleString();
          },
          style: {
            colors: '#f59e0b',
            fontSize: '12px'
          }
        }
      }
    ],
    tooltip: {
      shared: true,
      intersect: false,
      theme: 'light',
      style: {
        fontSize: '14px'
      },
      y: {
        formatter: function(val) {
          return val.toLocaleString();
        }
      }
    },
    legend: {
      position: 'top',
      horizontalAlign: 'center',
      fontSize: '14px',
      fontWeight: 600,
      markers: {
        radius: 6
      },
      itemMargin: {
        horizontal: 20
      }
    },
    grid: {
      borderColor: '#e5e7eb',
      strokeDashArray: 5,
      xaxis: {
        lines: {
          show: true
        }
      },
      yaxis: {
        lines: {
          show: true
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
  chartInstance = new ApexCharts(document.querySelector("#monthlyNetSalesVisitorsChart"), options);
  chartInstance.render();
}

function renderMonthlySummaryTable(rawData) {
  const tbody = $("#monthlySummaryTableBody");
  tbody.empty();

  const uniqueDataMap = {};
  rawData.forEach(item => {
    uniqueDataMap[item.date] = item;
  });

  const data = Object.values(uniqueDataMap).sort((a, b) => b.date.localeCompare(a.date)); // 내림차순

  data.forEach(row => {
    const tr = $("<tr></tr>");
    tr.append(`<td>${row.company_name}</td>`);
    tr.append(`<td>${row.date}</td>`);
    tr.append(`<td>${Number(row.net_sales).toLocaleString()}</td>`);
    tr.append(`<td>${Number(row.total_visitors).toLocaleString()}</td>`);
    tbody.append(tr);
  });
}

// ✅ Batch API용 렌더링 함수
function renderMonthlyNetSalesVisitorsWidget(data) {
  // ✅ UI 렌더링 (전역 변수 없음, 바로 렌더링)
  renderMonthlyNetSalesVisitorsChart(data || []);
  renderMonthlySummaryTable(data || []);

  // ✅ 로딩 스피너 제거
  hideLoading("#loadingOverlayMonthlyChart");
}

// 전역 함수로 노출
window.fetchMonthlyNetSalesVisitors = fetchMonthlyNetSalesVisitors;
