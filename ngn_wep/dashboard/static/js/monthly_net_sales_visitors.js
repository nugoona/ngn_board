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
  const uniqueDataMap = {};
  rawData.forEach(item => {
    uniqueDataMap[item.date] = item;
  });
  const data = Object.values(uniqueDataMap).sort((a, b) => a.date.localeCompare(b.date));

  const labels = data.map(d => d.date);
  const netSales = data.map(d => d.net_sales);
  const totalVisitors = data.map(d => d.total_visitors);

  const ctx = document.getElementById("monthlyNetSalesVisitorsChart").getContext("2d");

  if (chartInstance) {
    chartInstance.destroy();
  }

  chartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "매출",
          data: netSales,
          backgroundColor: "rgba(54, 162, 235, 0.6)",
          yAxisID: "y",
          barPercentage: 0.8
        },
        {
          label: "유입",
          data: totalVisitors,
          backgroundColor: "rgba(255, 206, 86, 0.6)",
          yAxisID: "y1",
          barPercentage: 0.8
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "top",
          labels: {
            font: { size: 14 }
          },
          onClick: (e, legendItem, legend) => {
            const index = legendItem.datasetIndex;
            const ci = legend.chart;
            const clicked = ci.data.datasets[index];
            const isOnlyVisible = ci.data.datasets.filter(ds => !ds.hidden).length === 1;

            if (!clicked.hidden && isOnlyVisible) {
              // 모두 보이게
              ci.data.datasets.forEach(ds => ds.hidden = false);
            } else {
              // 클릭한 것만 보이게
              ci.data.datasets.forEach((ds, i) => {
                ds.hidden = i !== index;
              });
            }
            ci.update();
          }
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const value = context.raw || 0;
              return `${context.dataset.label}: ${value.toLocaleString()}`;
            }
          }
        }
      },
      scales: {
        y: {
          title: { display: false },
          position: "left",
          ticks: {
            callback: (value) => value.toLocaleString()
          }
        },
        y1: {
          title: { display: false },
          position: "right",
          grid: { drawOnChartArea: false },
          ticks: {
            callback: (value) => value.toLocaleString()
          }
        }
      }
    }
  });
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
