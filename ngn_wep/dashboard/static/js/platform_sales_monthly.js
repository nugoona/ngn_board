let allMonthlyPlatformSalesData = [];
let monthlyPlatformSalesData = [];  // 누락된 변수 선언 추가
let platformSalesChart = null;  // (차트용 전역, 현재 미사용이지만 유지)

const platforms = [
  "site_official", "musinsa", "29cm", "shopee", "eql",
  "llud", "hana", "heights", "zigzag", "ably"
];

const itemsPerPage_monthly = 1000;
let currentPage_monthly = 1;
let totalPages_monthly = 1;

$(document).ready(function () {
  console.log("[DEBUG] platform_sales_monthly.js 로드됨");

  $("#accountFilter").change(function () {
    fetchMonthlyPlatformSalesData();
  });

  fetchMonthlyPlatformSalesData();
});

function fetchMonthlyPlatformSalesData() {
  const company = $("#accountFilter").val() || "all";
  const requestData = {
    data_type: "platform_sales_monthly",
    company_name: company
  };

  console.log("[DEBUG] 플랫폼 월별 매출 요청값:", requestData);
  showLoading("#loadingOverlayPlatformSalesMonthly");

  $.ajax({
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(requestData),
    success: function (res) {
      hideLoading("#loadingOverlayPlatformSalesMonthly");

      if (res.status === "success" && res.platform_sales_monthly) {
        monthlyPlatformSalesData = res.platform_sales_monthly;
        currentPage_monthly = 1;
        renderMonthlyPlatformSalesTable(currentPage_monthly);
      } else {
        monthlyPlatformSalesData = [];
        renderMonthlyPlatformSalesTable(currentPage_monthly);
      }
    },
    error: function (xhr, status, error) {
      hideLoading("#loadingOverlayPlatformSalesMonthly");
      console.error("[ERROR] 월별 플랫폼 매출 요청 오류:", status, error);
      monthlyPlatformSalesData = [];
      renderMonthlyPlatformSalesTable(currentPage_monthly);
      renderMonthlyPlatformSalesPagination(0);
    }
  });
}

function renderMonthlyPlatformSalesTable(page) {
  const tbody = $("#platformSalesMonthlyBody");
  tbody.empty();

  if (!monthlyPlatformSalesData.length) {
    tbody.append("<tr><td colspan='13'>데이터가 없습니다.</td></tr>");
    return;
  }

  const start = (page - 1) * itemsPerPage_monthly;
  const end = start + itemsPerPage_monthly;
  const pageData = monthlyPlatformSalesData.slice(start, end);

  pageData.forEach(row => {
    const tr = $("<tr></tr>");

    // ✅ 1. 연도/월
    tr.append(`<td>${row.month || row.year_month || '-'}</td>`);  // 서버가 'month' 필드를 보냄

    // ✅ 2. 총합계
    const totalValue = platforms.reduce((sum, platform) => sum + (row[platform] || 0), 0);
    tr.append(`<td style="font-weight: bold; font-size: 0.9em; text-align: center;">${totalValue.toLocaleString()}</td>`);

    // ✅ 3. 각 플랫폼별 수치 + heatmap 색상
    const maxValue = Math.max(...platforms.map(p => row[p] || 0));
    platforms.forEach(p => {
      const value = row[p] || 0;
      const color = getHeatmapColor(value, maxValue);
      tr.append(`<td style="background-color:${color}; text-align: center;">${value.toLocaleString()}</td>`);
    });

    tbody.append(tr);
  });
}

// ✅ 색상 그라데이션 (히트맵 스타일)
function getHeatmapColor(value, max) {
  if (max === 0) return "#ffffff"; // 값이 모두 0일 경우

  const ratio = value / max;
  const startColor = [255, 255, 255]; // 흰색
  const endColor = [242, 232, 155];     // 낮은 채도의 파랑

  const r = Math.round(startColor[0] + ratio * (endColor[0] - startColor[0]));
  const g = Math.round(startColor[1] + ratio * (endColor[1] - startColor[1]));
  const b = Math.round(startColor[2] + ratio * (endColor[2] - startColor[2]));

  return `rgb(${r}, ${g}, ${b})`;
}

function showLoading(target) {
  $(target).css({ display: "flex" });
}

function hideLoading(target) {
  $(target).css({ display: "none" });
}

// ✅ filters.js나 다른 JS에서 사용할 수 있도록 등록
window.fetchMonthlyPlatformSalesData = fetchMonthlyPlatformSalesData;
