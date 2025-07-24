let rawViewItemRows = [];
let currentPage = 1;
const itemsPerPage = 10;

// ✅ 배포 환경에서는 디버깅 로그 비활성화
const isProduction = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
const debugLog = isProduction ? () => {} : console.log;
const debugError = isProduction ? () => {} : console.error;

// ✅ 기간 필터링, 회사명 필터링 적용
function fetchGa4ViewItemSummaryData(requestData = {}, page = 1) {
  currentPage = page;

  const selectedPeriod = $("#periodFilter").val();
  const startDate = $("#startDate").val()?.trim();
  const endDate = $("#endDate").val()?.trim();

  // 기존 requestData에 기간 필터링 데이터 추가
  const mergedRequest = {
    ...requestData,
    page,
    service: "viewitem_summary",
    data_type: "viewitem_summary",
    period: selectedPeriod,
    start_date: startDate,
    end_date: endDate,
  };

  showLoading("#loadingOverlayViewitemSummary");

  $.ajax({
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(mergedRequest),
    success: function (res) {
      hideLoading("#loadingOverlayViewitemSummary");

      debugLog("[DEBUG] 🔍 ViewItem Summary 응답:", res);
      debugLog("[DEBUG] 📋 res.status:", res.status);
      debugLog("[DEBUG] 📋 res.viewitem_summary:", res.viewitem_summary);
      debugLog("[DEBUG] 📈 res.viewitem_summary 길이:", res.viewitem_summary ? res.viewitem_summary.length : "undefined");

      if (res.status === "success" && res.viewitem_summary) {
        rawViewItemRows = res.viewitem_summary;
        debugLog("[DEBUG] ✅ rawViewItemRows 설정됨:", rawViewItemRows);
        debugLog("[DEBUG] 📊 rawViewItemRows 길이:", rawViewItemRows.length);
        renderViewItemSummaryFilters(rawViewItemRows);
        renderViewItemSummaryTable();
        renderViewItemSummaryPagination(getGroupedFilteredData().length);
      } else {
        debugError("[ERROR] ❌ 응답 이상:", res);
        debugError("[ERROR] 🔍 status가 success가 아님 또는 viewitem_summary가 없음");
      }
    },
    error: function (jqXHR, textStatus, errorThrown) {
      hideLoading("#loadingOverlayViewitemSummary");
      if (textStatus !== "abort") {
      debugError(`[ERROR] ViewItem Summary 서버 오류: ${textStatus}, ${errorThrown}`, jqXHR);
      } else {
        debugLog("[DEBUG] ViewItem Summary 요청 abort됨");
      }
    }
  });
}

function renderViewItemSummaryFilters(data) {
  const sourcesMap = {};
  const countriesMap = {};

  data.forEach(row => {
    if (row.source_raw) {
      sourcesMap[row.source_raw] = (sourcesMap[row.source_raw] || 0) + (row.total_view_item || 0);
    }
    if (row.country) {
      countriesMap[row.country] = (countriesMap[row.country] || 0) + (row.total_view_item || 0);
    }
  });

  const topSources = Object.entries(sourcesMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(entry => entry[0]);

  const topCountries = Object.entries(countriesMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(entry => entry[0]);

  renderDropdown("#sourceFilter", new Set(topSources), "소스");
  renderDropdown("#countryFilter", new Set(topCountries), "국가");
}

function renderDropdown(selector, items, label) {
  const dropdown = $(selector);
  dropdown.empty();
  dropdown.append(`<option value="전체">${label} 전체</option>`);
  [...items].sort().forEach(item => {
    dropdown.append(`<option value="${item}">${item}</option>`);
  });
}

function getGroupedFilteredData() {
  const selectedSource = $("#sourceFilter").val();
  const selectedCountry = $("#countryFilter").val();
  const keyword = $("#productNameSearch").val()?.trim()?.toLowerCase() || "";

  const filtered = rawViewItemRows.filter(row => {
    const sourceMatch = selectedSource === "전체" || row.source_raw === selectedSource;
    const countryMatch = selectedCountry === "전체" || row.country === selectedCountry;
    const nameMatch = row.product_name_cleaned?.toLowerCase()?.includes(keyword);
    return sourceMatch && countryMatch && nameMatch;
  });

  const grouped = {};

  filtered.forEach(row => {
    let keyParts = [row.company_name, row.product_name_cleaned];
    if (selectedSource !== "전체") keyParts.push(row.source_raw || "-");
    if (selectedCountry !== "전체") keyParts.push(row.country || "-");

    const key = keyParts.join("||");

    if (!grouped[key]) {
      grouped[key] = {
        company_name: row.company_name,
        product_name_cleaned: row.product_name_cleaned,
        source_raw: selectedSource === "전체" ? "전체" : row.source_raw || "-",
        country: selectedCountry === "전체" ? "전체" : row.country || "-",
        total_view_item: 0
      };
    }

    grouped[key].total_view_item += row.total_view_item || 0;
  });

  const result = Object.values(grouped);
  result.sort((a, b) => b.total_view_item - a.total_view_item);
  return result;
}

function renderViewItemSummaryTable() {
  debugLog("[DEBUG] 🎨 renderViewItemSummaryTable 호출됨");
  
  const tbody = $("#viewitemSummaryBody").empty();
  debugLog("[DEBUG] 📋 tbody 선택됨:", tbody.length > 0 ? "성공" : "실패");
  
  const grouped = getGroupedFilteredData();
  debugLog("[DEBUG] 📊 grouped 데이터:", grouped);
  debugLog("[DEBUG] 📈 grouped 길이:", grouped.length);
  
  const paginated = grouped.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);
  debugLog("[DEBUG] 📄 paginated 데이터:", paginated);
  debugLog("[DEBUG] 📈 paginated 길이:", paginated.length);

  if (paginated.length === 0) {
    debugLog("[DEBUG] ⚠️ 데이터가 없어서 빈 메시지 표시");
    tbody.append("<tr><td colspan='5'>데이터가 없습니다.</td></tr>");
    return;
  }

  debugLog("[DEBUG] 🚀 테이블 행 렌더링 시작");
  paginated.forEach((row, index) => {
    debugLog(`[DEBUG] 📝 행 ${index + 1}:`, row);
    const tr = $("<tr>");
    tr.append(`<td>${row.company_name}</td>`);
    tr.append(`<td>${row.product_name_cleaned}</td>`);
    tr.append(`<td>${row.source_raw}</td>`);
    tr.append(`<td>${row.country}</td>`);
    tr.append(`<td>${row.total_view_item.toLocaleString()}</td>`);
    tbody.append(tr);
  });
  debugLog("[DEBUG] ✅ 테이블 렌더링 완료");
}

function renderViewItemSummaryPagination(totalItems) {
  const paginationContainer = $("#pagination_viewitem_summary").empty();
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  if (totalPages <= 1) return;

  const prevBtn = $(`<button class="pagination-btn">이전</button>`);
  const nextBtn = $(`<button class="pagination-btn">다음</button>`);

  if (currentPage === 1) prevBtn.prop("disabled", true).addClass("disabled");
  else prevBtn.click(() => {
    currentPage--;
    renderViewItemSummaryTable();
    renderViewItemSummaryPagination(totalItems);
  });

  if (currentPage === totalPages) nextBtn.prop("disabled", true).addClass("disabled");
  else nextBtn.click(() => {
    currentPage++;
    renderViewItemSummaryTable();
    renderViewItemSummaryPagination(totalItems);
  });

  paginationContainer.append(prevBtn);
  paginationContainer.append(`<span class="pagination-info">${currentPage} / ${totalPages}</span>`);
  paginationContainer.append(nextBtn);
}

// ✅ 필터 드롭다운 + 검색 input 모두 필터링에 반영
$("#sourceFilter, #countryFilter, #productNameSearch").on("input change", () => {
  currentPage = 1;
  renderViewItemSummaryTable();
  renderViewItemSummaryPagination(getGroupedFilteredData().length);
});

// ✅ 전역 함수로 노출 - dashboard.js에서 호출 가능하도록
window.fetchGa4ViewItemSummaryData = fetchGa4ViewItemSummaryData;
