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
    
    // 섹션 7 헤더 설정
    const trendHeader = document.getElementById("section7TrendHeader");
    const companyHeader = document.getElementById("section7CompanyHeader");
    if (trendHeader) {
      trendHeader.textContent = "29CM 베스트";
    }
    if (companyHeader) {
      companyHeader.textContent = companyName.toUpperCase();
    }
    
    updateLoadingProgress(85);
    
    // 모든 섹션 렌더링
    console.log("[월간 리포트] 섹션 렌더링 시작");
    await renderAllSections(data);
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
        console.log("[월간 리포트] 모든 섹션 표시 완료 (Section 3-9는 Lazy Loading)");
        
        // 섹션 5는 Lazy Loading에서 처리되므로 여기서는 제거
        
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
 * 모든 섹션 렌더링 (Lazy Loading 적용)
 * Section 1-2: 즉시 렌더링
 * Section 3-9: Intersection Observer로 지연 렌더링
 */
async function renderAllSections(data) {
  console.log("[월간 리포트] 렌더링 시작, 데이터 구조:", data);
  
  // 즉시 렌더링: Section 1 (지난달 매출 분석), Section 2 (주요 유입 채널)
  try {
    renderSection1(data); // 1. 지난달 매출 분석
  } catch (e) {
    console.error("[월간 리포트] 섹션 1 렌더링 실패:", e);
  }
  
  try {
    await renderSection5(data); // 2. 주요 유입 채널
  } catch (e) {
    console.error("[월간 리포트] 섹션 2 (주요 유입 채널) 렌더링 실패:", e);
  }
  
  // 지연 렌더링: Section 3-9 (Intersection Observer 사용)
  setupLazySectionRendering(data);
  
  console.log("[월간 리포트] 초기 섹션 렌더링 완료 (Section 1-2), 나머지는 Lazy Loading");
}

/**
 * Lazy Section Rendering 설정 (Intersection Observer)
 */
function setupLazySectionRendering(data) {
  // 섹션별 렌더링 함수 매핑
  const sectionRenderers = {
    'section-2-funnel': () => {
      try {
        renderSection2(data); // 3. 고객 방문 및 구매 여정
      } catch (e) {
        console.error("[월간 리포트] 섹션 3 (고객 방문 및 구매 여정) 렌더링 실패:", e);
      }
    },
    'section-3-products': () => {
      try {
        renderSection3(data); // 4. 자사몰 베스트 상품 성과
      } catch (e) {
        console.error("[월간 리포트] 섹션 4 (자사몰 베스트 상품 성과) 렌더링 실패:", e);
      }
    },
    'section-4-market-trend': () => {
      try {
        renderSection4(data); // 5. 시장 트렌드 확인 (29CM)
      } catch (e) {
        console.error("[월간 리포트] 섹션 5 (시장 트렌드 확인) 렌더링 실패:", e);
      }
    },
    'section-6-ads': () => {
      try {
        renderSection6(data); // 6. 매체 성과 및 효율 진단
      } catch (e) {
        console.error("[월간 리포트] 섹션 6 (매체 성과 및 효율 진단) 렌더링 실패:", e);
      }
    },
    'section-7-comparison': () => {
      try {
        renderSection7(data); // 7. 시장 트렌드와 자사몰 비교
      } catch (e) {
        console.error("[월간 리포트] 섹션 7 (시장 트렌드와 자사몰 비교) 렌더링 실패:", e);
      }
    },
    'section-8-forecast': () => {
      try {
        renderSection8(data); // 8. 익월 목표 설정 및 시장 전망
      } catch (e) {
        console.error("[월간 리포트] 섹션 8 (익월 목표 설정 및 시장 전망) 렌더링 실패:", e);
      }
    },
    'section-9-strategy': () => {
      try {
        renderSection9(data); // 9. 데이터 기반 전략 액션 플랜
      } catch (e) {
        console.error("[월간 리포트] 섹션 9 (데이터 기반 전략 액션 플랜) 렌더링 실패:", e);
      }
    }
  };
  
  // Intersection Observer 옵션
  const observerOptions = {
    root: null, // 뷰포트 기준
    rootMargin: '0px',
    threshold: 0.1 // 섹션이 10% 이상 보일 때 트리거
  };
  
  // 렌더링 완료 추적 (중복 렌더링 방지)
  const renderedSections = new Set();
  
  // Intersection Observer 콜백
  const observerCallback = (entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && entry.intersectionRatio >= 0.1) {
        const section = entry.target;
        const sectionClass = Array.from(section.classList).find(cls => cls.startsWith('section-'));
        
        if (sectionClass && !renderedSections.has(sectionClass)) {
          renderedSections.add(sectionClass);
          console.log(`[Lazy Loading] ${sectionClass} 렌더링 시작`);
          
          const renderer = sectionRenderers[sectionClass];
          if (renderer) {
            renderer();
            console.log(`[Lazy Loading] ${sectionClass} 렌더링 완료`);
          }
          
          // 렌더링 후 관찰 중지 (한 번만 렌더링)
          observer.unobserve(section);
        }
      }
    });
  };
  
  // Intersection Observer 생성
  const observer = new IntersectionObserver(observerCallback, observerOptions);
  
  // Section 3-9 관찰 시작
  const lazySections = [
    '.section-2-funnel',
    '.section-3-products',
    '.section-4-market-trend',
    '.section-6-ads',
    '.section-7-comparison',
    '.section-8-forecast',
    '.section-9-strategy'
  ];
  
  lazySections.forEach(selector => {
    const section = document.querySelector(selector);
    if (section) {
      // Placeholder 표시 (이미 HTML에 있지만, 명시적으로 표시)
      section.style.minHeight = '200px'; // 최소 높이로 레이아웃 시프트 방지
      observer.observe(section);
      console.log(`[Lazy Loading] ${selector} 관찰 시작`);
    } else {
      console.warn(`[Lazy Loading] ${selector} 요소를 찾을 수 없습니다`);
    }
  });
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
    { label: "유입수 (GA)", value: visitors, color: "#6366f1" },
    { label: "장바구니 건수 (GA)", value: cartUsers, color: "#8b5cf6" },
    { label: "주문 건수", value: purchases, color: "#ec4899" }
  ];
  
  const container = document.getElementById("section2Funnel");
  if (container) {
    const maxValue = Math.max(...funnelData.map(d => d.value), 1);
    
    container.innerHTML = funnelData.map((item, index) => {
      const width = maxValue > 0 ? (item.value / maxValue) * 100 : 0;
      const conversion = index > 0 && funnelData[index - 1].value > 0 
        ? ((item.value / funnelData[index - 1].value) * 100).toFixed(1) 
        : "100.0";
      
      // 바가 너무 작으면(30% 미만) 수치를 바 밖에 표시
      const showValueInside = width >= 30;
      
      return `
        <div class="funnel-item">
          <div class="funnel-label-row">
            <span class="funnel-label">${item.label}</span>
            ${index > 0 ? `<span class="funnel-conversion">전환율: ${conversion}%</span>` : ""}
          </div>
          <div class="funnel-bar-wrapper">
            <div class="funnel-bar" style="width: ${width}%; background-color: ${item.color};">
              ${showValueInside ? `<span class="funnel-value funnel-value-inside">${formatNumber(item.value)}</span>` : ""}
            </div>
            ${!showValueInside ? `<span class="funnel-value funnel-value-outside">${formatNumber(item.value)}</span>` : ""}
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
  
  // 디버그: 첫 번째 아이템의 구조 확인
  if (items.length > 0) {
    console.log("[섹션 4] 첫 번째 아이템 데이터 구조:", JSON.stringify(items[0], null, 2));
    console.log("[섹션 4] 첫 번째 아이템의 모든 키:", Object.keys(items[0]));
    console.log("[섹션 4] 첫 번째 아이템의 각 필드 값:", {
      "tab": items[0].tab,
      "rank": items[0].rank,
      "name": items[0].name,
      "brand": items[0].brand,
      "price": items[0].price,
      "img": items[0].img,
      "url": items[0].url,
      "item_url": items[0].item_url,
      "itemUrl": items[0].itemUrl,
      "item_id": items[0].item_id,
      "itemId": items[0].itemId
    });
  }
  
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
          
          // URL 변환: 버킷에 저장된 URL을 올바른 형식으로 변환
          // 예: https://product.29cm.co.kr/catalog/2964732 → https://29cm.co.kr/products/2964732
          let productUrl = '#';
          
          // 1. item.url 또는 item.item_url에서 URL 가져오기
          const rawUrl = item.url || item.item_url || (item.itemUrl && (typeof item.itemUrl === 'string' ? item.itemUrl : item.itemUrl.webLink));
          
          if (rawUrl) {
            // URL에서 item_id 추출 (catalog/ 뒤의 숫자)
            const catalogMatch = rawUrl.match(/catalog\/(\d+)/);
            if (catalogMatch) {
              const itemId = catalogMatch[1];
              productUrl = `https://29cm.co.kr/products/${itemId}`;
            } else if (rawUrl.includes('29cm.co.kr/products/')) {
              // 이미 올바른 형식인 경우 그대로 사용
              productUrl = rawUrl;
            } else {
              // 다른 형식의 URL인 경우 그대로 사용
              productUrl = rawUrl;
            }
          } else {
            // URL이 없으면 item_id로 직접 생성
            const itemId = item.item_id || item.itemId;
            if (itemId) {
              productUrl = `https://29cm.co.kr/products/${itemId}`;
            } else {
              // 디버그: URL과 item_id가 모두 없는 경우
              if (index === 0) {
                console.warn("[섹션 4] URL과 item_id가 모두 없습니다. item 객체:", item);
              }
            }
          }
          
          // 디버그: 최종 URL 확인
          if (index === 0) {
            console.log("[섹션 4] URL 변환 결과:", {
              "rawUrl": rawUrl,
              "item_id": item.item_id || item.itemId,
              "최종 productUrl": productUrl
            });
          }
          
          const price = item.price || 0;
          const formattedPrice = price > 0 ? `${Math.round(price).toLocaleString()}원` : '가격 정보 없음';
          
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
                <div class="market-trend-price-compact">${formattedPrice}</div>
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
async function renderSection5(data) {
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
  
  // 섹션 5 요소를 먼저 찾고, 그 안에서 container 찾기
  const section5 = document.querySelector(".section-5-channels");
  console.log("[섹션 5] section-5-channels 요소:", section5);
  
  let container = null;
  if (section5) {
    // 먼저 section-main 내부를 확인
    const sectionMain = section5.querySelector(".section-main");
    console.log("[섹션 5] section-main 요소:", sectionMain);
    
    if (sectionMain) {
      // 기존 donut-chart-wrapper가 있으면 제거하고 channels-table-wrapper 생성
      const donutChart = sectionMain.querySelector("#section5DonutChart, .donut-chart-wrapper");
      if (donutChart) {
        console.log("[섹션 5] 기존 donut-chart-wrapper 발견, 제거하고 table-wrapper 생성");
        donutChart.remove();
      }
      
      // channels-table-wrapper가 없으면 생성
      container = sectionMain.querySelector("#section5ChannelsTable");
      if (!container) {
        console.log("[섹션 5] channels-table-wrapper 생성");
        container = document.createElement("div");
        container.className = "channels-table-wrapper";
        container.id = "section5ChannelsTable";
        sectionMain.appendChild(container);
      }
    } else {
      container = section5.querySelector("#section5ChannelsTable");
    }
    console.log("[섹션 5] 섹션 내부에서 찾은 container:", container);
  }
  
  // 섹션 내부에서 못 찾으면 전체 문서에서 찾기
  if (!container) {
    container = document.getElementById("section5ChannelsTable");
    console.log("[섹션 5] 전체 문서에서 찾은 container:", container);
  }
  
  if (!container) {
    console.error("[섹션 5] container 요소를 찾을 수 없습니다!");
    console.error("[섹션 5] section-5-channels 존재 여부:", !!section5);
    if (section5) {
      console.error("[섹션 5] section-5-channels의 innerHTML 일부:", section5.innerHTML.substring(0, 300));
    }
    // 나중에 다시 시도하도록 설정
    setTimeout(() => {
      console.log("[섹션 5] 재시도: container 요소 찾기");
      renderSection5(data);
    }, 200);
    return;
  }
  
  if (container) {
    const total = topSources.reduce((sum, s) => sum + (s.total_users || s.users || s.value || 0), 0);
    console.log("[섹션 5] 계산된 total:", total);
    console.log("[섹션 5] topSources.length:", topSources.length);
    console.log("[섹션 5] topSources 데이터:", topSources);
    
    if (topSources.length > 0 && total > 0) {
      // Top 5만 선택하고 정렬
      const top5 = topSources
        .map(s => ({
          source: s.source || s.name || "Unknown",
          users: s.total_users || s.users || s.value || 0,
          bounce_rate: s.bounce_rate || 0
        }))
        .sort((a, b) => b.users - a.users)
        .slice(0, 5);
      
      console.log("[섹션 5] Top 5 데이터:", top5);
      
      // 표 생성
      const tableHTML = `
        <table class="channels-table">
          <thead>
            <tr>
              <th>채널</th>
              <th class="text-right">유입수</th>
              <th class="text-right">유입비중</th>
              <th class="text-right">이탈률</th>
            </tr>
          </thead>
          <tbody>
            ${top5.map(item => {
              const share = total > 0 ? ((item.users / total) * 100).toFixed(1) : "0.0";
              return `
                <tr>
                  <td>${item.source}</td>
                  <td class="text-right">${formatNumber(item.users)}</td>
                  <td class="text-right">${share}%</td>
                  <td class="text-right">${item.bounce_rate.toFixed(1)}%</td>
                </tr>
              `;
            }).join("")}
          </tbody>
        </table>
      `;
      
      container.innerHTML = tableHTML;
      console.log("[섹션 5] 표 HTML 생성 완료, container.innerHTML 길이:", container.innerHTML.length);
    } else {
      console.warn("[섹션 5] 데이터가 없거나 total이 0입니다. topSources:", topSources, "total:", total);
      container.innerHTML = `
        <div class="channels-table-empty">
          <div class="empty-text">유입 채널 데이터가 없습니다.</div>
        </div>
      `;
    }
  } else {
    console.error("[섹션 5] container 요소를 찾을 수 없습니다!");
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
    
    // 전환 광고는 ROAS, 유입 광고는 클릭률 추가
    let additionalMetric = "";
    if (type === "conversion") {
      const roas = ad.roas || 0;
      additionalMetric = ` • ROAS: ${roas.toFixed(1)}%`;
    } else {
      const ctr = ad.ctr || 0;
      additionalMetric = ` • 클릭률: ${ctr.toFixed(2)}%`;
    }
    
    return `
      <div class="ads-ranking-item">
        <div class="ads-ranking-rank">${index + 1}</div>
        <div class="ads-ranking-info">
          <div class="ads-ranking-name">${name}</div>
          <div class="ads-ranking-metrics">
            <span>${metric}${additionalMetric}</span>
            <span>•</span>
            <span>${spend}</span>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// ============================================
// 섹션 7: 시장 트렌드와 자사몰 비교
// ============================================
function renderSection7(data) {
  const signals = data.signals || {};
  let analysis = signals.section_7_analysis || "";
  
  // 업체명 가져오기
  const companyName = currentCompany || "업체명";
  
  // 섹션 제목 명시적으로 설정
  const section7 = document.querySelector(".section-7-comparison");
  if (section7) {
    const sectionTitle = section7.querySelector(".section-title");
    if (sectionTitle) {
      sectionTitle.textContent = "시장 트렌드와 자사몰 비교";
    }
  }
  
  // 헤더 업데이트
  const trendHeader = document.getElementById("section7TrendHeader");
  const companyHeader = document.getElementById("section7CompanyHeader");
  const tableTrendHeader = document.getElementById("section7TableTrendHeader");
  const tableCompanyHeader = document.getElementById("section7TableCompanyHeader");
  if (trendHeader) trendHeader.textContent = "29CM 베스트";
  if (companyHeader) companyHeader.textContent = companyName.toUpperCase();
  if (tableTrendHeader) tableTrendHeader.textContent = "29CM 베스트";
  if (tableCompanyHeader) tableCompanyHeader.textContent = companyName.toUpperCase();
  
  // ============================================
  // 1. JSON 블록 추출 및 파싱
  // ============================================
  let comparisonTableData = null;
  const jsonBlockRegex = /```json\s*([\s\S]*?)\s*```/;
  const jsonMatch = analysis.match(jsonBlockRegex);
  
  if (jsonMatch && jsonMatch[1]) {
    try {
      comparisonTableData = JSON.parse(jsonMatch[1].trim());
      console.log("[섹션 7] 비교표 JSON 파싱 성공:", comparisonTableData);
    } catch (e) {
      console.error("[섹션 7] 비교표 JSON 파싱 실패:", e);
      console.error("[섹션 7] 원본 JSON 블록:", jsonMatch[1]);
    }
  }
  
  // ============================================
  // 2. 비교표 렌더링
  // ============================================
  const comparisonTableWrapper = document.getElementById("section7ComparisonTable");
  const comparisonTableBody = document.getElementById("section7ComparisonTableBody");
  
  if (comparisonTableData && comparisonTableBody) {
    // 비교표 데이터가 있으면 테이블 렌더링
    const tableRows = [];
    
    // JSON 객체의 각 키를 행으로 변환
    for (const [key, value] of Object.entries(comparisonTableData)) {
      if (typeof value === 'object' && value !== null) {
        const marketValue = value.market || value.trend || value["29cm"] || "-";
        const companyValue = value.company || value.our || value.ours || value[companyName.toLowerCase()] || "-";
        
        // 키를 한글 레이블로 변환 (예: "주력_아이템" -> "주력 아이템")
        const label = key.replace(/_/g, " ");
        
        tableRows.push(`
          <tr>
            <td class="comparison-label">${label}</td>
            <td class="comparison-market">${marketValue}</td>
            <td class="comparison-company">${companyValue}</td>
          </tr>
        `);
      }
    }
    
    if (tableRows.length > 0) {
      comparisonTableBody.innerHTML = tableRows.join("");
      if (comparisonTableWrapper) {
        comparisonTableWrapper.style.display = "block";
      }
    } else {
      if (comparisonTableWrapper) {
        comparisonTableWrapper.style.display = "none";
      }
    }
  } else {
    // 비교표 데이터가 없으면 숨김
    if (comparisonTableWrapper) {
      comparisonTableWrapper.style.display = "none";
    }
  }
  
  // ============================================
  // 3. 텍스트에서 JSON 블록 제거 (클린업)
  // ============================================
  if (jsonMatch) {
    analysis = analysis.replace(jsonBlockRegex, "").trim();
  }
  
  // ============================================
  // 4. AI 분석 텍스트 렌더링 (JSON 블록 제거된 텍스트)
  // ============================================
  renderAiAnalysis("section7AiAnalysis", analysis);
  
  // ============================================
  // 5. 비교 박스 렌더링 (기존 로직 유지)
  // ============================================
  const marketContent = document.getElementById("section7MarketContent");
  const ourContent = document.getElementById("section7OurContent");
  
  if (analysis) {
    const lines = analysis.split("\n").filter(l => l.trim());
    const marketKeywords = [];
    const ourKeywords = [];
    
    lines.forEach(line => {
      if (line.includes("시장") || line.includes("경쟁사") || line.includes("트렌드") || line.includes("29CM")) {
        marketKeywords.push(line);
      } else if (line.includes("우리") || line.includes("자사") || line.includes(companyName)) {
        ourKeywords.push(line);
      }
    });
    
    if (marketContent) {
      marketContent.innerHTML = marketKeywords.length > 0
        ? marketKeywords.map(kw => `<div class="comparison-keyword">${kw}</div>`).join("")
        : `<div class="comparison-text">분석 데이터 준비 중...</div>`;
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
  const mallSalesForecast = forecast.mall_sales || {};
  
  const container = document.getElementById("section8Forecast");
  if (container) {
    // 작년 동월 매출 (median 값 사용)
    const sameMonthStats = mallSalesForecast.net_sales_same_month_stats || {};
    const lastYearSameMonthSales = sameMonthStats.median || 0;
    
    // 작년 익월 매출 (median 값 사용)
    const nextMonthStats = mallSalesForecast.net_sales_next_month_stats || {};
    const lastYearNextMonthSales = nextMonthStats.median || 0;
    
    // 작년 매출 증감률
    const yoyGrowthPct = mallSalesForecast.yoy_growth_pct;
    
    // 날짜 계산 (현재 리포트 월 기준)
    // 현재 리포트가 2025-12라면:
    // - 작년 동월: 2024-12 (현재 리포트의 작년 동월)
    // - 작년 익월: 2025-01 (다음 달의 작년 동월)
    
    // 작년 동월 날짜 (현재 리포트 월의 작년 동월)
    const lastYear = currentYear - 1;
    const lastYearDateStr = `${lastYear}-${String(currentMonth).padStart(2, '0')}`;
    
    // 작년 익월 날짜 계산 (다음 달의 작년 동월)
    const nextMonthNum = currentMonth === 12 ? 1 : currentMonth + 1;
    const nextYear = currentMonth === 12 ? currentYear : currentYear - 1;
    const lastYearNextMonthStr = `${nextYear}-${String(nextMonthNum).padStart(2, '0')}`;
    
    // 증감률 포맷팅
    let growthDisplay = "데이터 없음";
    let growthClass = "";
    if (yoyGrowthPct !== null && yoyGrowthPct !== undefined) {
      if (yoyGrowthPct > 0) {
        growthDisplay = `+${yoyGrowthPct.toFixed(1)}%`;
        growthClass = "forecast-growth-positive";
      } else if (yoyGrowthPct < 0) {
        growthDisplay = `${yoyGrowthPct.toFixed(1)}%`;
        growthClass = "forecast-growth-negative";
      } else {
        growthDisplay = "0%";
      }
    }
    
    // 3개 카드 렌더링 (섹션 1과 동일한 구조 - grid div는 HTML에 이미 있으므로 카드만 직접 넣음)
    const htmlContent = `
      <div class="forecast-card">
        <div class="forecast-label">작년 동월 매출 (${lastYearDateStr})</div>
        <div class="forecast-value-large">${formatMoney(lastYearSameMonthSales)}</div>
      </div>
      <div class="forecast-card">
        <div class="forecast-label">작년 익월 매출 (${lastYearNextMonthStr})</div>
        <div class="forecast-value-large">${formatMoney(lastYearNextMonthSales)}</div>
      </div>
      <div class="forecast-card">
        <div class="forecast-label">작년 매출 증감</div>
        <div class="forecast-value-large ${growthClass}">${growthDisplay}</div>
      </div>
    `;
    container.innerHTML = htmlContent;
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
  // 원 단위 + 천단위 쉼표로 변경 (만원 단위 제거)
  return `${Math.round(value).toLocaleString()}원`;
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
