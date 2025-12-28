/**
 * 월간 전략 리포트 뷰어
 * GCS에서 직접 JSON 데이터를 로드하여 9개 섹션을 렌더링
 * 성능 최적화: lazy loading, skeleton UI, 가로 스크롤
 */

// GCS 직접 접근 대신 백엔드 API 사용
// const GCS_BASE_URL = "https://storage.googleapis.com/winged-precept-443218-v8.appspot.com/ai-reports";

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
  setTimeout(() => {
    modal.classList.add("hidden");
    // 데이터 초기화
    currentReportData = null;
  }, 300);
}

/**
 * 백엔드 API를 통해 월간 리포트 데이터 로드
 */
async function loadMonthlyReport(companyName, year, month) {
  const loadingEl = document.getElementById("monthlyReportLoading");
  const contentEl = document.getElementById("monthlyReportContent");
  
  // 로딩 상태 표시
  if (loadingEl) {
    loadingEl.style.display = "block";
    loadingEl.innerHTML = `
      <div class="loading-spinner"></div>
      <div class="loading-text">리포트를 불러오는 중...</div>
    `;
  }
  if (contentEl) {
    Array.from(contentEl.querySelectorAll(".monthly-report-section")).forEach(section => {
      section.style.display = "none";
    });
  }
  
  try {
    // 백엔드 API를 통해 데이터 로드 (GCS 직접 접근 대신)
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
    
    if (result.status === "error") {
      throw new Error(result.message || "리포트를 불러올 수 없습니다");
    }
    
    if (!result.data) {
      throw new Error("리포트 데이터가 없습니다");
    }
    
    const data = result.data;
    currentReportData = data;
    
    // 헤더 업데이트
    updateReportHeader(companyName, year, month);
    
    // 모든 섹션 렌더링
    renderAllSections(data);
    
    // 로딩 숨김, 섹션 표시
    if (loadingEl) loadingEl.style.display = "none";
    if (contentEl) {
      Array.from(contentEl.querySelectorAll(".monthly-report-section")).forEach(section => {
        section.style.display = "block";
      });
    }
    
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
 * 리포트 헤더 업데이트
 */
function updateReportHeader(companyName, year, month) {
  const titleEl = document.getElementById("monthlyReportTitle");
  if (titleEl) {
    const monthStr = String(month).padStart(2, '0');
    titleEl.textContent = `${year}.${monthStr} Monthly Strategy Report - ${companyName.toUpperCase()}`;
  }
}

/**
 * 모든 섹션 렌더링
 */
function renderAllSections(data) {
  renderSection1(data); // 월간 핵심 지표
  renderSection2(data); // 고객 방문 및 구매 여정
  renderSection3(data); // 베스트 상품 성과
  renderSection4(data); // 외부 시장 트렌드 (29CM)
  renderSection5(data); // 주요 유입 채널
  renderSection6(data); // 광고 매체 효율
  renderSection7(data); // 우리와 시장의 차이점
  renderSection8(data); // 다음 달 목표 및 전망
  renderSection9(data); // AI 제안 전략 액션
}

// ============================================
// 섹션 1: 월간 핵심 지표 요약
// ============================================
function renderSection1(data) {
  const facts = data.facts || {};
  const mallSales = facts.mall_sales || {};
  const monthly13m = mallSales.monthly_13m || [];
  const thisMonth = mallSales.this || {};
  const prevMonth = mallSales.prev || {};
  const comparisons = facts.comparisons || {};
  const comp = comparisons.mall_sales || {};
  
  // 최근 2개월 데이터
  const latest = monthly13m[monthly13m.length - 1] || {};
  const prev = monthly13m[monthly13m.length - 2] || {};
  
  const netSalesThis = thisMonth.net_sales || 0;
  const netSalesPrev = prevMonth.net_sales || 0;
  const ordersThis = thisMonth.total_orders || 0;
  const ordersPrev = prevMonth.total_orders || 0;
  const aovThis = ordersThis > 0 ? netSalesThis / ordersThis : 0;
  const aovPrev = ordersPrev > 0 ? netSalesPrev / ordersPrev : 0;
  
  const scorecardData = [
    {
      label: "월 매출",
      value: formatMoney(netSalesThis),
      prev: formatMoney(netSalesPrev),
      change: comp.net_sales_mom ? formatChange(comp.net_sales_mom.pct) : "-",
      status: comp.net_sales_mom?.pct >= 0 ? "up" : "down"
    },
    {
      label: "주문 건수",
      value: formatNumber(ordersThis) + "건",
      prev: formatNumber(ordersPrev) + "건",
      change: comp.orders_mom ? formatChange(comp.orders_mom.pct) : "-",
      status: comp.orders_mom?.pct >= 0 ? "up" : "down"
    },
    {
      label: "객단가 (AOV)",
      value: formatMoney(aovThis),
      prev: formatMoney(aovPrev),
      change: aovPrev > 0 ? formatChange(((aovThis - aovPrev) / aovPrev) * 100) : "-",
      status: aovThis >= aovPrev ? "up" : "down"
    }
  ];
  
  const container = document.getElementById("section1Scorecard");
  if (container) {
    container.innerHTML = scorecardData.map(item => `
      <div class="scorecard-item">
        <div class="scorecard-label">${item.label}</div>
        <div class="scorecard-value">${item.value}</div>
        <div class="scorecard-prev">전월: ${item.prev}</div>
        <div class="scorecard-change ${item.status}">
          ${item.change !== "-" ? (item.status === "up" ? "▲" : "▼") : ""} ${item.change}
        </div>
      </div>
    `).join("");
  }
  
  // AI 분석
  renderAiAnalysis("section1AiAnalysis", data.signals?.section_1_analysis);
}

// ============================================
// 섹션 2: 고객 방문 및 구매 여정
// ============================================
function renderSection2(data) {
  const facts = data.facts || {};
  const ga4 = facts.ga4_traffic || {};
  const ga4This = ga4.this || {};
  const mallSales = facts.mall_sales || {};
  const salesThis = mallSales.this || {};
  
  const visitors = ga4This.total_users || 0;
  const cartUsers = ga4This.cart_users || 0;
  const purchases = salesThis.total_orders || 0;
  
  const funnelData = [
    { label: "방문", value: visitors, color: "#6366f1" },
    { label: "장바구니", value: cartUsers, color: "#8b5cf6" },
    { label: "결제", value: purchases, color: "#ec4899" }
  ];
  
  const container = document.getElementById("section2Funnel");
  if (container) {
    const maxValue = Math.max(...funnelData.map(d => d.value));
    
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
  const facts = data.facts || {};
  const products = facts.products || {};
  const productsThis = products.this || {};
  const rolling = productsThis.rolling || {};
  const d30 = rolling.d30 || {};
  const topProducts = d30.top_products_by_sales || [];
  
  const container = document.getElementById("section3BarChart");
  if (container) {
    const top5 = topProducts.slice(0, 5);
    const maxSales = top5.length > 0 ? Math.max(...top5.map(p => p.sales || 0)) : 1;
    
    container.innerHTML = top5.map((product, index) => {
      const sales = product.sales || 0;
      const width = maxSales > 0 ? (sales / maxSales) * 100 : 0;
      const name = product.product_name || "상품명 없음";
      const truncatedName = name.length > 30 ? name.substring(0, 30) + "..." : name;
      
      return `
        <div class="bar-chart-item">
          <div class="bar-chart-label-row">
            <span class="bar-chart-rank">${index + 1}</span>
            <span class="bar-chart-name" title="${name}">${truncatedName}</span>
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
// 섹션 4: 외부 시장 트렌드 (29CM) - 카테고리 탭 방식
// ============================================
let section4Data = null; // 전체 데이터 저장

function renderSection4(data) {
  const facts = data.facts || {};
  const cm29Data = facts["29cm_best"] || {};
  const items = cm29Data.items || [];
  
  // 전체 데이터 저장 (탭 전환 시 사용)
  section4Data = items;
  
  // 탭 이벤트 리스너 설정
  setupSection4Tabs(items);
  
  // 초기 로딩: 전체 탭의 10개만 렌더링
  renderSection4ByTab("전체", items);
  
  // AI 분석
  renderAiAnalysis("section4AiAnalysis", data.signals?.section_4_analysis);
}

/**
 * 섹션 4 탭 설정
 */
function setupSection4Tabs(items) {
  const tabButtons = document.querySelectorAll("#section4Tabs .market-trend-tab-btn");
  
  tabButtons.forEach(btn => {
    btn.addEventListener("click", function() {
      const selectedTab = this.dataset.tab;
      
      // 탭 활성화 상태 변경
      tabButtons.forEach(b => b.classList.remove("active"));
      this.classList.add("active");
      
      // 해당 탭의 데이터 렌더링
      renderSection4ByTab(selectedTab, items);
    });
  });
}

/**
 * 선택된 탭에 해당하는 아이템 렌더링 (최대 10개)
 */
function renderSection4ByTab(tabName, items) {
  const container = document.getElementById("section4MarketTrend");
  if (!container) return;
  
  // 선택된 탭에 해당하는 아이템 필터링
  let filteredItems;
  if (tabName === "전체") {
    filteredItems = items.filter(item => item.tab === "전체");
  } else {
    // 카테고리명 매핑 (탭 버튼 텍스트 → 데이터의 tab 속성)
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
  
  // 최대 10개만 렌더링
  const itemsToRender = filteredItems.slice(0, 10);
  
  // 페이드 아웃 애니메이션
  container.style.opacity = "0";
  container.style.transition = "opacity 0.3s ease";
  
  setTimeout(() => {
    container.innerHTML = itemsToRender.map((item, index) => {
      const rank = item.rank || (index + 1);
      const brand = item.brand || "Unknown";
      const name = item.name || "Unknown";
      const img = item.img || "";
      const reviews = item.reviews || [];
      const firstReview = reviews.length > 0 ? reviews[0].txt || "" : "";
      const truncatedReview = firstReview.length > 50 ? firstReview.substring(0, 50) + "..." : firstReview;
      
      return `
        <div class="market-trend-card-horizontal">
          <div class="market-trend-rank-badge">Rank ${rank}</div>
          <div class="market-trend-image-wrapper-horizontal">
            <div class="image-skeleton"></div>
            <img 
              src="${img}" 
              alt="${name}" 
              class="market-trend-image-horizontal"
              loading="lazy"
              decoding="async"
              onload="this.parentElement.querySelector('.image-skeleton')?.remove()"
              onerror="
                this.parentElement.querySelector('.image-skeleton')?.remove();
                this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'200\\' height=\\'200\\'%3E%3Crect fill=\\'%23f0f0f0\\' width=\\'200\\' height=\\'200\\'/%3E%3Ctext x=\\'50%25\\' y=\\'50%25\\' text-anchor=\\'middle\\' dy=\\'.3em\\' fill=\\'%23999\\'%3ENo Image%3C/text%3E%3C/svg%3E';
              ">
          </div>
          <div class="market-trend-info-horizontal">
            <div class="market-trend-brand-horizontal">${brand}</div>
            <div class="market-trend-name-horizontal">${name}</div>
            ${truncatedReview ? `
              <div class="market-trend-review-bubble">
                <div class="review-bubble-text">${truncatedReview}</div>
              </div>
            ` : ""}
          </div>
        </div>
      `;
    }).join("");
    
    // 페이드 인 애니메이션
    requestAnimationFrame(() => {
      container.style.opacity = "1";
    });
  }, 150);
}

// ============================================
// 섹션 5: 주요 유입 채널
// ============================================
function renderSection5(data) {
  const facts = data.facts || {};
  const ga4 = facts.ga4_traffic || {};
  const ga4This = ga4.this || {};
  const topSources = ga4This.top_sources || [];
  
  const container = document.getElementById("section5DonutChart");
  if (container) {
    const total = topSources.reduce((sum, s) => sum + (s.users || 0), 0);
    
    // ApexCharts 도넛 차트 생성
    if (typeof ApexCharts !== "undefined" && topSources.length > 0) {
      const chartData = topSources.map(s => ({
        name: s.source || "Unknown",
        value: s.users || 0
      }));
      
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
    } else {
      container.innerHTML = `
        <div class="donut-chart-fallback">
          <div class="fallback-text">유입 채널 데이터가 없습니다.</div>
        </div>
      `;
    }
  }
  
  // AI 분석
  renderAiAnalysis("section5AiAnalysis", data.signals?.section_5_analysis);
}

// ============================================
// 섹션 6: 광고 매체 효율
// ============================================
function renderSection6(data) {
  const facts = data.facts || {};
  const metaAdsGoals = facts.meta_ads_goals || {};
  const goalsThis = metaAdsGoals.this || {};
  
  const container = document.getElementById("section6AdsContent");
  if (container) {
    // 전환 목표 데이터
    const conversionAds = goalsThis.conversion_ads || [];
    const trafficAds = goalsThis.traffic_ads || [];
    
    container.innerHTML = `
      <div class="ads-tab-content active" data-content="conversion">
        ${renderAdsRankingList(conversionAds, "conversion")}
      </div>
      <div class="ads-tab-content" data-content="traffic">
        ${renderAdsRankingList(trafficAds, "traffic")}
      </div>
    `;
    
    // 탭 전환 이벤트
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
  
  // AI 분석
  renderAiAnalysis("section6AiAnalysis", data.signals?.section_6_analysis);
}

function renderAdsRankingList(ads, type) {
  if (!ads || ads.length === 0) {
    return `<div class="ads-empty">${type === "conversion" ? "전환" : "유입"} 소재 데이터가 없습니다.</div>`;
  }
  
  const sorted = [...ads].sort((a, b) => {
    if (type === "conversion") {
      return (b.purchases || 0) - (a.purchases || 0);
    } else {
      return (b.clicks || 0) - (a.clicks || 0);
    }
  });
  
  return sorted.slice(0, 10).map((ad, index) => {
    const name = ad.ad_name || "소재명 없음";
    const metric = type === "conversion" 
      ? `전환: ${formatNumber(ad.purchases || 0)}건`
      : `클릭: ${formatNumber(ad.clicks || 0)}회`;
    const spend = formatMoney(ad.spend || 0);
    
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
    // 간단한 파싱 (실제로는 더 정교한 파싱 필요)
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
// 섹션 8: 다음 달 목표 및 전망
// ============================================
function renderSection8(data) {
  const facts = data.facts || {};
  const forecast = facts.forecast_next_month || {};
  
  const container = document.getElementById("section8Forecast");
  if (container) {
    const predicted = forecast.predicted_sales || 0;
    const target = forecast.target_sales || predicted * 1.1; // 목표가 없으면 예측의 110%
    const progress = target > 0 ? (predicted / target) * 100 : 0;
    
    container.innerHTML = `
      <div class="forecast-item">
        <div class="forecast-label-row">
          <span class="forecast-label">예측 매출</span>
          <span class="forecast-value">${formatMoney(predicted)}</span>
        </div>
        <div class="forecast-progress-bar-wrapper">
          <div class="forecast-progress-bar" style="width: ${Math.min(progress, 100)}%;"></div>
        </div>
      </div>
      <div class="forecast-item">
        <div class="forecast-label-row">
          <span class="forecast-label">목표 매출</span>
          <span class="forecast-value">${formatMoney(target)}</span>
        </div>
        <div class="forecast-progress-bar-wrapper">
          <div class="forecast-progress-bar target" style="width: 100%;"></div>
        </div>
      </div>
    `;
  }
  
  // AI 분석
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
      // 전략을 문단별로 분리
      const strategies = analysis.split(/\n\n+/).filter(s => s.trim().length > 20);
      
      container.innerHTML = strategies.map((strategy, index) => {
        const lines = strategy.split("\n").filter(l => l.trim());
        const title = lines[0] || `전략 ${index + 1}`;
        const content = lines.slice(1).join(" ") || strategy;
        
        // 아이콘 선택 (순환)
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
