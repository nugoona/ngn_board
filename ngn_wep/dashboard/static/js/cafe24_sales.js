let currentPage_sales = 1;
let totalPages_sales = 1;
const itemsPerPage_sales = 10;
let cafe24SalesTotalCount = 0;

let lastXhrSales = null;
let cafe24SalesRawData = [];

$(document).ready(function () {
  console.log("[DEBUG] Cafe24 매출 데이터 JS 로드됨");

  $("#cafe24SalesTable").before(`
    <div class="date-type-filter radio-group" style="margin-bottom: 16px;">
      <label class="radio-item">
        <input type="radio" name="dateType" value="summary" checked>
        <span>기간합</span>
      </label>
      <label class="radio-item">
        <input type="radio" name="dateType" value="daily">
        <span>일자별</span>
      </label>
      <div class="modern-dropdown" style="display: none; margin-left: 16px;">
        <select id="dateSort">
          <option value="desc" selected>날짜 내림차순</option>
          <option value="asc">날짜 오름차순</option>
        </select>
      </div>
    </div>
  `);

  $("input[name='dateType']").change(function () {
    const type = $(this).val();
    $("#dateSort").closest('.modern-dropdown').toggle(type === "daily");

    currentPage_sales = 1;
    const request = getRequestData(currentPage_sales, {
      data_type: "cafe24_sales",
      date_type: type,
      date_sort: $("#dateSort").val()
    });
    fetchCafe24SalesData(request);
  });

  $("#dateSort").change(function () {
    if ($("input[name='dateType']:checked").val() === "daily") {
      currentPage_sales = 1;
      const request = getRequestData(currentPage_sales, {
        data_type: "cafe24_sales",
        date_type: "daily",
        date_sort: $("#dateSort").val()
      });
      fetchCafe24SalesData(request);
    }
  });
});

function updateCafe24SalesTable() {
  const $body = $("#cafe24SalesBody").empty();

  if (!Array.isArray(cafe24SalesRawData) || cafe24SalesRawData.length === 0) {
    const colCount = $("#cafe24SalesTable thead th").length || 10;
    $body.html(`<tr><td colspan="${colCount}" style="text-align:center;">데이터가 없습니다.</td></tr>`);
    return;
  }

  // ✅ slice 제거 — 이미 서버에서 페이징 처리된 데이터 제공
  const rowsHtml = cafe24SalesRawData.map(row => `
    <tr>
      <td>${cleanData(row.company_name)}</td>
      <td>${cleanData(row.report_date)}</td>
      <td>${cleanData(row.total_orders)}</td>
      <td>${cleanData(row.item_product_price)}</td>
      <td>${cleanData(row.total_shipping_fee)}</td>
      <td>${cleanData(row.total_discount)}</td>
      <td>${cleanData(row.total_coupon_discount)}</td>
      <td>${cleanData(row.total_payment)}</td>
      <td>${cleanData(row.total_refund_amount)}</td>
      <td>${cleanData(row.net_sales)}</td>
    </tr>
  `).join("");

  $body.html(rowsHtml);
}

function renderCafe24SalesPagination(requestBase) {
  const $container = $("#pagination_cafe24_sales").empty();
  totalPages_sales = Math.ceil(cafe24SalesTotalCount / itemsPerPage_sales);
  if (totalPages_sales <= 1) return;

  const $prev = $("<button class='pagination-btn'>이전</button>");
  if (currentPage_sales === 1) {
    $prev.prop("disabled", true).addClass("disabled");
  } else {
    $prev.click(() => {
      currentPage_sales--;
      const request = getRequestData(currentPage_sales, requestBase);
      fetchCafe24SalesData(request);
    });
  }

  const $next = $("<button class='pagination-btn'>다음</button>");
  if (currentPage_sales === totalPages_sales) {
    $next.prop("disabled", true).addClass("disabled");
  } else {
    $next.click(() => {
      currentPage_sales++;
      const request = getRequestData(currentPage_sales, requestBase);
      fetchCafe24SalesData(request);
    });
  }

  $container.append($prev);
  $container.append(`<span class="pagination-info">${currentPage_sales} / ${totalPages_sales}</span>`);
  $container.append($next);
}

function fetchCafe24SalesData(requestData) {
  const { period, end_date } = requestData;
  if (period === "manual" && (!end_date || end_date === "")) return Promise.resolve();

  // 순차 실행이므로 abort 제거
  // if (lastXhrSales) {
  //   console.log("[DEBUG] 이전 Cafe24 매출 요청 abort");
  //   lastXhrSales.abort();
  // }

  showLoading("#loadingOverlayCafe24Sales");
  const startTime = performance.now();

  return new Promise((resolve, reject) => {
    lastXhrSales = $.ajax({
      url: "/dashboard/get_data",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify(requestData),
      success: (response) => {
        hideLoading("#loadingOverlayCafe24Sales");
        const elapsed = (performance.now() - startTime).toFixed(1);
        console.log(`[DEBUG] ✅ Cafe24 매출 응답 도착 (${elapsed}ms)`);

        if (!response || response.error) {
          console.error("[ERROR] Cafe24 매출 응답 오류:", response?.error || "알 수 없음");
          reject(response?.error || "응답 오류");
          return;
        }

        cafe24SalesRawData = response.cafe24_sales || [];
        cafe24SalesTotalCount = response.cafe24_sales_total_count || 0;

        updateCafe24SalesTable();
        renderCafe24SalesPagination({
          data_type: requestData.data_type,
          date_type: requestData.date_type,
          date_sort: requestData.date_sort,
          period: requestData.period,
          start_date: requestData.start_date,
          end_date: requestData.end_date
        });

        resolve(response);
      },
      error: (xhr, textStatus, errorThrown) => {
        hideLoading("#loadingOverlayCafe24Sales");
        if (textStatus !== "abort") {
          console.warn("[ERROR] Ajax 오류:", textStatus, errorThrown);
          reject(errorThrown);
        } else {
          console.log("[DEBUG] Cafe24 매출 요청 abort됨");
        }
      },
      complete: () => {
        lastXhrSales = null;
      }
    });
  });
}
