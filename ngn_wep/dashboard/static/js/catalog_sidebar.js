/* ****************************************
 * catalog_sidebar.js  (v6.3.2 – FB 권한검사 제거 · 풀 버전)
 *****************************************/
// showInlinePopup 함수는 common_ui.js에서 전역으로 정의됨

/* ───────── 전역 상태 ───────── */
let isLoadingCatalog      = false;
let isFetchingManualList  = false;
let isSearchingManual     = false;
let catalogAuthOk         = false;   // ← 추가
let latestCatalogId       = "-";
let manualSearchResults   = [];
let selectedManualItems   = [];

/* ───────── DOM util ───────── */
const qs  = (sel, root = document) => root.querySelector(sel);
const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

/* ───────── 상태/UI util ───────── */
const toggleCatalogSidebarLoading = on => {
  console.log("[DEBUG] toggleCatalogSidebarLoading called with:", on);
  const sidebar = qs("#catalogSidebar");
  console.log("[DEBUG] catalogSidebar element:", sidebar);
  
  if (sidebar) {
    if (on) {
      sidebar.classList.add("loading");
      console.log("[DEBUG] loading class added");
    } else {
      sidebar.classList.remove("loading");
      console.log("[DEBUG] loading class removed");
    }
    console.log("[DEBUG] loading class applied:", sidebar.classList.contains("loading"));
  } else {
    console.error("[ERROR] catalogSidebar element not found!");
  }
  
  isLoadingCatalog = on;
};
const updateCatalogHeader = id => {
  qs("#catalogIdText").textContent = id || "-";
  latestCatalogId = id || "-";
};
const openCatalogSidebar  = () => { const el = qs("#catalogSidebar"); el?.classList.remove("hidden"); requestAnimationFrame(() => el?.classList.add("active")); };
const closeCatalogSidebar = () => { const el = qs("#catalogSidebar"); el?.classList.remove("active"); setTimeout(() => el?.classList.add("hidden"), 300); };

/* ───────── 테이블 렌더러 ───────── */
function renderCatalogTableRows(tbodyId, items = []) {
  const tbody = qs(`#${tbodyId}`);
  if (!tbody) return;
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="3" class="no-data">표시할 상품이 없습니다.</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map(
    ({ product_name, total_quantity, product_no }) =>
      `<tr><td>${product_name}</td><td>${total_quantity}</td><td>${product_no}</td></tr>`
  ).join("");
}

/* ───────── 수동 선택/검색 테이블 util ───────── */
function renderManualProductTable(items = []) {
  const tbody = qs("#manualProductTableBody");
  if (!tbody) return;
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="2" class="no-data">표시할 상품이 없습니다.</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map(
    ({ product_name, product_no }) =>
      `<tr><td>${product_name}</td><td>${product_no}</td></tr>`
  ).join("");
}
const clearManualProductTable = () => {
  const tbody = qs("#manualProductTableBody");
  if (tbody) tbody.innerHTML = `<tr><td colspan="2" class="no-data">상품이 없습니다.</td></tr>`;
};

function renderManualSearchResults() {
  const tbody = qs("#manualSearchResultBody");
  if (!tbody) return;
  if (!manualSearchResults.length) {
    tbody.innerHTML = `<tr><td colspan="4" class="no-data">검색 결과가 없습니다.</td></tr>`;
    return;
  }
  tbody.innerHTML = manualSearchResults.map(({ company_name, product_name, product_no }) => {
    const disabled = selectedManualItems.some(i => i.product_no === product_no);
    return `<tr>
      <td>${company_name}</td><td>${product_name}</td><td>${product_no}</td>
      <td><button class="add-product-btn" data-product-no="${product_no}" ${disabled ? "disabled" : ""}>추가</button></td>
    </tr>`;
  }).join("");

  qsa(".add-product-btn", tbody).forEach(btn => {
    if (btn.disabled) return;
    btn.onclick = () => {
      const pno = btn.dataset.productNo;
      const item = manualSearchResults.find(r => String(r.product_no) === pno);
      if (item) addManualItem({ product_name: item.product_name, product_no: pno });
    };
  });
}
function renderSelectedManualItems() {
  const tbody = qs("#manualSelectedItemBody");
  if (!tbody) return;
  if (!selectedManualItems.length) {
    tbody.innerHTML = `<tr><td colspan="3" class="no-data">아직 추가된 상품이 없습니다.</td></tr>`;
    return;
  }
  tbody.innerHTML = selectedManualItems.map(({ product_name, product_no }) =>
    `<tr><td>${product_name}</td><td>${product_no}</td>
      <td><button class="remove-product-btn" data-no="${product_no}">삭제</button></td></tr>`
  ).join("");
  qsa(".remove-product-btn", tbody).forEach(btn =>
    btn.onclick = () => removeManualItem(btn.dataset.no)
  );
}
function addManualItem(item) {
  if (selectedManualItems.some(i => i.product_no === item.product_no)) {
    return showInlinePopup("이미 추가된 상품입니다.");
  }
  selectedManualItems.push(item);
  renderSelectedManualItems();
  renderManualSearchResults();
}
const removeManualItem = product_no => {
  selectedManualItems = selectedManualItems.filter(i => i.product_no !== product_no);
  renderSelectedManualItems();
  renderManualSearchResults();
};

/* ───────── 서버 요청 – 세트 생성 ───────── */
async function createProductSetOnServer(payload) {
  const res = await fetch("/dashboard/catalog_set", {
    method : "POST",
    headers: { "Content-Type": "application/json" },
    body   : JSON.stringify(payload),
  });
  return res.json();
}

/* ───────── 세트 생성 요약 팝업 ───────── */
async function showSummaryPopup(setName, retailerIds) {
  if (!retailerIds.length) return showInlinePopup("상품을 1개 이상 추가해 주세요.");

  const summary = retailerIds.length === 1
    ? retailerIds[0]
    : `${retailerIds[0]} 외 ${retailerIds.length - 1}개`;

  let serverResult;
  try {
    serverResult = await createProductSetOnServer({
      catalog_id   : latestCatalogId,
      set_name     : setName,
      retailer_ids : retailerIds,
    });
  } catch (e) {
    serverResult = { status: "error", message: e.message };
  }

  showSetCreatedPopup({ catalog_id: latestCatalogId, set_name: setName, summary, serverResult });
}

/* ───────── URL 세트 / 수동 세트 제출 ───────── */
function createCatalogSetPreview() {
  const setName = qs("#urlSetNameInput")?.value.trim();
  if (!setName) return showInlinePopup("세트명을 입력하세요.");
  const ids = qsa("#manualProductTableBody tr")
    .map(tr => tr.querySelector("td:last-child")?.textContent.trim() || "")
    .filter(id => /^\d+$/.test(id));
  showSummaryPopup(setName, ids);
}
function createManualSetPopup() {
  const setName = qs("#manualSetNameInput")?.value.trim();
  if (!setName) return showInlinePopup("세트명을 입력하세요.");
  const ids = selectedManualItems.map(i => i.product_no);
  showSummaryPopup(setName, ids);
}

/* ───────── 세트 생성 결과 팝업 ───────── */
function showSetCreatedPopup(data) {
  const { serverResult } = data;
  const ok = serverResult.status === "success";
  const header = ok
    ? `제품세트가 성공적으로 ${serverResult.action === "updated" ? "업데이트" : "생성"}되었습니다`
    : "제품세트 생성 실패";
  const body  = ok
    ? `<div class="popup-row"><strong>세트 ID :</strong> ${serverResult.set_id}</div>`
    : `<div class="popup-row error"><strong>API 오류 :</strong> ${serverResult.message || "Unknown error"}</div>`;

  const wrap = document.createElement("div");
  wrap.className = "set-created-popup-wrapper";
  wrap.innerHTML = `
    <div class="set-created-popup ${ok ? "" : "error"}">
      <div class="popup-header">${successIcon()} ${header}</div>
      <div class="popup-row"><strong>카탈로그 ID :</strong> ${data.catalog_id}</div>
      <div class="popup-row"><strong>세트명 :</strong> ${data.set_name}</div>
      <div class="popup-row"><strong>포함된 상품 :</strong> ${data.summary}</div>
      ${body}
    </div>`;
  document.body.appendChild(wrap);
  setTimeout(() => wrap.remove(), 5000);
}
function successIcon() {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
            stroke="#4caf50" stroke-width="2.2" class="icon-svg">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M9 12.75 11.25 15 15 9.75 M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
          </svg>`;
}

/* ───────── 로딩 스피너 util ───────── */
const showManualLoading        = () => qs("#manualLoadingSpinner")?.classList.remove("hidden");
const hideManualLoading        = () => qs("#manualLoadingSpinner")?.classList.add("hidden");
const showManualSearchLoading  = () => qs("#manualSearchLoadingSpinner")?.classList.remove("hidden");
const hideManualSearchLoading  = () => qs("#manualSearchLoadingSpinner")?.classList.add("hidden");

/* ───────── 서버 통신 – 사이드바 / 수동 상품 / 검색 ───────── */
async function fetchCatalogSidebar(accountId) {
  if (!accountId) return null;
  toggleCatalogSidebarLoading(true);
  try {
    const res  = await fetch("/dashboard/get_data", {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({ data_type: "catalog_sidebar", account_id: accountId }),
    });
    const json = await res.json();
    if (json.status !== "success") showInlinePopup(json.message || "카탈로그 데이터를 불러올 수 없습니다.");

    const cd = json.catalog_sidebar ?? {};
    updateCatalogHeader(cd.catalog_id || "-");
    renderCatalogTableRows("best-28-table-body", cd.best_28 ?? []);
    renderCatalogTableRows("best-7-table-body" , cd.best_7  ?? []);
    return cd;
  } catch (err) {
    console.error(err);
    showInlinePopup("카탈로그 정보를 불러오는 중 오류가 발생했습니다.");
    return null;
  } finally {
    toggleCatalogSidebarLoading(false);
  }
}

async function fetchManualProducts() {
  if (isFetchingManualList) return;
  const url = qs("#manualCategoryUrlInput")?.value.trim();
  if (!url) return showInlinePopup("URL을 입력해 주세요.");

  isFetchingManualList = true;
  showManualLoading(); clearManualProductTable();
  try {
    const res  = await fetch("/dashboard/get_data", {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({ data_type: "catalog_manual", category_url: url }),
    });
    const json = await res.json();
    renderManualProductTable(json.status === "success" ? json.products : []);
    if (json.status !== "success") showInlinePopup(json.message || "상품 데이터를 불러올 수 없습니다.");
  } catch (e) {
    console.error(e);
    showInlinePopup("요청 중 오류가 발생했습니다.");
  } finally {
    hideManualLoading(); isFetchingManualList = false;
  }
}

async function performManualSearch() {
  if (isSearchingManual) return;
  const keyword   = qs("#manualSearchInput")?.value.trim();
  const type      = qs("#manualSearchTypeSelect")?.value;
  const accountId = window.metaAdsState?.accountId;
  if (!keyword)   return showInlinePopup("검색어를 입력하세요.");
  if (!accountId) return showInlinePopup("계정을 먼저 선택해 주세요.");

  isSearchingManual = true;
  showManualSearchLoading(); manualSearchResults = []; renderManualSearchResults();
  try {
    const res  = await fetch("/dashboard/get_data", {
      method : "POST",
      headers: { "Content-Type": "application/json" },
      body   : JSON.stringify({ data_type: "catalog_manual_search", account_id: accountId, keyword, search_type: type }),
    });
    const json = await res.json();
    manualSearchResults = json.status === "success" ? json.results : [];
    if (json.status !== "success") showInlinePopup(json.message || "검색 결과가 없습니다.");
    renderManualSearchResults();
  } catch (e) {
    console.error(e);
    showInlinePopup("검색 중 오류 발생");
  } finally {
    hideManualSearchLoading(); isSearchingManual = false;
  }
}

/* ───────── 권한 체크(Stub) ─────────
   FB SDK를 제거했으므로, 서버에서 세션·토큰을 이미 보유하고 있다고
   가정해 ‘항상 허용’ 형태의 단순 stub 로 대체.
   필요 시 서버 REST 호출로 교체하세요.                       */
async function checkCatalogAccess() {
  return { allowed: true };
}

/* ───────── DOMContentLoaded ───────── */
document.addEventListener("DOMContentLoaded", () => {
  /* 계정 선택 시 catalogId 동기화 */
  qs("#metaAccountSelector")?.addEventListener("change", e => {
    const selId   = e.target.value || null;
    window.metaAdsState.accountId = selId;

    const opt      = e.target.selectedOptions?.[0];
    let   catId    = opt?.getAttribute("data-catalog");
    const compName = opt?.getAttribute("data-company");
    if (!catId || catId.toLowerCase() === "null") catId = window.metaAdsState.catalogMap?.[selId] || null;
    if (compName && compName !== "null") window.metaAdsState.company = compName;
    window.metaAdsState.catalogId = catId;
    console.debug("[Meta] 계정 변경", { accountId: selId, catalogId: catId, company: compName });
  });

  /* 카탈로그 사이드바 열기 */
  qs("#openCatalogSidebarBtn")?.addEventListener("click", async () => {
    const accountId = window.metaAdsState?.accountId;
    if (!accountId) return showInlinePopup("좌측에서 Meta 광고 계정을 먼저 선택해 주세요.");

    console.log("[DEBUG] 카탈로그 사이드바 열기 시작");
    console.log("[DEBUG] accountId:", accountId);

    // 먼저 사이드바를 표시하고 hidden 클래스 제거
    const sidebar = qs("#catalogSidebar");
    console.log("[DEBUG] sidebar element:", sidebar);
    
    if (sidebar) {
      sidebar.classList.remove("hidden");
      sidebar.classList.add("active");
      console.log("[DEBUG] 사이드바 표시됨");
      
      // 사이드바가 표시된 후 로딩 시작 (약간의 지연으로 애니메이션이 보이도록)
      setTimeout(() => {
        console.log("[DEBUG] 로딩 시작");
        toggleCatalogSidebarLoading(true);
      }, 50);
    }

    try {
      if (!catalogAuthOk) {
        const { allowed } = await checkCatalogAccess();
        if (!allowed) throw new Error("카탈로그 권한이 없습니다.");
        catalogAuthOk = true;
      }
      await fetchCatalogSidebar(accountId);
    } catch (err) {
      console.warn(err);
      showInlinePopup(err.message || "카탈로그 열기 실패");
    } finally {
      console.log("[DEBUG] 로딩 완료");
      toggleCatalogSidebarLoading(false);
    }
  });

  /* 기타 버튼 */
  qs("#closeCatalogSidebarBtn") ?.addEventListener("click", closeCatalogSidebar);
  qs("#manualFetchBtn")        ?.addEventListener("click", fetchManualProducts);
  qs("#createUrlSetBtn")       ?.addEventListener("click", createCatalogSetPreview);
  qs("#manualSearchBtn")       ?.addEventListener("click", performManualSearch);
  qs("#createManualSetBtn")    ?.addEventListener("click", createManualSetPopup);
});

/* ───────── export ───────── */
export { fetchCatalogSidebar, openCatalogSidebar, closeCatalogSidebar };
