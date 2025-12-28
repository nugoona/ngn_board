/**
 * 월간 리포트 뷰어
 * GCS 버킷에서 스냅샷 데이터를 가져와서 표시
 */

// Mock Data (개발용)
const MOCK_REPORT_DATA = {
  meta: {
    report_month: "2025-12",
    company_name: "PISCESS"
  },
  scorecard: [
    { label: "월 매출", current: "1,498만원", prev: "1,662만원", change: "-9.9%", status: "down" },
    { label: "객단가(AOV)", current: "11.0만원", prev: "8.6만원", change: "+27.9%", status: "up" },
    { label: "주문 건수", current: "136건", prev: "192건", change: "-29.2%", status: "down" }
  ],
  market_trend: {
    title: "29CM 아우터 카테고리 Top 3",
    items: [
      { rank: 1, brand: "오떼뜨", name: "부클 램 하프 퍼 코트", img: "https://img.29cm.co.kr/item/202511/11f0baaa17fe8c51938051050108e7e7.jpg" },
      { rank: 2, brand: "108파운드", name: "몰리 리버시블 코트", img: "https://img.29cm.co.kr/item/202509/11f09ab523b75244920c61e3e96ef393.jpg" },
      { rank: 3, brand: "로우", name: "테디 플리스 아노락", img: "https://img.29cm.co.kr/item/202511/11f0c03affb14929a563cbe2f0c50560.jpg" }
    ],
    keywords: ["#리버시블", "#부클소재", "#보온성"]
  },
  ai_analysis: {
    scorecard: null, // AI 해석 텍스트
    market_trend: null, // AI 해석 텍스트
    insights: null // AI 전략 인사이트
  }
};

let currentReportData = null;

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
  // 기존 토스트가 있으면 제거
  const existingToast = document.querySelector(".toast-message");
  if (existingToast) {
    existingToast.remove();
  }
  
  const toast = document.createElement("div");
  toast.className = "toast-message";
  toast.textContent = message;
  document.body.appendChild(toast);
  
  // 애니메이션
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
  const companyName = getSelectedCompany();
  if (!companyName) {
    showToast("업체를 먼저 선택해주세요");
    return;
  }
  
  const modal = document.getElementById("monthlyReportModal");
  if (!modal) return;
  
  modal.classList.remove("hidden");
  requestAnimationFrame(() => {
    modal.classList.add("active");
  });
  
  // 현재 날짜 기준으로 리포트 로드
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth() + 1;
  
  loadMonthlyReport(companyName, year, month);
}

/**
 * 모달 닫기
 */
function closeMonthlyReportModal() {
  const modal = document.getElementById("monthlyReportModal");
  if (!modal) return;
  
  modal.classList.remove("active");
  setTimeout(() => {
    modal.classList.add("hidden");
  }, 300);
}

/**
 * GCS 버킷에서 월간 리포트 데이터 로드
 */
async function loadMonthlyReport(companyName, year, month) {
  try {
    // 로딩 상태 표시
    showLoadingState();
    
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
    
    const result = await response.json();
    
    if (result.status === "success" && result.data) {
      currentReportData = result.data;
      renderMonthlyReport(result.data, year, month);
    } else {
      // 데이터가 없으면 Mock Data 사용
      console.warn("리포트 데이터 없음, Mock Data 사용:", result.message);
      renderMonthlyReportWithMockData(companyName, year, month);
    }
  } catch (error) {
    console.error("리포트 로드 실패:", error);
    // 에러 시 Mock Data 사용
    renderMonthlyReportWithMockData(companyName, year, month);
  } finally {
    hideLoadingState();
  }
}

/**
 * 실제 스냅샷 데이터로 렌더링
 */
function renderMonthlyReport(snapshotData, year, month) {
  // 헤더 업데이트
  const titleEl = document.getElementById("monthlyReportTitle");
  if (titleEl) {
    const companyName = snapshotData.report_meta?.company_name || "Unknown";
    titleEl.textContent = `${year}.${String(month).padStart(2, '0')} Monthly Strategy Report - ${companyName.toUpperCase()}`;
  }
  
  // 섹션 1: 매크로 성적표
  renderScorecard(snapshotData);
  
  // 섹션 2: 마켓 트렌드 (29CM 데이터)
  renderMarketTrend(snapshotData);
  
  // 섹션 3: AI 인사이트
  renderAiInsights(snapshotData);
}

/**
 * Mock Data로 렌더링
 */
function renderMonthlyReportWithMockData(companyName, year, month) {
  const mockData = {
    ...MOCK_REPORT_DATA,
    meta: {
      ...MOCK_REPORT_DATA.meta,
      company_name: companyName.toUpperCase(),
      report_month: `${year}-${String(month).padStart(2, '0')}`
    }
  };
  
  // 헤더 업데이트
  const titleEl = document.getElementById("monthlyReportTitle");
  if (titleEl) {
    titleEl.textContent = `${year}.${String(month).padStart(2, '0')} Monthly Strategy Report - ${companyName.toUpperCase()}`;
  }
  
  // Mock Data 렌더링
  renderScorecardMock(mockData.scorecard);
  renderMarketTrendMock(mockData.market_trend);
  renderAiInsightsMock();
}

/**
 * 매크로 성적표 렌더링
 */
function renderScorecard(snapshotData) {
  const tbody = document.getElementById("scorecardTableBody");
  if (!tbody) return;
  
  const facts = snapshotData.facts || {};
  const mallSales = facts.mall_sales || {};
  const comparisons = facts.comparisons || {};
  
  // 이번 달 / 지난 달 데이터
  const salesThis = mallSales.this || {};
  const salesPrev = mallSales.prev || {};
  const comparison = comparisons.mall_sales || {};
  
  const scorecardData = [
    {
      label: "월 매출",
      current: formatMoney(salesThis.net_sales || 0),
      prev: formatMoney(salesPrev.net_sales || 0),
      change: comparison.net_sales_mom ? formatChange(comparison.net_sales_mom.pct) : "-",
      status: comparison.net_sales_mom?.pct >= 0 ? "up" : "down"
    },
    {
      label: "객단가(AOV)",
      current: formatMoney((salesThis.net_sales || 0) / (salesThis.total_orders || 1)),
      prev: formatMoney((salesPrev.net_sales || 0) / (salesPrev.total_orders || 1)),
      change: "-", // 계산 필요
      status: "neutral"
    },
    {
      label: "주문 건수",
      current: formatNumber(salesThis.total_orders || 0) + "건",
      prev: formatNumber(salesPrev.total_orders || 0) + "건",
      change: comparison.net_sales_mom ? formatChange(comparison.net_sales_mom.pct) : "-",
      status: comparison.net_sales_mom?.pct >= 0 ? "up" : "down"
    }
  ];
  
  tbody.innerHTML = scorecardData.map(item => `
    <tr>
      <td>${item.label}</td>
      <td class="value-current">${item.current}</td>
      <td class="value-prev">${item.prev}</td>
      <td class="value-change ${item.status}">
        ${item.change !== "-" ? (item.status === "up" ? "▲" : "▼") : ""} ${item.change}
      </td>
    </tr>
  `).join("");
  
  // AI 해석 (현재는 스켈레톤, 나중에 실제 데이터로 교체)
  const aiAnalysisEl = document.getElementById("scorecardAiAnalysis");
  if (aiAnalysisEl) {
    aiAnalysisEl.innerHTML = `
      <div class="ai-analysis-skeleton">
        <div class="skeleton-line"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
      </div>
    `;
  }
}

/**
 * Mock Data로 성적표 렌더링
 */
function renderScorecardMock(scorecardData) {
  const tbody = document.getElementById("scorecardTableBody");
  if (!tbody) return;
  
  tbody.innerHTML = scorecardData.map(item => `
    <tr>
      <td>${item.label}</td>
      <td class="value-current">${item.current}</td>
      <td class="value-prev">${item.prev}</td>
      <td class="value-change ${item.status}">
        ${item.status === "up" ? "▲" : "▼"} ${item.change}
      </td>
    </tr>
  `).join("");
}

/**
 * 마켓 트렌드 렌더링
 */
function renderMarketTrend(snapshotData) {
  const facts = snapshotData.facts || {};
  const cm29Data = facts["29cm_best"];
  
  if (!cm29Data || !cm29Data.items || cm29Data.items.length === 0) {
    // 데이터 없으면 Mock Data 사용
    renderMarketTrendMock(MOCK_REPORT_DATA.market_trend);
    return;
  }
  
  // 29CM 데이터에서 Top 3 추출 (전체 탭에서 상위 3개)
  const allTabItems = cm29Data.items.filter(item => item.tab === "전체");
  const topItems = allTabItems
    .slice(0, 3)
    .map((item, index) => ({
      rank: item.rank || (index + 1),
      brand: item.brand || "Unknown",
      name: item.name || "Unknown",
      img: item.img || ""
    }));
  
  if (topItems.length > 0) {
    renderMarketTrendItems(topItems, "29CM 아우터 카테고리 Top 3");
    
    // 키워드 추출 (리뷰에서 자주 나오는 키워드 등, 현재는 Mock)
    const keywordsEl = document.getElementById("marketTrendKeywords");
    if (keywordsEl) {
      keywordsEl.innerHTML = `
        <span class="keyword-tag">#리버시블</span>
        <span class="keyword-tag">#부클소재</span>
        <span class="keyword-tag">#보온성</span>
      `;
    }
  } else {
    renderMarketTrendMock(MOCK_REPORT_DATA.market_trend);
  }
  
  // AI 해석 (현재는 스켈레톤)
  const aiAnalysisEl = document.getElementById("marketTrendAiAnalysis");
  if (aiAnalysisEl) {
    aiAnalysisEl.innerHTML = `
      <div class="ai-analysis-skeleton">
        <div class="skeleton-line"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
      </div>
    `;
  }
}

/**
 * Mock Data로 마켓 트렌드 렌더링
 */
function renderMarketTrendMock(marketTrendData) {
  renderMarketTrendItems(marketTrendData.items, marketTrendData.title);
  
  // 키워드 렌더링
  const keywordsEl = document.getElementById("marketTrendKeywords");
  if (keywordsEl && marketTrendData.keywords) {
    keywordsEl.innerHTML = marketTrendData.keywords.map(kw => 
      `<span class="keyword-tag">${kw}</span>`
    ).join("");
  }
  
  // AI 해석 (현재는 스켈레톤)
  const aiAnalysisEl = document.getElementById("marketTrendAiAnalysis");
  if (aiAnalysisEl) {
    aiAnalysisEl.innerHTML = `
      <div class="ai-analysis-skeleton">
        <div class="skeleton-line"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
      </div>
    `;
  }
}

/**
 * 마켓 트렌드 아이템 렌더링
 */
function renderMarketTrendItems(items, title) {
  const titleEl = document.getElementById("marketTrendTitle");
  if (titleEl) {
    titleEl.textContent = title;
  }
  
  const gridEl = document.getElementById("marketTrendGrid");
  if (!gridEl) return;
  
  gridEl.innerHTML = items.map(item => `
    <div class="market-trend-card">
      <div class="market-trend-rank">Rank ${item.rank}</div>
      <div class="market-trend-image-wrapper">
        <img src="${item.img}" alt="${item.name}" class="market-trend-image" 
             onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'200\\' height=\\'200\\'%3E%3Crect fill=\\'%23f0f0f0\\' width=\\'200\\' height=\\'200\\'/%3E%3Ctext x=\\'50%25\\' y=\\'50%25\\' text-anchor=\\'middle\\' dy=\\'.3em\\' fill=\\'%23999\\'%3ENo Image%3C/text%3E%3C/svg%3E'">
      </div>
      <div class="market-trend-info">
        <div class="market-trend-brand">${item.brand}</div>
        <div class="market-trend-name">${item.name}</div>
      </div>
    </div>
  `).join("");
}

/**
 * AI 인사이트 렌더링
 */
function renderAiInsights(snapshotData) {
  const insightsEl = document.getElementById("aiInsightsContent");
  if (!insightsEl) return;
  
  // 현재는 Empty State
  insightsEl.innerHTML = `
    <div class="ai-insights-empty-state">
      <div class="empty-state-icon">🤖</div>
      <div class="empty-state-text">AI가 데이터를 분석할 준비가 되었습니다.</div>
      <div class="empty-state-subtext">분석이 완료되면 전략 인사이트가 표시됩니다.</div>
    </div>
  `;
}

/**
 * Mock Data로 AI 인사이트 렌더링
 */
function renderAiInsightsMock() {
  renderAiInsights(null);
}

/**
 * 유틸리티 함수들
 */
function formatMoney(value) {
  if (typeof value !== "number") return "-";
  const millions = value / 10000;
  return millions >= 1 ? `${millions.toFixed(1)}만원` : `${value.toLocaleString()}원`;
}

function formatNumber(value) {
  if (typeof value !== "number") return "-";
  return value.toLocaleString();
}

function formatChange(pct) {
  if (pct === null || pct === undefined) return "-";
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

function showLoadingState() {
  // 로딩 상태 표시 (필요시 구현)
}

function hideLoadingState() {
  // 로딩 상태 숨김 (필요시 구현)
}

/**
 * 이벤트 리스너 등록
 */
document.addEventListener("DOMContentLoaded", function() {
  // 월간 리포트 버튼 클릭
  const openBtn = document.getElementById("openMonthlyReportBtn");
  if (openBtn) {
    openBtn.addEventListener("click", openMonthlyReportModal);
  }
  
  // 모달 닫기
  const closeBtn = document.getElementById("closeMonthlyReportBtn");
  if (closeBtn) {
    closeBtn.addEventListener("click", closeMonthlyReportModal);
  }
  
  // 백드롭 클릭 시 닫기
  const backdrop = document.getElementById("monthlyReportBackdrop");
  if (backdrop) {
    backdrop.addEventListener("click", closeMonthlyReportModal);
  }
  
  // 다운로드 버튼 (향후 구현)
  const downloadBtn = document.getElementById("downloadMonthlyReportBtn");
  if (downloadBtn) {
    downloadBtn.addEventListener("click", function() {
      // TODO: PDF 다운로드 기능
      console.log("다운로드 기능은 향후 구현 예정");
    });
  }
  
  // ESC 키로 닫기
  document.addEventListener("keydown", function(e) {
    if (e.key === "Escape") {
      const modal = document.getElementById("monthlyReportModal");
      if (modal && !modal.classList.contains("hidden")) {
        closeMonthlyReportModal();
      }
    }
  });
});

