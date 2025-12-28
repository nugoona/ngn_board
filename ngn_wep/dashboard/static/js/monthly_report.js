/**
 * 월간 전략 리포트 뷰어
 * 백엔드 API를 통해 JSON 데이터를 로드하여 9개 섹션을 렌더링
 * 성능 최적화: lazy loading, skeleton UI, 가로 스크롤, 캐시
 */

// 캐시 저장소
const reportCache = new Map();

let currentReportData = null;
let currentCompany = null;
let currentYear = null;
let currentMonth = null;

/**
 * 업체 선택 확인
 */
function getSelectedCompany() {
  const companySelect = document.getElementById("accountFilter");
  if (!companySelect) return null;
  const value = companySelect.value;
  return value && value !== "all" ? value : null;
}

/**
 * 토스트 메시지 표시
 */
function showToast(message) {
  const existingToast = document.querySelector(".toast-message");
  if (existingToast) existingToast.remove();
  
  const toast = document.createElement("div");
  toast.className = "toast-message";
  toast.textContent = message;
  document.body.appendChild(toast);
  
  setTimeout(() => toast.classList.add("show"), 10);
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

/**
 * 모달 열기
 */
function openMonthlyReportModal() {
  console.log("[월간 리포트] 모달 열기 시작");
  const companyName = getSelectedCompany();
  if (!companyName) {
    showToast("업체를 먼저 선택해주세요");
    return;
  }
  
  const modal = document.getElementById("monthlyReportModal");
  console.log("[월간 리포트] 모달 요소:", modal);
  if (!modal) {
    console.error("[월간 리포트] 모달 요소를 찾을 수 없습니다!");
    return;
  }
  
  console.log("[월간 리포트] 모달 클래스 (열기 전):", modal.className);
  modal.classList.remove("hidden");
  console.log("[월간 리포트] hidden 클래스 제거 후:", modal.className);
  
  // display를 먼저 flex로 설정 (hidden 클래스가 display: none을 설정했을 수 있음)
  modal.style.display = "flex";
  
  // requestAnimationFrame을 두 번 사용하여 브라우저가 스타일을 계산할 시간을 줌
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      modal.classList.add("active");
      // 인라인 스타일로 opacity를 강제로 설정 (CSS transition이 작동하도록)
      modal.style.opacity = "1";
      modal.style.pointerEvents = "all";
      console.log("[월간 리포트] active 클래스 추가 후:", modal.className);
      console.log("[월간 리포트] 모달 computed style display:", window.getComputedStyle(modal).display);
      console.log("[월간 리포트] 모달 computed style opacity:", window.getComputedStyle(modal).opacity);
    });
  });
  
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth() + 1;
  
  currentCompany = companyName;
  currentYear = year;
  currentMonth = month;
  
  loadMonthlyReport(companyName, year, month);
}

/**
 * 모달 닫기
 */
function closeMonthlyReportModal() {
  const modal = document.getElementById("monthlyReportModal");
  if (!modal) return;
  
  modal.classList.remove("active");
  // 인라인 스타일도 제거
  modal.style.opacity = "";
  modal.style.pointerEvents = "";
  setTimeout(() => {
    modal.classList.add("hidden");
    modal.style.display = "";
    // 데이터 초기화
    currentReportData = null;
  }, 300);
}

/**
 * 백엔드 API를 통해 월간 리포트 데이터 로드 (캐시 지원)
 */
async function loadMonthlyReport(companyName, year, month) {
  const loadingEl = document.getElementById("monthlyReportLoading");
  const contentEl = document.getElementById("monthlyReportContent");
  
  // 캐시 키 생성
  const cacheKey = `${companyName}-${year}-${month}`;
  
  // 캐시 확인
  if (reportCache.has(cacheKey)) {
    const cachedData = reportCache.get(cacheKey);
    currentReportData = cachedData;
    updateReportHeader(companyName, year, month);
    renderAllSections(cachedData);
    if (loadingEl) loadingEl.style.display = "none";
    if (contentEl) {
      Array.from(contentEl.querySelectorAll(".monthly-report-section")).forEach(section => {
        section.style.display = "block";
      });
    }
    return;
  }
  
  // 로딩바 초기화
  if (loadingEl) {
    loadingEl.style.display = "block";
    loadingEl.innerHTML = `
      <div class="loading-progress-wrapper">
        <div class="loading-progress-bar" id="loadingProgressBar" style="width: 0%"></div>
        <div class="loading-text">리포트를 불러오는 중... <span id="loadingPercent">0%</span></div>
      </div>
    `;
    updateLoadingProgress(0);
  }
  if (contentEl) {
    Array.from(contentEl.querySelectorAll(".monthly-report-section")).forEach(section => {
      section.style.display = "none";
    });
  }
  
  try {
    // 점진적 로딩 진행률 시뮬레이션
    const progressInterval = setInterval(() => {
      const currentPercent = parseInt(document.getElementById("loadingPercent")?.textContent || "0");
      if (currentPercent < 30) {
        updateLoadingProgress(currentPercent + 2);
      }
    }, 100);
    
    // 백엔드 API를 통해 데이터 로드
    const response = await fetch("/dashboard/monthly_report", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        company_name: companyName,
        year: year,
        month: month
      })
    });
    
    clearInterval(progressInterval);
    updateLoadingProgress(50);
    
    const result = await response.json();
    
    if (result.status === "error") {
      throw new Error(result.message || "리포트를 불러올 수 없습니다");
    }
    
    if (!result.data) {
      throw new Error("리포트 데이터가 없습니다");
    }
    
    const data = result.data;
    console.log("[월간 리포트] 받은 데이터:", data);
    console.log("[월간 리포트] 데이터 구조 확인 - facts:", data?.facts);
    console.log("[월간 리포트] 데이터 구조 확인 - mall_sales:", data?.facts?.mall_sales);
    
    currentReportData = data;
    
    // 캐시에 저장
    reportCache.set(cacheKey, data);
    
    updateLoadingProgress(70);
    
    // 헤더 업데이트
    updateReportHeader(companyName, year, month);
    
    updateLoadingProgress(85);
    
    // 모든 섹션 렌더링
    console.log("[월간 리포트] 섹션 렌더링 시작");
    renderAllSections(data);
    console.log("[월간 리포트] 섹션 렌더링 완료");
    
    updateLoadingProgress(100);
    
    // 로딩 숨김, 섹션 표시
    setTimeout(() => {
      console.log("[월간 리포트] 섹션 표시 시작");
      if (loadingEl) {
        loadingEl.style.display = "none";
        console.log("[월간 리포트] 로딩 요소 숨김 완료");
      }
      if (contentEl) {
        const sections = Array.from(contentEl.querySelectorAll(".monthly-report-section"));
        console.log("[월간 리포트] 찾은 섹션 개수:", sections.length);
        sections.forEach((section, index) => {
          console.log(`[월간 리포트] 섹션 ${index + 1} 표시 전 - display:`, window.getComputedStyle(section).display);
          section.style.display = "block";
          console.log(`[월간 리포트] 섹션 ${index + 1} 표시 후 - display:`, window.getComputedStyle(section).display);
          console.log(`[월간 리포트] 섹션 ${index + 1} 표시:`, section.className);
          console.log(`[월간 리포트] 섹션 ${index + 1} innerHTML 길이:`, section.innerHTML.length);
        });
        console.log("[월간 리포트] 모든 섹션 표시 완료");
        
        // 섹션 1의 실제 DOM 상태 확인
        const section1 = document.querySelector(".section-1-key-metrics");
        if (section1) {
          console.log("[월간 리포트] 섹션 1 최종 상태:");
          console.log("  - display:", window.getComputedStyle(section1).display);
          console.log("  - visibility:", window.getComputedStyle(section1).visibility);
          console.log("  - opacity:", window.getComputedStyle(section1).opacity);
          console.log("  - height:", window.getComputedStyle(section1).height);
          const scorecard = section1.querySelector("#section1Scorecard");
          if (scorecard) {
            console.log("  - scorecard children:", scorecard.children.length);
            console.log("  - scorecard innerHTML 길이:", scorecard.innerHTML.length);
          }
        }
      } else {
        console.error("[월간 리포트] contentEl을 찾을 수 없습니다!");
      }
    }, 300);
    
  } catch (error) {
    console.error("[월간 리포트] 로드 실패:", error);
    showToast(`리포트를 불러올 수 없습니다: ${error.message}`);
    
    if (loadingEl) {
      loadingEl.innerHTML = `
        <div class="error-state">
          <div class="error-icon">⚠️</div>
          <div class="error-text">리포트를 불러올 수 없습니다</div>
          <div class="error-subtext">${error.message}</div>
        </div>
      `;
    }
  }
}

/**
 * 로딩 진행률 업데이트
 */
function updateLoadingProgress(percent) {
  const progressBar = document.getElementById("loadingProgressBar");
  const percentText = document.getElementById("loadingPercent");
  if (progressBar) {
    progressBar.style.width = `${percent}%`;
  }
  if (percentText) {
    percentText.textContent = `${percent}%`;
  }
}

/**
 * 리포트 헤더 업데이트
 */
function updateReportHeader(companyName, year, month) {
  const titleEl = document.getElementById("monthlyReportTitle");
  if (titleEl) {
    const monthStr = String(month).padStart(2, '0');
    titleEl.textContent = `${year}.${monthStr} 월간 AI 리포트 - ${companyName.toUpperCase()}`;
  }
}

/**
 * 모든 섹션 렌더링
 */
function renderAllSections(data) {
  console.log("[월간 리포트] 렌더링 시작, 데이터 구조:", data);
  
  try {
    renderSection1(data); // 지난달 매출 요약
  } catch (e) {
    console.error("[월간 리포트] 섹션 1 렌더링 실패:", e);
  }
  
  try {
    renderSection2(data); // 고객 방문 및 구매 여정
  } catch (e) {
    console.error("[월간 리포트] 섹션 2 렌더링 실패:", e);
  }
  
  try {
    renderSection3(data); // 베스트 상품 성과
  } catch (e) {
    console.error("[월간 리포트] 섹션 3 렌더링 실패:", e);
  }
  
  try {
    renderSection4(data); // 외부 시장 트렌드 (29CM)
  } catch (e) {
    console.error("[월간 리포트] 섹션 4 렌더링 실패:", e);
  }
  
  try {
    renderSection5(data); // 주요 유입 채널
  } catch (e) {
    console.error("[월간 리포트] 섹션 5 렌더링 실패:", e);
  }
  
  try {
    renderSection6(data); // 광고 매체 효율
  } catch (e) {
    console.error("[월간 리포트] 섹션 6 렌더링 실패:", e);
  }
  
  try {
    renderSection7(data); // 우리와 시장의 차이점
  } catch (e) {
    console.error("[월간 리포트] 섹션 7 렌더링 실패:", e);
  }
  
  try {
    renderSection8(data); // 다음 달 목표 및 전망
  } catch (e) {
    console.error("[월간 리포트] 섹션 8 렌더링 실패:", e);
  }
  
  try {
    renderSection9(data); // AI 제안 전략 액션
  } catch (e) {
    console.error("[월간 리포트] 섹션 9 렌더링 실패:", e);
  }
  
  console.log("[월간 리포트] 모든 섹션 렌더링 완료");
}

// ============================================
// 섹션 1: 지난달 매출 요약
// ============================================
function renderSection1(data) {
  console.log("[섹션 1] 데이터 로드 시작", data);
  const facts = data.facts || {};
  const mallSales = facts.mall_sales || {};
  const thisMonth = mallSales.this || {};
  const prevMonth = mallSales.prev || {};
  const comparisons = facts.comparisons || {};
  const comp = comparisons.mall_sales || {};
  
  console.log("[섹션 1] facts:", facts);
  console.log("[섹션 1] mallSales:", mallSales);
  console.log("[섹션 1] thisMonth:", thisMonth);
  console.log("[섹션 1] prevMonth:", prevMonth);
  
  const netSalesThis = thisMonth.net_sales || 0;
  const netSalesPrev = prevMonth.net_sales || 0;
  const ordersThis = thisMonth.total_orders || 0;
  const ordersPrev = prevMonth.total_orders || 0;
  const aovThis = ordersThis > 0 ? netSalesThis / ordersThis : 0;
  const aovPrev = ordersPrev > 0 ? netSalesPrev / ordersPrev : 0;
  
  console.log("[섹션 1] 계산된 값:", { netSalesThis, netSalesPrev, ordersThis, ordersPrev, aovThis, aovPrev });
  
  // 절대값 계산
  const salesDiff = netSalesThis - netSalesPrev;
  const ordersDiff = ordersThis - ordersPrev;
  const aovDiff = aovThis - aovPrev;
  
  const scorecardData = [
    {
      label: "월 매출",
      value: formatMoney(netSalesThis),
      prev: formatMoney(netSalesPrev),
      change: comp.net_sales_mom ? formatChange(comp.net_sales_mom.pct) : "-",
      diff: formatMoney(Math.abs(salesDiff)),
      status: comp.net_sales_mom?.pct >= 0 ? "up" : "down"
    },
    {
      label: "주문 건수",
      value: formatNumber(ordersThis) + "건",
      prev: formatNumber(ordersPrev) + "건",
      change: comp.orders_mom ? formatChange(comp.orders_mom.pct) : "-",
      diff: `${Math.abs(ordersDiff)}건`,
      status: comp.orders_mom?.pct >= 0 ? "up" : "down"
    },
    {
      label: "객단가 (AOV)",
      value: formatMoney(aovThis),
      prev: formatMoney(aovPrev),
      change: aovPrev > 0 ? formatChange(((aovThis - aovPrev) / aovPrev) * 100) : "-",
      diff: formatMoney(Math.abs(aovDiff)),
      status: aovThis >= aovPrev ? "up" : "down"
    }
  ];
  
  const container = document.getElementById("section1Scorecard");
    console.log("[섹션 1] container 요소:", container);
  if (container) {
    console.log("[섹션 1] 스코어카드 데이터:", scorecardData);
    const htmlContent = scorecardData.map(item => `
      <div class="scorecard-item">
        <div class="scorecard-label">${item.label}</div>
        <div class="scorecard-value">${item.value}</div>
        <div class="scorecard-prev">전월: ${item.prev}</div>
        <div class="scorecard-change ${item.status}">
          ${item.change !== "-" ? (item.status === "up" ? "▲" : "▼") : ""} ${item.change}
          ${item.diff && item.status === "down" ? ` (${item.diff})` : item.diff && item.status === "up" ? ` (+${item.diff})` : ""}
        </div>
      </div>
    `).join("");
    container.innerHTML = htmlContent;
    console.log("[섹션 1] 스코어카드 렌더링 완료");
    console.log("[섹션 1] container.innerHTML 길이:", container.innerHTML.length);
    console.log("[섹션 1] container.children 개수:", container.children.length);
    console.log("[섹션 1] container computed style display:", window.getComputedStyle(container).display);
    console.log("[섹션 1] container computed style visibility:", window.getComputedStyle(container).visibility);
  } else {
    console.error("[섹션 1] container 요소를 찾을 수 없습니다!");
  }
  
  // AI 분석
  renderAiAnalysis("section1AiAnalysis", data.signals?.section_1_analysis);
}

// ============================================
// 섹션 2: 고객 방문 및 구매 여정
// ============================================
function renderSection2(data) {
  console.log("[섹션 2] 데이터 로드 시작", data);
  const facts = data.facts || {};
  const ga4 = facts.ga4_traffic || {};
  const ga4This = ga4.this || {};
  const mallSales = facts.mall_sales || {};
  const salesThis = mallSales.this || {};
  
  console.log("[섹션 2] GA4 전체 구조:", ga4);
  console.log("[섹션 2] GA4 데이터:", ga4This);
  console.log("[섹션 2] GA4 데이터 키 목록:", Object.keys(ga4This || {}));
  console.log("[섹션 2] GA4 데이터 전체 내용:", JSON.stringify(ga4This, null, 2));
  console.log("[섹션 2] 매출 데이터:", salesThis);
  
  // GA4 데이터 매핑 수정 - totals 객체에서 가져오기
  const totals = ga4This.totals || {};
  const visitors = totals.total_users || 0;
  const cartUsers = totals.add_to_cart_users || 0;
  const purchases = salesThis.total_orders || 0;
  
  console.log("[섹션 2] 계산된 값:", { visitors, cartUsers, purchases });
  console.log("[섹션 2] visitors 경로 확인:", {
    "total_users": ga4This.total_users,
    "users": ga4This.users,
    "visitors": ga4This.visitors,
    "total_visitors": ga4This.total_visitors
  });
  
  const funnelData = [
    { label: "방문", value: visitors, color: "#6366f1" },
    { label: "장바구니", value: cartUsers, color: "#8b5cf6" },
    { label: "결제", value: purchases, color: "#ec4899" }
  ];
  
  const container = document.getElementById("section2Funnel");
  if (container) {
    const maxValue = Math.max(...funnelData.map(d => d.value), 1);
    
    container.innerHTML = funnelData.map((item, index) => {
      const width = maxValue > 0 ? (item.value / maxValue) * 100 : 0;
      const conversion = index > 0 && funnelData[index - 1].value > 0 
        ? ((item.value / funnelData[index - 1].value) * 100).toFixed(1) 
        : "100.0";
      
      return `
        <div class="funnel-item">
          <div class="funnel-label-row">
            <span class="funnel-label">${item.label}</span>
            <span class="funnel-value">${formatNumber(item.value)}</span>
            ${index > 0 ? `<span class="funnel-conversion">전환율: ${conversion}%</span>` : ""}
          </div>
          <div class="funnel-bar-wrapper">
            <div class="funnel-bar" style="width: ${width}%; background-color: ${item.color};"></div>
          </div>
        </div>
      `;
    }).join("");
  }
  
  // AI 분석
  renderAiAnalysis("section2AiAnalysis", data.signals?.section_2_analysis);
}

// ============================================
// 섹션 3: 베스트 상품 성과
// ============================================
function renderSection3(data) {
  console.log("[섹션 3] 데이터 로드 시작", data);
  const facts = data.facts || {};
  const products = facts.products || {};
  console.log("[섹션 3] products:", products);
  
  const productsThis = products.this || {};
  console.log("[섹션 3] products.this:", productsThis);
  
  const rolling = productsThis.rolling || {};
  console.log("[섹션 3] rolling:", rolling);
  
  const d30 = rolling.d30 || {};
  console.log("[섹션 3] d30:", d30);
  
  const topProducts = d30.top_products_by_sales || [];
  console.log("[섹션 3] top_products_by_sales:", topProducts);
  
  const container = document.getElementById("section3BarChart");
  if (container) {
    const top5 = topProducts.slice(0, 5);
    const maxSales = top5.length > 0 ? Math.max(...top5.map(p => p.sales || 0)) : 1;
    
    container.innerHTML = top5.map((product, index) => {
      const sales = product.sales || 0;
      const width = maxSales > 0 ? (sales / maxSales) * 100 : 0;
      const name = product.product_name || "상품명 없음";
      // 상품명 전체 표시 (줄바꿈 허용)
      
      return `
        <div class="bar-chart-item">
          <div class="bar-chart-label-row">
            <span class="bar-chart-rank">${index + 1}</span>
            <span class="bar-chart-name" title="${name}">${name}</span>
            <span class="bar-chart-value">${formatMoney(sales)}</span>
          </div>
          <div class="bar-chart-bar-wrapper">
            <div class="bar-chart-bar" style="width: ${width}%;"></div>
          </div>
        </div>
      `;
    }).join("");
  }
  
  // AI 분석
  renderAiAnalysis("section3AiAnalysis", data.signals?.section_3_analysis);
}

// ============================================
// 섹션 4: 외부 시장 트렌드 (29CM) - Top 5 카드
// ============================================
let section4Data = null;

function renderSection4(data) {
  const facts = data.facts || {};
  const cm29Data = facts["29cm_best"] || {};
  const items = cm29Data.items || [];
  
  section4Data = items;
  
  setupSection4Tabs(items);
  renderSection4ByTab("전체", items, 1);
  
  renderAiAnalysis("section4AiAnalysis", data.signals?.section_4_analysis);
}

function setupSection4Tabs(items) {
  const tabButtons = document.querySelectorAll("#section4Tabs .market-trend-tab-btn");
  
  tabButtons.forEach(btn => {
    btn.addEventListener("click", function() {
      const selectedTab = this.dataset.tab;
      tabButtons.forEach(b => b.classList.remove("active"));
      this.classList.add("active");
      renderSection4ByTab(selectedTab, items, 1); // 페이지 리셋
    });
  });
}

// 섹션 4 페이지네이션 상태
let section4CurrentPage = 1;

function renderSection4ByTab(tabName, items, page = 1) {
  const container = document.getElementById("section4MarketTrend");
  if (!container) return;
  
  let filteredItems;
  if (tabName === "전체") {
    filteredItems = items.filter(item => item.tab === "전체");
  } else {
    const tabMapping = {
      "아우터": "아우터",
      "상의": "상의",
      "니트": "니트웨어",
      "바지": "바지",
      "스커트": "스커트"
    };
    const dataTabName = tabMapping[tabName] || tabName;
    filteredItems = items.filter(item => item.tab === dataTabName);
  }
  
  section4CurrentPage = page;
  const startIdx = (page - 1) * 5;
  const endIdx = startIdx + 5;
  const itemsToRender = filteredItems.slice(startIdx, endIdx);
  const hasNext = filteredItems.length > endIdx;
  const hasPrev = page > 1;
  
  container.style.opacity = "0";
  container.style.transition = "opacity 0.3s ease";
  
  setTimeout(() => {
    container.innerHTML = `
      ${hasPrev ? `
        <button class="market-trend-nav-btn market-trend-nav-prev" onclick="renderSection4ByTab('${tabName}', section4Data, ${page - 1})">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      ` : '<div class="market-trend-nav-spacer"></div>'}
      <div class="market-trend-cards-container">
        ${itemsToRender.map((item, index) => {
          const rank = item.rank || (startIdx + index + 1);
          const brand = item.brand || "Unknown";
          const name = item.name || "Unknown";
          const img = item.img || "";
          const itemId = item.item_id || item.itemId || '';
          const productUrl = itemId ? `https://www.29cm.co.kr/products/${itemId}` : '#';
          
          return `
            <div class="market-trend-card-compact">
              <div class="market-trend-rank-badge">Rank ${rank}</div>
              <div class="market-trend-image-wrapper-compact">
                <div class="image-skeleton"></div>
                <img 
                  src="${img}" 
                  alt="${name}" 
                  class="market-trend-image-compact"
                  loading="lazy"
                  decoding="async"
                  onload="this.parentElement.querySelector('.image-skeleton')?.remove()"
                  onerror="
                    this.parentElement.querySelector('.image-skeleton')?.remove();
                    this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'200\\' height=\\'200\\'%3E%3Crect fill=\\'%23f0f0f0\\' width=\\'200\\' height=\\'200\\'/%3E%3Ctext x=\\'50%25\\' y=\\'50%25\\' text-anchor=\\'middle\\' dy=\\'.3em\\' fill=\\'%23999\\'%3ENo Image%3C/text%3E%3C/svg%3E';
                  ">
              </div>
              <div class="market-trend-info-compact">
                <div class="market-trend-brand-compact">${brand}</div>
                <div class="market-trend-name-compact">${name}</div>
                <a href="${productUrl}" target="_blank" class="market-trend-link-btn">바로가기</a>
              </div>
            </div>
          `;
        }).join("")}
      </div>
      ${hasNext ? `
        <button class="market-trend-nav-btn market-trend-nav-next" onclick="renderSection4ByTab('${tabName}', section4Data, ${page + 1})">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M9 18L15 12L9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      ` : '<div class="market-trend-nav-spacer"></div>'}
    `;
    
    requestAnimationFrame(() => {
      container.style.opacity = "1";
    });
  }, 150);
}

// ============================================
// 섹션 5: 주요 유입 채널
// ============================================
function renderSection5(data) {
  console.log("[섹션 5] 데이터 로드 시작", data);
  const facts = data.facts || {};
  const ga4 = facts.ga4_traffic || {};
  const ga4This = ga4.this || {};
  
  console.log("[섹션 5] GA4 전체 구조:", ga4);
  console.log("[섹션 5] GA4 this 데이터:", ga4This);
  console.log("[섹션 5] GA4 this 키 목록:", Object.keys(ga4This || {}));
  console.log("[섹션 5] GA4 this 전체 내용:", JSON.stringify(ga4This, null, 2));
  
  // top_sources가 없을 수 있으므로 다른 경로 확인
  let topSources = ga4This.top_sources || ga4This.topSources || [];
  
  console.log("[섹션 5] top_sources (첫 시도):", topSources);
  
  // 대체 경로 시도
  if (topSources.length === 0 && ga4This.sources) {
    topSources = ga4This.sources;
    console.log("[섹션 5] sources 경로 사용:", topSources);
  }
  
  // 추가 경로 시도
  if (topSources.length === 0 && ga4.top_sources) {
    topSources = ga4.top_sources;
    console.log("[섹션 5] ga4.top_sources 경로 사용:", topSources);
  }
  
  console.log("[섹션 5] 최종 topSources:", topSources);
  
  const container = document.getElementById("section5DonutChart");
  if (container) {
    const total = topSources.reduce((sum, s) => sum + (s.total_users || s.users || s.value || 0), 0);
    console.log("[섹션 5] 계산된 total:", total);
    console.log("[섹션 5] ApexCharts 존재 여부:", typeof ApexCharts !== "undefined");
    console.log("[섹션 5] topSources.length:", topSources.length);
    
    if (typeof ApexCharts !== "undefined" && topSources.length > 0 && total > 0) {
      const chartData = topSources.map(s => ({
        name: s.source || s.name || "Unknown",
        value: s.total_users || s.users || s.value || 0
      }));
      
      // 기존 차트 제거
      if (container._apexChart) {
        container._apexChart.destroy();
      }
      
      const chart = new ApexCharts(container, {
        series: chartData.map(d => d.value),
        chart: {
          type: "donut",
          height: 300
        },
        labels: chartData.map(d => d.name),
        colors: ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"],
        legend: {
          position: "bottom"
        },
        dataLabels: {
          enabled: true,
          formatter: function(val) {
            return val.toFixed(1) + "%";
          }
        }
      });
      
      chart.render();
      container._apexChart = chart;
    } else {
      container.innerHTML = `
        <div class="donut-chart-fallback">
          <div class="fallback-text">유입 채널 데이터가 없습니다.</div>
        </div>
      `;
    }
  }
  
  renderAiAnalysis("section5AiAnalysis", data.signals?.section_5_analysis);
}

// ============================================
// 섹션 6: 광고 매체 효율
// ============================================
function renderSection6(data) {
  console.log("[섹션 6] 데이터 로드 시작", data);
  const facts = data.facts || {};
  const metaAdsGoals = facts.meta_ads_goals || {};
  const goalsThis = metaAdsGoals.this || {};
  
  console.log("[섹션 6] meta_ads_goals 전체 구조:", metaAdsGoals);
  console.log("[섹션 6] goalsThis 데이터:", goalsThis);
  console.log("[섹션 6] goalsThis 키 목록:", Object.keys(goalsThis || {}));
  console.log("[섹션 6] goalsThis 전체 내용:", JSON.stringify(goalsThis, null, 2));
  
  const container = document.getElementById("section6AdsContent");
  if (container) {
    // 데이터 구조 확인 및 매핑 - top_ads 객체에서 가져오기
    const topAds = goalsThis.top_ads || {};
    const conversionAds = topAds.conversion_top_by_purchases || [];
    const trafficAds = topAds.traffic_top_by_ctr || [];
    
    container.innerHTML = `
      <div class="ads-tab-content active" data-content="conversion">
        ${renderAdsRankingList(conversionAds, "conversion")}
      </div>
      <div class="ads-tab-content" data-content="traffic">
        ${renderAdsRankingList(trafficAds, "traffic")}
      </div>
    `;
    
    document.querySelectorAll(".ads-tab-btn").forEach(btn => {
      btn.addEventListener("click", function() {
        const tab = this.dataset.tab;
        document.querySelectorAll(".ads-tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".ads-tab-content").forEach(c => c.classList.remove("active"));
        this.classList.add("active");
        document.querySelector(`.ads-tab-content[data-content="${tab}"]`)?.classList.add("active");
      });
    });
  }
  
  renderAiAnalysis("section6AiAnalysis", data.signals?.section_6_analysis);
}

function renderAdsRankingList(ads, type) {
  if (!ads || ads.length === 0) {
    return `<div class="ads-empty">${type === "conversion" ? "전환" : "유입"} 소재 데이터가 없습니다.</div>`;
  }
  
  const sorted = [...ads].sort((a, b) => {
    if (type === "conversion") {
      return (b.purchases || b.conversions || 0) - (a.purchases || a.conversions || 0);
    } else {
      return (b.clicks || 0) - (a.clicks || 0);
    }
  });
  
  return sorted.slice(0, 10).map((ad, index) => {
    const name = ad.ad_name || ad.name || "소재명 없음";
    const metric = type === "conversion" 
      ? `전환: ${formatNumber(ad.purchases || ad.conversions || 0)}건`
      : `클릭: ${formatNumber(ad.clicks || 0)}회`;
    const spend = formatMoney(ad.spend || ad.cost || 0);
    
    return `
      <div class="ads-ranking-item">
        <div class="ads-ranking-rank">${index + 1}</div>
        <div class="ads-ranking-info">
          <div class="ads-ranking-name">${name}</div>
          <div class="ads-ranking-metrics">
            <span>${metric}</span>
            <span>•</span>
            <span>${spend}</span>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// ============================================
// 섹션 7: 우리와 시장의 차이점
// ============================================
function renderSection7(data) {
  const signals = data.signals || {};
  const analysis = signals.section_7_analysis || "";
  
  const marketContent = document.getElementById("section7MarketContent");
  const ourContent = document.getElementById("section7OurContent");
  
  if (analysis) {
    const lines = analysis.split("\n").filter(l => l.trim());
    const marketKeywords = [];
    const ourKeywords = [];
    
    lines.forEach(line => {
      if (line.includes("시장") || line.includes("경쟁사")) {
        marketKeywords.push(line);
      } else if (line.includes("우리") || line.includes("자사")) {
        ourKeywords.push(line);
      }
    });
    
    if (marketContent) {
      marketContent.innerHTML = marketKeywords.length > 0
        ? marketKeywords.map(kw => `<div class="comparison-keyword">${kw}</div>`).join("")
        : `<div class="comparison-text">${analysis.substring(0, 200)}...</div>`;
    }
    
    if (ourContent) {
      ourContent.innerHTML = ourKeywords.length > 0
        ? ourKeywords.map(kw => `<div class="comparison-keyword">${kw}</div>`).join("")
        : `<div class="comparison-text">분석 데이터 준비 중...</div>`;
    }
  } else {
    if (marketContent) marketContent.innerHTML = `<div class="comparison-text">분석 데이터 준비 중...</div>`;
    if (ourContent) ourContent.innerHTML = `<div class="comparison-text">분석 데이터 준비 중...</div>`;
  }
}

// ============================================
// 섹션 8: 다음 달 목표 및 전망 (차트 제거)
// ============================================
function renderSection8(data) {
  const facts = data.facts || {};
  const forecast = facts.forecast_next_month || {};
  const mallSales = facts.mall_sales || {};
  const yoy = mallSales.yoy || {};
  
  const container = document.getElementById("section8Forecast");
  if (container) {
    // 작년 동월 매출 (yoy 데이터 사용)
    const lastYearSales = yoy.net_sales || forecast.predicted_sales || 0;
    const target = forecast.target_sales || lastYearSales * 1.1;
    
    // 차트 대신 텍스트로 표시
    container.innerHTML = `
      <div class="forecast-text-content">
        <div class="forecast-item-text">
          <div class="forecast-label">작년 동월 매출</div>
          <div class="forecast-value-large">${formatMoney(lastYearSales)}</div>
        </div>
        <div class="forecast-item-text">
          <div class="forecast-label">목표 매출</div>
          <div class="forecast-value-large">${formatMoney(target)}</div>
        </div>
      </div>
    `;
  }
  
  renderAiAnalysis("section8AiAnalysis", data.signals?.section_8_analysis);
}

// ============================================
// 섹션 9: AI 제안 전략 액션
// ============================================
function renderSection9(data) {
  const signals = data.signals || {};
  const analysis = signals.section_9_analysis || "";
  
  const container = document.getElementById("section9StrategyCards");
  if (container) {
    if (analysis) {
      const strategies = analysis.split(/\n\n+/).filter(s => s.trim().length > 20);
      
      container.innerHTML = strategies.map((strategy, index) => {
        const lines = strategy.split("\n").filter(l => l.trim());
        const title = lines[0] || `전략 ${index + 1}`;
        const content = lines.slice(1).join(" ") || strategy;
        
        const icons = ["💡", "🎯", "📊", "🚀", "⚡", "🔍"];
        const icon = icons[index % icons.length];
        
        return `
          <div class="strategy-card">
            <div class="strategy-card-icon">${icon}</div>
            <div class="strategy-card-title">${title}</div>
            <div class="strategy-card-content">${content}</div>
          </div>
        `;
      }).join("");
    } else {
      container.innerHTML = `
        <div class="strategy-empty">
          <div class="empty-icon">🤖</div>
          <div class="empty-text">AI 전략 분석이 준비되면 표시됩니다.</div>
        </div>
      `;
    }
  }
}

// ============================================
// AI 분석 렌더링 (공통)
// ============================================
function renderAiAnalysis(elementId, analysisText) {
  const element = document.getElementById(elementId);
  if (!element) return;
  
  if (analysisText && analysisText.trim()) {
    element.innerHTML = `<div class="ai-analysis-text">${analysisText}</div>`;
  } else {
    element.innerHTML = `
      <div class="ai-analysis-skeleton">
        <div class="skeleton-line"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
      </div>
    `;
  }
}

// ============================================
// 유틸리티 함수
// ============================================
function formatMoney(value) {
  if (typeof value !== "number" || isNaN(value)) return "-";
  const millions = value / 10000;
  return millions >= 1 ? `${millions.toFixed(1)}만원` : `${Math.round(value).toLocaleString()}원`;
}

function formatNumber(value) {
  if (typeof value !== "number" || isNaN(value)) return "-";
  return value.toLocaleString();
}

function formatChange(pct) {
  if (typeof pct !== "number" || isNaN(pct)) return "-";
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

// ============================================
// 이벤트 리스너
// ============================================
document.addEventListener("DOMContentLoaded", function() {
  const openBtn = document.getElementById("openMonthlyReportBtn");
  if (openBtn) {
    openBtn.addEventListener("click", openMonthlyReportModal);
  }
  
  const closeBtn = document.getElementById("closeMonthlyReportBtn");
  if (closeBtn) {
    closeBtn.addEventListener("click", closeMonthlyReportModal);
  }
  
  const backdrop = document.getElementById("monthlyReportBackdrop");
  if (backdrop) {
    backdrop.addEventListener("click", closeMonthlyReportModal);
  }
  
  const downloadBtn = document.getElementById("downloadMonthlyReportBtn");
  if (downloadBtn) {
    downloadBtn.addEventListener("click", function() {
      console.log("다운로드 기능은 향후 구현 예정");
    });
  }
  
  document.addEventListener("keydown", function(e) {
    if (e.key === "Escape") {
      const modal = document.getElementById("monthlyReportModal");
      if (modal && !modal.classList.contains("hidden")) {
        closeMonthlyReportModal();
      }
    }
  });
});
