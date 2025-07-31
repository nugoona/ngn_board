let rawGa4SourceRows = [];
let currentGa4SourcePage = 1;
const ga4SourceItemsPerPage = 10;

// ✅ requestData + page 인자 받도록 수정
function fetchGa4SourceSummaryData(page = 1) {
  currentGa4SourcePage = page;

  const requestData = getRequestData(page, {
    data_type: "ga4_source_summary",
    _cache_buster: Date.now() // 캐시 무효화
  });

  console.log("[DEBUG] GA4 소스별 유입수 요청:", requestData);
  console.log("[DEBUG] GA4 소스별 유입수 요청 - 기간:", requestData.start_date, "~", requestData.end_date);

  showLoading("#loadingOverlayGa4Source");

  $.ajax({
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(requestData),
    success: function (res) {
      // 🔥 최소 500ms 로딩 스피너 표시 보장
      setTimeout(() => {
        hideLoading("#loadingOverlayGa4Source");
      }, 500);

      if (res.status === "success" && res.ga4_source_summary) {
        rawGa4SourceRows = res.ga4_source_summary;
        console.log("[DEBUG] GA4 소스별 유입수 응답:", res.ga4_source_summary);
        console.log("[DEBUG] GA4 소스별 유입수 데이터 개수:", res.ga4_source_summary.length);

        renderGa4SourceSummaryFilters(rawGa4SourceRows);  // 소스 드롭다운
        renderGa4CountrySummaryFilters(rawGa4SourceRows); // 국가 드롭다운

        renderGa4SourceSummaryTable();
        renderGa4SourceSummaryPagination(getFilteredGa4SourceData().length);
      } else {
        console.error("[ERROR] 응답 이상:", res);
      }
    },
    error: function (jqXHR, textStatus, errorThrown) {
      hideLoading("#loadingOverlayGa4Source");
      console.error(`[ERROR] GA4 Source Summary 서버 오류: ${textStatus}, ${errorThrown}`, jqXHR);
    }
  });
}



function renderGa4SourceSummaryFilters(data) {
  const sourceMap = {};
  data.forEach(row => {
    if (row.source) {
      sourceMap[row.source] = (sourceMap[row.source] || 0) + (row.total_users || 0);
    }
  });

  const topSources = Object.entries(sourceMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(entry => entry[0]);

  renderGa4SourceDropdown("#ga4SourceFilter", new Set(topSources), "소스");
}

function renderGa4CountrySummaryFilters(data) {
  const countries = new Set();
  data.forEach(row => {
    if (row.country) countries.add(row.country);
  });

  renderGa4SourceDropdown("#countryFilter", countries, "국가");
}

function renderGa4SourceDropdown(selector, items, label) {
  const dropdown = $(selector);
  dropdown.empty();
  dropdown.append(`<option value="전체">${label} 전체</option>`);
  [...items].sort().forEach(item => {
    dropdown.append(`<option value="${item}">${item}</option>`);
  });
}

function getFilteredGa4SourceData() {
  const selectedSource = $("#ga4SourceFilter").val() || "전체";
  const selectedCountry = $("#countryFilter").val() || "전체";

  const filtered = rawGa4SourceRows.filter(row => {
    const matchSource = selectedSource === "전체" || row.source === selectedSource;
    const matchCountry = selectedCountry === "전체" || row.country === selectedCountry;
    return matchSource && matchCountry;
  });

  if (selectedSource === "전체") {
    return filtered.sort((a, b) => b.total_users - a.total_users);
  }

  const countryMap = {};
  filtered.forEach(row => {
    const country = row.country || "미지정";
    countryMap[country] = (countryMap[country] || 0) + (row.total_users || 0);
  });

  return Object.entries(countryMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([country, users]) => ({
      source: selectedSource,
      country,
      total_users: users
    }));
}

function renderGa4SourceSummaryTable() {
  const tbody = $("#ga4SourceSummaryBody").empty();
  const finalData = getFilteredGa4SourceData();
  const startIdx = (currentGa4SourcePage - 1) * ga4SourceItemsPerPage;
  const paginated = finalData.slice(startIdx, startIdx + ga4SourceItemsPerPage);

  if (paginated.length === 0) {
    const colCount = $("#ga4SourceSummaryTable thead th").length || 3;
    tbody.append(`<tr><td colspan="${colCount}" style="text-align:center;">데이터가 없습니다.</td></tr>`);
    return;
  }

  const selectedSource = $("#ga4SourceFilter").val() || "전체";
  paginated.forEach(row => {
    const tr = $("<tr>");
    if (selectedSource === "전체") {
      tr.append(`<td>${row.company_name || ""}</td>`);
      tr.append(`<td>${row.source || ""}</td>`);
      tr.append(`<td>${(row.total_users || 0).toLocaleString()}</td>`);
    } else {
      tr.append(`<td>${row.source}</td>`);
      tr.append(`<td>${row.country}</td>`);
      tr.append(`<td>${(row.total_users || 0).toLocaleString()}</td>`);
    }
    tbody.append(tr);
  });
}

function renderGa4SourceSummaryPagination(totalItems) {
  const container = $("#pagination_ga4_source_summary").empty();
  const totalPages = Math.ceil(totalItems / ga4SourceItemsPerPage);
  if (totalPages <= 1) return;

  const prevBtn = $(`<button class="pagination-btn">이전</button>`);
  const nextBtn = $(`<button class="pagination-btn">다음</button>`);

  if (currentGa4SourcePage === 1) prevBtn.prop("disabled", true).addClass("disabled");
  else prevBtn.click(() => { currentGa4SourcePage--; renderGa4SourceSummaryTable(); renderGa4SourceSummaryPagination(totalItems); });

  if (currentGa4SourcePage === totalPages) nextBtn.prop("disabled", true).addClass("disabled");
  else nextBtn.click(() => { currentGa4SourcePage++; renderGa4SourceSummaryTable(); renderGa4SourceSummaryPagination(totalItems); });

  container.append(prevBtn);
  container.append(`<span class="pagination-info">${String(currentGa4SourcePage)} / ${String(totalPages)}</span>`);
  container.append(nextBtn);
}

// ✅ 필터 드롭다운 변경 시 테이블 다시 렌더링
$("#ga4SourceFilter, #countryFilter").on("change", () => {
  currentGa4SourcePage = 1;
  renderGa4SourceSummaryTable();
  renderGa4SourceSummaryPagination(getFilteredGa4SourceData().length);
});


