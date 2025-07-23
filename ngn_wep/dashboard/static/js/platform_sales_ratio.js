let chartInstance_platform = null;
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
  showLoading("#loadingOverlayPlatformSalesRatio");

  latestAjaxRequest("platform_sales_ratio", {
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(requestData),
    error: function (xhr, status, error) {
      hideLoading("#loadingOverlayPlatformSalesRatio");
      console.error("[ERROR] 플랫폼 매출 비중 오류:", status, error);
    }
  }, function (res) {
    hideLoading("#loadingOverlayPlatformSalesRatio");

    if (res.status === "success") {
      platformSalesRatioData = res.platform_sales_ratio || [];
      renderPlatformSalesRatioChart();
    } else {
      console.warn("[WARN] 플랫폼 매출 비중 응답 없음", res);
    }
  });
}

function renderPlatformSalesRatioChart() {
  const top5 = [...platformSalesRatioData]
    .sort((a, b) => b.sales - a.sales)
    .slice(0, 5);

  // ✅ 플랫폼명 한글 매핑
  const labels = top5.map(item => {
    switch (item.platform) {
      case "site_official": return "자사몰";
      case "musinsa": return "무신사";
      default: return item.platform;
    }
  });
  const values = top5.map(item => item.sales_ratio_percent);
  const actualSales = top5.map(item => item.sales);  // ✅ 실제 매출

  const canvas = document.getElementById("platformSalesRatioChart");
  const ctx = canvas.getContext("2d");

  if (chartInstance_platform) chartInstance_platform.destroy();

  chartInstance_platform = new Chart(ctx, {
    type: "pie",
    data: {
      labels: labels,
      datasets: [{
        label: "플랫폼 매출 비중",
        data: values,
        backgroundColor: ["#36A2EB", "#FF6384", "#FFB347", "#FFD700", "#20B2AA"]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: {
        padding: { top: 30, bottom: 30, left: 0, right: 0 }  // ✅ 오른쪽 여유 공간 확보
      },
      plugins: {
        legend: {
          position: "right",
          labels: {
            boxWidth: 20,
            font: { size: 20 },
            padding: 15
          }
        },
        tooltip: {
          bodyFont: { size: 16 },
          callbacks: {
            label: function (ctx) {
              const idx = ctx.dataIndex;
              const sales = actualSales[idx] || 0;
              return `${labels[idx]}: ₩${sales.toLocaleString()}`;  // ✅ 실제 매출 출력
            }
          }
        },
        datalabels: {
          formatter: (value) => `${value.toFixed(1)}%`,
          color: "#000",
          font: { weight: "bold", size: 16 },
          anchor: "end",
          align: "end",
          offset: 0,
          clamp: true
        }
      }
    },
    plugins: [ChartDataLabels]
  });
}
