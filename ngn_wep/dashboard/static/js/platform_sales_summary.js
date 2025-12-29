let currentPage_platform = 1;
let totalPages_platform = 1;
const itemsPerPage_platform = 1000;
let allPlatformSalesData = [];

$(document).ready(function () {
  console.log("[DEBUG] platform_sales_summary.js 로드됨");

  $("input[name='platformDateType']").change(function () {
    $("#platformDateSort").toggle($(this).val() === "daily");
    currentPage_platform = 1;

    document.getElementById("platformStartDateValue").value = $("#startDate").val();
    document.getElementById("platformEndDateValue").value = $("#endDate").val();

    fetchPlatformSalesSummary();
  });

  $("#platformDateSort").change(function () {
    if ($("input[name='platformDateType']:checked").val() === "daily") {
      currentPage_platform = 1;
      fetchPlatformSalesSummary();
    }
  });

  $("#togglePlatformSalesRatio").on("click", function () {
    const $container = $("#platformSalesRatioContainer");
    const isVisible = $container.is(":visible");
    $container.toggle();
    $(this).text(isVisible ? "매출 비중 차트 보기" : "매출 비중 차트 숨기기");
    if (!isVisible) fetchPlatformSalesRatio();
  });

  fetchPlatformSalesSummary();
});

function fetchPlatformSalesSummary() {
  const period = $("#periodSelector").val();
  const endDate = $("#endDate").val();

  if (period === "manual" && !endDate) {
    console.warn("[SKIP] 종료일이 없어 요청 생략");
    return;
  }

  const requestData = getRequestData(currentPage_platform, {
    data_type: "platform_sales_summary",
    date_type: $("input[name='platformDateType']:checked").val(),
    date_sort: $("#platformDateSort").val() || "desc"
  });

  console.log("[DEBUG] 플랫폼 요약 요청값:", requestData);
  showLoading("#loadingOverlayPlatformSalesSummary");

  latestAjaxRequest("platform_sales_summary", {
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(requestData),
    error: function (xhr, status, error) {
      hideLoading("#loadingOverlayPlatformSalesSummary");
      console.error("[ERROR] 플랫폼 매출 요약 오류:", status, error);
    }
  }, function (res) {
    hideLoading("#loadingOverlayPlatformSalesSummary");
    if (res.status === "success") {
      allPlatformSalesData = res.platform_sales_summary || [];
      currentPage_platform = 1;
      renderPlatformSalesTable(currentPage_platform);
      renderPlatformSalesPagination(allPlatformSalesData.length);
    }
  });
}

function renderPlatformSalesTable(page) {
  const tbody = $("#platformSalesSummaryBody");
  tbody.empty();

  const selectedPeriod = $("#periodFilter").val();
  const startDate = $("#platformStartDateValue").val();  // ✅ 기간합용 날짜는 hidden input에서
  const endDate = $("#platformEndDateValue").val();
  const dateType = $("input[name='platformDateType']:checked").val();

  const platforms = [
    "site_official", "musinsa", "29cm", "shopee", "eql",
    "llud", "hana", "heights", "zigzag", "ably"
  ];

  const filteredData = allPlatformSalesData.filter(row => row.company_name !== "total");

  if (filteredData.length === 0) {
    tbody.append("<tr><td colspan='13'>데이터가 없습니다.</td></tr>");
    return;
  }

  // ✅ 기간합일 경우: 한 줄만 출력하고 "기간합" 행 표시
  if (selectedPeriod === "manual") {
    const row = filteredData[0];
    const formattedDate =
      (row.start_date && row.end_date)
        ? `${row.start_date} ~ ${row.end_date}`
        : "-";
  
    const tr = $("<tr></tr>");
    tr.append(`<td>${row.company_name || "-"}</td>`);
    tr.append(`<td>${formattedDate}</td>`);
    tr.append(`<td>${cleanData(row.total_sales)}</td>`);
    platforms.forEach(p => {
      tr.append(`<td>${cleanData(row[p])}</td>`);
    });
    tbody.append(tr);
  
    const periodTr = $("<tr class='total-row'></tr>");
    periodTr.append(`<td>기간합</td><td>${formattedDate}</td>`);
    periodTr.append(`<td>${cleanData(row.total_sales)}</td>`);
    platforms.forEach(p => {
      periodTr.append(`<td>${cleanData(row[p])}</td>`);
    });
    tbody.append(periodTr);
    return;
  }
  

  // ✅ 일자별일 경우: 페이지네이션 적용 출력
  const start = (page - 1) * itemsPerPage_platform;
  const end = start + itemsPerPage_platform;
  const pageData = filteredData.slice(start, end);

  pageData.forEach(row => {
    const tr = $("<tr></tr>");
    tr.append(`<td>${row.company_name || "-"}</td>`);

    let formattedDate = "-";
    if (row.date) {
      try {
        formattedDate = new Date(row.date).toISOString().split("T")[0];
      } catch (e) {
        formattedDate = row.date;
      }
    }

    tr.append(`<td>${formattedDate}</td>`);
    tr.append(`<td>${cleanData(row.total_sales)}</td>`);
    platforms.forEach(p => {
      tr.append(`<td>${cleanData(row[p])}</td>`);
    });
    tbody.append(tr);
  });
}



function renderPlatformSalesPagination(totalCount) {
  const container = $("#pagination_platform_sales_summary");
  container.empty();

  totalPages_platform = Math.ceil(totalCount / itemsPerPage_platform);
  if (totalPages_platform <= 1) return;

  const prevBtn = $("<button class='pagination-btn'>이전</button>").prop("disabled", currentPage_platform === 1);
  const nextBtn = $("<button class='pagination-btn'>다음</button>").prop("disabled", currentPage_platform === totalPages_platform);

  prevBtn.click(() => {
    currentPage_platform--;
    renderPlatformSalesTable(currentPage_platform);
    renderPlatformSalesPagination(totalCount);
  });

  nextBtn.click(() => {
    currentPage_platform++;
    renderPlatformSalesTable(currentPage_platform);
    renderPlatformSalesPagination(totalCount);
  });

  const pageInfo = $(`<span class="pagination-info">${currentPage_platform} / ${totalPages_platform}</span>`);
  container.append(prevBtn, pageInfo, nextBtn);
}

// ✅ Batch API용 렌더링 함수
function renderPlatformSalesSummaryWidget(data) {
  // ✅ 전역 변수 업데이트 및 페이지 초기화
  currentPage_platform = 1;
  allPlatformSalesData = data || [];

  // ✅ UI 렌더링
  renderPlatformSalesTable(currentPage_platform);
  renderPlatformSalesPagination(allPlatformSalesData.length);

  // ✅ 로딩 스피너 제거
  hideLoading("#loadingOverlayPlatformSalesSummary");
}

window.fetchPlatformSalesSummary = fetchPlatformSalesSummary;
