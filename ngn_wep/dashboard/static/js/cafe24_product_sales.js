let cafe24ProductSalesRawData = [];
let cafe24ProductSalesCurrentPage = 1;
const cafe24ProductSalesItemsPerPage = 10; /* 15개에서 10개로 변경 */
let cafe24ProductSalesTotalCount = 0;
let lastXhrProductSales = null;

$(document).ready(function () {
  console.log("[DEBUG] Cafe24 상품 판매 데이터 JS 로드됨");

  // ✅ HTML의 라디오 버튼과 연동
  $("input[name='cafe24_product_sort']").change(() => {
    cafe24ProductSalesCurrentPage = 1;
    const req = getRequestData(1, {
      data_type: "cafe24_product_sales",
      sort_by: $("input[name='cafe24_product_sort']:checked").val()
    });
    fetchCafe24ProductSalesData(req);
  });
});

// ✅ 테이블 렌더링
function renderCafe24ProductSalesTable() {
  const $body = $("#cafe24ProductSalesBody").empty();

  if (!Array.isArray(cafe24ProductSalesRawData) || cafe24ProductSalesRawData.length === 0) {
    const colCount = $("#cafe24ProductSalesTable thead th").length || 12;
    $body.html(`<tr><td colspan="${colCount}" style="text-align:center;">데이터가 없습니다.</td></tr>`);
    return;
  }

  const rowsHtml = cafe24ProductSalesRawData.map(row => {
    const formattedDate = cleanData(row.report_date);
    const firstOrder = row.total_first_order != null ? cleanData(row.total_first_order) : "0";

    return `
      <tr>
        <td>${cleanData(row.company_name)}</td>
        <td>${formattedDate}</td>
        <td>${cleanData(row.product_name)}</td>
        <td>${cleanData(row.product_price)}</td>
        <td>${cleanData(row.total_quantity)}</td>
        <td>${cleanData(row.total_canceled)}</td>
        <td>${cleanData(row.item_quantity)}</td>
        <td>${cleanData(row.item_product_sales)}</td>
        <td>${firstOrder}</td>
        <td><a href="${cleanData(row.product_url)}" target="_blank">상품 보기</a></td>
      </tr>
    `;
  }).join("");

  $body.html(rowsHtml);
}

// ✅ 페이지네이션 렌더링
function renderCafe24ProductSalesPagination() {
  const $container = $("#pagination_cafe24_product_sales").empty();
  const totalPages = Math.ceil(cafe24ProductSalesTotalCount / cafe24ProductSalesItemsPerPage);

  if (totalPages <= 1) return;

  const sort_by = $("input[name='cafe24_product_sort']:checked").val();

  const $prev = $("<button class='pagination-btn'>이전</button>");
  const $next = $("<button class='pagination-btn'>다음</button>");

  if (cafe24ProductSalesCurrentPage === 1) {
    $prev.prop("disabled", true).addClass("disabled");
  } else {
    $prev.click(() => {
      cafe24ProductSalesCurrentPage--;
      const req = getRequestData(cafe24ProductSalesCurrentPage, {
        data_type: "cafe24_product_sales",
        sort_by
      });
      fetchCafe24ProductSalesData(req);
    });
  }

  if (cafe24ProductSalesCurrentPage === totalPages) {
    $next.prop("disabled", true).addClass("disabled");
  } else {
    $next.click(() => {
      cafe24ProductSalesCurrentPage++;
      const req = getRequestData(cafe24ProductSalesCurrentPage, {
        data_type: "cafe24_product_sales",
        sort_by
      });
      fetchCafe24ProductSalesData(req);
    });
  }

  $container.append($prev);
  $container.append(`<span class="pagination-info">${cafe24ProductSalesCurrentPage} / ${totalPages}</span>`);
  $container.append($next);
}

// ✅ 데이터 요청
function fetchCafe24ProductSalesData(requestData) {
  const { period, end_date } = requestData;

  if (period === "manual" && (!end_date || end_date === "")) return Promise.resolve();

  // 순차 실행이므로 abort 제거
  // if (lastXhrProductSales) {
  //   console.log("[DEBUG] 이전 Cafe24 상품 판매 요청 abort");
  //   lastXhrProductSales.abort();
  // }

  showLoading("#loadingOverlayCafe24Products");
  const startTime = performance.now();

  return new Promise((resolve, reject) => {
    lastXhrProductSales = $.ajax({
      url: "/dashboard/get_data",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify(requestData),
      success: (response) => {
        hideLoading("#loadingOverlayCafe24Products");
        const elapsed = (performance.now() - startTime).toFixed(1);
        console.log(`[DEBUG] ✅ Cafe24 상품 판매 응답 도착 (${elapsed}ms)`);
        console.log("[DEBUG] 응답 구조:", response);

        if (!response || response.error) {
          console.error("[ERROR] Cafe24 상품 판매 데이터 오류:", response?.error || "알 수 없는 오류");
          reject(response?.error || "응답 오류");
          return;
        }

        // 응답 구조 확인 및 데이터 추출
        const data = response.cafe24_product_sales || response.rows || [];
        const totalCount = response.cafe24_product_sales_total_count || response.total_count || 0;
        
        console.log("[DEBUG] 추출된 데이터:", data);
        console.log("[DEBUG] 데이터 개수:", data.length);
        console.log("[DEBUG] 전체 개수:", totalCount);

        cafe24ProductSalesRawData = data;
        cafe24ProductSalesTotalCount = totalCount;
        renderCafe24ProductSalesTable();
        renderCafe24ProductSalesPagination();
        resolve(response);
      },
      error: (xhr, textStatus, errorThrown) => {
        hideLoading("#loadingOverlayCafe24Products");
        if (textStatus !== "abort") {
          console.warn("[ERROR] cafe24ProductSales Ajax 오류:", textStatus, errorThrown);
          reject(errorThrown);
        } else {
          console.log("[DEBUG] Cafe24 상품 판매 요청 abort됨");
        }
      },
      complete: () => {
        lastXhrProductSales = null;
      }
    });
  });
}
