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
  
  // 전월 리포트를 보기 위해 1개월 전으로 계산
  const now = new Date();
  const prevMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const year = prevMonth.getFullYear();
  const month = prevMonth.getMonth() + 1;
  
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
    await renderSection2(data); // 2. 주요 유입 채널
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
    'section-3-funnel': () => {
      try {
        renderSection3(data); // 3. 고객 방문 및 구매 여정
      } catch (e) {
        console.error("[월간 리포트] 섹션 3 (고객 방문 및 구매 여정) 렌더링 실패:", e);
      }
    },
    'section-4-products': () => {
      try {
        renderSection4(data); // 4. 자사몰 베스트 상품 성과
      } catch (e) {
        console.error("[월간 리포트] 섹션 4 (자사몰 베스트 상품 성과) 렌더링 실패:", e);
      }
    },
    'section-5-market-trend': () => {
      try {
        renderSection5(data); // 5. 시장 트렌드 확인 (29CM)
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
    '.section-3-funnel',
    '.section-4-products',
    '.section-5-market-trend',
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
  
  // ============================================
  // 스파크라인 데이터 준비 (최근 6개월)
  // ============================================
  const monthly13m = mallSales.monthly_13m || [];
  const recent6Months = monthly13m.slice(-6); // 최근 6개월
  
  // 시작 월과 끝 월 추출
  const startMonth = recent6Months.length > 0 ? recent6Months[0].ym : "";
  const endMonth = recent6Months.length > 0 ? recent6Months[recent6Months.length - 1].ym : "";
  const monthRange = startMonth && endMonth ? `${startMonth} ~ ${endMonth}` : "최근 6개월 추이";
  
  // 각 메트릭별 스파크라인 데이터 추출
  const sparklineData = {
    sales: recent6Months.map(m => m.net_sales || 0),
    orders: recent6Months.map(m => m.total_orders || 0),
    aov: recent6Months.map(m => {
      const orders = m.total_orders || 0;
      const sales = m.net_sales || 0;
      return orders > 0 ? sales / orders : 0;
    })
  };
  
  // 스파크라인 SVG 생성 함수
  function generateSparklineSVG(values, width = 100, height = 30, color = "#0066CC") {
    if (!values || values.length === 0) return "";
    
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1; // 0으로 나누기 방지
    
    const points = values.map((val, idx) => {
      const x = (idx / (values.length - 1)) * width;
      const y = height - ((val - min) / range) * height;
      return `${x},${y}`;
    }).join(" ");
    
    return `
      <svg class="sparkline-svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
        <polyline
          points="${points}"
          fill="none"
          stroke="${color}"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    `;
  }
  
  const scorecardData = [
    {
      label: "월 매출",
      value: formatMoney(netSalesThis),
      prev: formatMoney(netSalesPrev),
      change: comp.net_sales_mom ? formatChange(comp.net_sales_mom.pct) : "-",
      diff: formatMoney(Math.abs(salesDiff)),
      status: comp.net_sales_mom?.pct >= 0 ? "up" : "down",
      sparkline: generateSparklineSVG(sparklineData.sales, 100, 30, comp.net_sales_mom?.pct >= 0 ? "#28a745" : "#dc3545")
    },
    {
      label: "주문 건수",
      value: formatNumber(ordersThis) + "건",
      prev: formatNumber(ordersPrev) + "건",
      change: comp.orders_mom ? formatChange(comp.orders_mom.pct) : "-",
      diff: `${Math.abs(ordersDiff)}건`,
      status: comp.orders_mom?.pct >= 0 ? "up" : "down",
      sparkline: generateSparklineSVG(sparklineData.orders, 100, 30, comp.orders_mom?.pct >= 0 ? "#28a745" : "#dc3545")
    },
    {
      label: "객단가 (AOV)",
      value: formatMoney(aovThis),
      prev: formatMoney(aovPrev),
      change: aovPrev > 0 ? formatChange(((aovThis - aovPrev) / aovPrev) * 100) : "-",
      diff: formatMoney(Math.abs(aovDiff)),
      status: aovThis >= aovPrev ? "up" : "down",
      sparkline: generateSparklineSVG(sparklineData.aov, 100, 30, aovThis >= aovPrev ? "#28a745" : "#dc3545")
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
        <div class="scorecard-sparkline">
          <div class="sparkline-label">${monthRange}</div>
          ${item.sparkline}
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
  
  console.log("[섹션 2] GA4 전체 구조:", ga4);
  console.log("[섹션 2] GA4 this 데이터:", ga4This);
  console.log("[섹션 2] GA4 this 키 목록:", Object.keys(ga4This || {}));
  console.log("[섹션 2] GA4 this 전체 내용:", JSON.stringify(ga4This, null, 2));
  
  // top_sources가 없을 수 있으므로 다른 경로 확인
  let topSources = ga4This.top_sources || ga4This.topSources || [];
  
  console.log("[섹션 2] top_sources (첫 시도):", topSources);
  
  // 대체 경로 시도
  if (topSources.length === 0 && ga4This.sources) {
    topSources = ga4This.sources;
    console.log("[섹션 2] sources 경로 사용:", topSources);
  }
  
  // 추가 경로 시도
  if (topSources.length === 0 && ga4.top_sources) {
    topSources = ga4.top_sources;
    console.log("[섹션 2] ga4.top_sources 경로 사용:", topSources);
  }
  
  console.log("[섹션 2] 최종 topSources:", topSources);
  
  const container = document.getElementById("section2ChannelsTable");
  console.log("[섹션 2] container 요소:", container);
  
  if (container) {
    const total = topSources.reduce((sum, s) => sum + (s.total_users || s.users || s.value || 0), 0);
    console.log("[섹션 2] 계산된 total:", total);
    console.log("[섹션 2] topSources.length:", topSources.length);
    console.log("[섹션 2] topSources 데이터:", topSources);
    
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
      
      console.log("[섹션 2] Top 5 데이터:", top5);
      
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
      console.log("[섹션 2] 표 HTML 생성 완료, container.innerHTML 길이:", container.innerHTML.length);
    } else {
      console.warn("[섹션 2] 데이터가 없거나 total이 0입니다. topSources:", topSources, "total:", total);
      container.innerHTML = `
        <div class="channels-table-empty">
          <div class="empty-text">유입 채널 데이터가 없습니다.</div>
        </div>
      `;
    }
  } else {
    console.error("[섹션 2] container 요소를 찾을 수 없습니다!");
  }
  
  // AI 분석 (섹션 2: 주요 유입 채널)
  renderAiAnalysis("section2AiAnalysis", data.signals?.section_2_analysis);
}

// ============================================
// 섹션 3: 고객 방문 및 구매 여정
// ============================================
function renderSection3(data) {
  console.log("[섹션 3] 데이터 로드 시작", data);
  const facts = data.facts || {};
  const ga4 = facts.ga4_traffic || {};
  const ga4This = ga4.this || {};
  const mallSales = facts.mall_sales || {};
  const salesThis = mallSales.this || {};
  
  console.log("[섹션 3] GA4 전체 구조:", ga4);
  console.log("[섹션 3] GA4 데이터:", ga4This);
  console.log("[섹션 3] GA4 데이터 키 목록:", Object.keys(ga4This || {}));
  console.log("[섹션 3] GA4 데이터 전체 내용:", JSON.stringify(ga4This, null, 2));
  console.log("[섹션 3] 매출 데이터:", salesThis);
  
  // GA4 데이터 매핑 수정 - totals 객체에서 가져오기
  const totals = ga4This.totals || {};
  const visitors = totals.total_users || 0;
  const cartUsers = totals.add_to_cart_users || 0;
  const purchases = salesThis.total_orders || 0;
  
  console.log("[섹션 3] 계산된 값:", { visitors, cartUsers, purchases });
  console.log("[섹션 3] visitors 경로 확인:", {
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
  
  const container = document.getElementById("section3Funnel");
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
  
  // AI 분석 (섹션 3: 고객 방문 및 구매 여정)
  renderAiAnalysis("section3AiAnalysis", data.signals?.section_3_analysis);
}

// ============================================
// 섹션 4: 자사몰 베스트 상품 성과
// ============================================
function renderSection4(data) {
  console.log("[섹션 4] 데이터 로드 시작", data);
  const facts = data.facts || {};
  
  // 구매 데이터 (매출 베스트)
  const products = facts.products || {};
  const productsThis = products.this || {};
  const rolling = productsThis.rolling || {};
  const d30 = rolling.d30 || {};
  const topProductsBySales = d30.top_products_by_sales || [];
  
  // 조회 데이터 (조회수 베스트)
  const viewitem = facts.viewitem || {};
  const viewitemThis = viewitem.this || {};
  const topItemsByView = viewitemThis.top_items_by_view_item || [];
  
  console.log("[섹션 4] top_products_by_sales:", topProductsBySales);
  console.log("[섹션 4] top_items_by_view_item:", topItemsByView);
  
  // 탭 버튼 이벤트 설정
  setupSection4Tabs(data);
  
  // 초기 렌더링 (구매 탭)
  renderSection4ByTab("sales", data);
  
  // AI 분석 (섹션 4: 자사몰 베스트 상품 성과)
  renderAiAnalysis("section4AiAnalysis", data.signals?.section_4_analysis);
}

function setupSection4Tabs(data) {
  const tabButtons = document.querySelectorAll("#section4Tabs .products-tab-btn");
  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const tab = btn.getAttribute("data-tab");
      
      // 활성 탭 변경
      tabButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      
      // 해당 탭 렌더링
      renderSection4ByTab(tab, data);
    });
  });
}

function renderSection4ByTab(tab, data) {
  const facts = data.facts || {};
  const container = document.getElementById("section4BarChart");
  
  if (!container) return;
  
  if (tab === "sales") {
    // 구매 탭: 매출 베스트 5
    const products = facts.products || {};
    const productsThis = products.this || {};
    const rolling = productsThis.rolling || {};
    const d30 = rolling.d30 || {};
    const topProducts = d30.top_products_by_sales || [];
    
    const top5 = topProducts.slice(0, 5);
    const maxSales = top5.length > 0 ? Math.max(...top5.map(p => p.sales || 0)) : 1;
    
    container.innerHTML = top5.map((product, index) => {
      const sales = product.sales || 0;
      const width = maxSales > 0 ? (sales / maxSales) * 100 : 0;
      const name = product.product_name || "상품명 없음";
      
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
  } else if (tab === "views") {
    // 조회 탭: 조회수 베스트 5
    const viewitem = facts.viewitem || {};
    const viewitemThis = viewitem.this || {};
    const topItems = viewitemThis.top_items_by_view_item || [];
    
    const top5 = topItems.slice(0, 5);
    const maxViews = top5.length > 0 ? Math.max(...top5.map(p => p.total_view_item || 0)) : 1;
    
    container.innerHTML = top5.map((item, index) => {
      const views = item.total_view_item || 0;
      const width = maxViews > 0 ? (views / maxViews) * 100 : 0;
      const name = item.item_name_normalized || "상품명 없음";
      
      return `
        <div class="bar-chart-item">
          <div class="bar-chart-label-row">
            <span class="bar-chart-rank">${index + 1}</span>
            <span class="bar-chart-name" title="${name}">${name}</span>
            <span class="bar-chart-value">${formatNumber(views)}회</span>
          </div>
          <div class="bar-chart-bar-wrapper">
            <div class="bar-chart-bar" style="width: ${width}%;"></div>
          </div>
        </div>
      `;
    }).join("");
  }
}

// ============================================
// 섹션 5: 외부 시장 트렌드 (29CM) - Top 5 카드
// ============================================
let section5Data = null;

async function renderSection5(data) {
  const facts = data.facts || {};
  const cm29Data = facts["29cm_best"] || {};
  const items = cm29Data.items || [];
  
  // 디버그: 첫 번째 아이템의 구조 확인
  if (items.length > 0) {
    console.log("[섹션 5] 첫 번째 아이템 데이터 구조:", JSON.stringify(items[0], null, 2));
    console.log("[섹션 5] 첫 번째 아이템의 모든 키:", Object.keys(items[0]));
    console.log("[섹션 5] 첫 번째 아이템의 각 필드 값:", {
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
  
  section5Data = items;
  
  setupSection5Tabs(items);
  renderSection5ByTab("전체", items, 1);
  
  // AI 분석 (섹션 5: 시장 트렌드 확인)
  renderAiAnalysis("section5AiAnalysis", data.signals?.section_5_analysis);
}

function setupSection5Tabs(items) {
  const tabButtons = document.querySelectorAll("#section5Tabs .market-trend-tab-btn");
  
  tabButtons.forEach(btn => {
    btn.addEventListener("click", function() {
      const selectedTab = this.dataset.tab;
      tabButtons.forEach(b => b.classList.remove("active"));
      this.classList.add("active");
      renderSection5ByTab(selectedTab, items, 1); // 페이지 리셋
    });
  });
}

// 섹션 5 페이지네이션 상태
let section5CurrentPage = 1;

function renderSection5ByTab(tabName, items, page = 1) {
  const container = document.getElementById("section5MarketTrend");
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
  
  section5CurrentPage = page;
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
        <button class="market-trend-nav-btn market-trend-nav-prev" onclick="renderSection5ByTab('${tabName}', section5Data, ${page - 1})">
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
                console.warn("[섹션 5] URL과 item_id가 모두 없습니다. item 객체:", item);
              }
            }
          }
          
          // 디버그: 최종 URL 확인
          if (index === 0) {
            console.log("[섹션 5] URL 변환 결과:", {
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
        <button class="market-trend-nav-btn market-trend-nav-next" onclick="renderSection5ByTab('${tabName}', section5Data, ${page + 1})">
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
  const section7Data = signals.section_7_data || null;  // 백엔드에서 구조화된 JSON 데이터
  let analysis = signals.section_7_analysis || "";
  
  // 업체명 가져오기
  const companyName = currentCompany || "업체명";
  
  // ============================================
  // 1. 단일 통합 비교표 렌더링
  // ============================================
  const comparisonTableBody = document.getElementById("section7ComparisonTableBody");
  const defaultComparisonItems = [
    { key: "주력_아이템", label: "주력 아이템" },
    { key: "평균_가격", label: "평균 가격" },
    { key: "핵심_소재", label: "핵심 소재" },
    { key: "타겟_고객층", label: "타겟 고객층" },
    { key: "가격대", label: "가격대" }
  ];
  
  if (comparisonTableBody) {
    const rows = [];
    
    if (section7Data) {
      // 백엔드에서 구조화된 JSON 데이터 사용
      for (const [key, value] of Object.entries(section7Data)) {
        if (typeof value === 'object' && value !== null) {
          const marketValue = value.market || value.trend || value["29cm"] || "-";
          const companyValue = value.company || value.our || value.ours || value[companyName.toLowerCase()] || "-";
          const label = key.replace(/_/g, " ");
          
          rows.push(`
            <tr>
              <td>${label}</td>
              <td>${marketValue}</td>
              <td>${companyValue}</td>
            </tr>
          `);
        }
      }
    } else {
      // 데이터가 없으면 기본 항목 표시
      defaultComparisonItems.forEach(item => {
        rows.push(`
          <tr>
            <td>${item.label}</td>
            <td>-</td>
            <td>-</td>
          </tr>
        `);
      });
    }
    
    comparisonTableBody.innerHTML = rows.join("");
  }
  
  // ============================================
  // 2. AI 분석 텍스트를 두 개 박스로 분리
  // ============================================
  // 백엔드에서 이미 분리된 분석 텍스트 사용
  let leftAnalysis = signals.section_7_analysis_1 || "";
  let rightAnalysis = signals.section_7_analysis_2 || "";
  
  // 하위 호환성: section_7_analysis가 있으면 분리 시도
  if ((!leftAnalysis || !rightAnalysis) && analysis && analysis.trim()) {
    // JSON 코드 블록 제거
    const jsonBlockRegex = /```json\s*[\s\S]*?\s*```/g;
    analysis = analysis.replace(jsonBlockRegex, "").trim();
    const codeBlockRegex = /```[\s\S]*?```/g;
    analysis = analysis.replace(codeBlockRegex, "").trim();
    
    // 더 정확한 패턴 매칭: "29cm 시장은" 또는 "29CM 시장은"으로 시작하는 부분
    // 그리고 "자사몰은" 또는 "자사몰"로 시작하는 부분을 찾기
    const marketStartPatterns = [
      /(?:29cm|29CM)\s*시장[\s은는이가의]?/i,
      /29cm\s*시장[\s은는이가의]?/i,
      /29CM\s*시장[\s은는이가의]?/i
    ];
    
    const companyStartPatterns = [
      /자사몰[\s은는이가의]?/i,
      /(?:우리|본사|회사)[\s은는이가의]?/i
    ];
    
    // "29cm 시장은" 또는 "29CM 시장은"으로 시작하는 위치 찾기
    let marketStartIndex = -1;
    for (const pattern of marketStartPatterns) {
      const match = analysis.search(pattern);
      if (match >= 0) {
        marketStartIndex = match;
        break;
      }
    }
    
    // "자사몰은" 또는 "자사몰"로 시작하는 위치 찾기
    let companyStartIndex = -1;
    for (const pattern of companyStartPatterns) {
      const match = analysis.search(pattern);
      if (match >= 0 && match > marketStartIndex) {
        companyStartIndex = match;
        break;
      }
    }
    
    // 두 위치를 모두 찾은 경우
    if (marketStartIndex >= 0 && companyStartIndex > marketStartIndex) {
      leftAnalysis = analysis.substring(marketStartIndex, companyStartIndex).trim();
      rightAnalysis = analysis.substring(companyStartIndex).trim();
    } else if (marketStartIndex >= 0) {
      // 시장 부분만 찾은 경우
      leftAnalysis = analysis.substring(marketStartIndex).trim();
      rightAnalysis = analysis.substring(0, marketStartIndex).trim();
    } else if (companyStartIndex >= 0) {
      // 자사몰 부분만 찾은 경우
      rightAnalysis = analysis.substring(companyStartIndex).trim();
      leftAnalysis = analysis.substring(0, companyStartIndex).trim();
    } else {
      // 패턴 매칭이 실패한 경우, 텍스트를 중간에서 분할
      const midPoint = Math.floor(analysis.length / 2);
      // 문단 구분자로 분할 시도
      const splitPoint = analysis.lastIndexOf('\n\n', midPoint);
      
      if (splitPoint > 0 && splitPoint < analysis.length * 0.8) {
        leftAnalysis = analysis.substring(0, splitPoint).trim();
        rightAnalysis = analysis.substring(splitPoint).trim();
      } else {
        // 단순히 중간에서 분할
        leftAnalysis = analysis.substring(0, midPoint).trim();
        rightAnalysis = analysis.substring(midPoint).trim();
      }
    }
  }
  
  // 왼쪽 박스 렌더링 (29CM 시장 분석)
  const leftContainer = document.getElementById("section7AnalysisLeft");
  if (leftContainer) {
    if (leftAnalysis && leftAnalysis.trim()) {
      renderAiAnalysis("section7AnalysisLeft", leftAnalysis);
    } else {
      leftContainer.innerHTML = `
        <div class="ai-analysis-skeleton">
          <div class="skeleton-line"></div>
          <div class="skeleton-line"></div>
          <div class="skeleton-line short"></div>
        </div>
      `;
    }
  }
  
  // 오른쪽 박스 렌더링 (자사몰 분석)
  const rightContainer = document.getElementById("section7AnalysisRight");
  if (rightContainer) {
    if (rightAnalysis && rightAnalysis.trim()) {
      renderAiAnalysis("section7AnalysisRight", rightAnalysis);
    } else {
      rightContainer.innerHTML = `
        <div class="ai-analysis-skeleton">
          <div class="skeleton-line"></div>
          <div class="skeleton-line"></div>
          <div class="skeleton-line short"></div>
        </div>
      `;
    }
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
// 섹션 9: AI 제안 전략 액션 (카드 그리드 레이아웃)
// ============================================
function renderSection9(data) {
  const signals = data.signals || {};
  const cards = signals.section_9_cards || [];  // 백엔드에서 구조화된 카드 배열
  const analysis = signals.section_9_analysis || "";  // Fallback: 카드가 없을 때 원본 텍스트 사용
  
  const container = document.getElementById("section9StrategyCards");
  if (container) {
    if (cards && cards.length > 0) {
      // 카드들을 3열 그리드로 렌더링
      const cardsHtml = cards.map((card, index) => {
        const title = card.title || `전략 ${index + 1}`;
        const content = card.content || "";
        
        // 마크다운을 HTML로 변환
        let htmlContent = "";
        
        if (content && content.trim()) {
          if (typeof marked !== 'undefined') {
            try {
              marked.setOptions({
                breaks: true,
                gfm: true  // GitHub Flavored Markdown 활성화 (표 지원)
              });
              
              const markdownHtml = marked.parse(content);
              
              if (typeof DOMPurify !== 'undefined') {
                htmlContent = DOMPurify.sanitize(markdownHtml, {
                  ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
                  ALLOWED_ATTR: []
                });
              } else {
                htmlContent = markdownHtml;
              }
            } catch (e) {
              console.warn("[섹션 9] 마크다운 변환 실패:", e);
              htmlContent = content.replace(/\n/g, '<br>');
            }
          } else {
            htmlContent = content.replace(/\n/g, '<br>');
          }
        }
        
        // 제목 정리: ###, 이모지, [전략 N] 패턴, 마크다운 문법 제거
        let cleanTitle = title
          .replace(/^###\s*/, '') // ### 제거
          .replace(/^#+\s*/, '') // 다른 # 마크다운 헤더도 제거
          .replace(/^[💡🎯📦🚀⭐🔥]\s*/, '') // 앞쪽 이모지 제거
          .replace(/\[전략\s*\d+\]\s*/i, '') // [전략 1] 패턴 제거
          .replace(/\*\*/g, '') // ** 마크다운 굵게 제거
          .replace(/\*/g, '') // * 마크다운 제거
          .trim();
        
        // 아이콘 선택 (제목과 무관하게 인덱스 기반으로 선택)
        const icons = ['💡', '🎯', '📦', '🚀', '⭐', '🔥'];
        const icon = icons[index % icons.length];
        
        return `
          <div class="strategy-card">
            <div class="strategy-card-header">
              <span class="strategy-card-icon">${icon}</span>
              <h4 class="strategy-card-title">${cleanTitle}</h4>
            </div>
            <div class="strategy-card-content markdown-content">${htmlContent || "내용 없음"}</div>
          </div>
        `;
      }).join("");
      
      container.innerHTML = cardsHtml;
    } else if (analysis && analysis.trim()) {
      // 카드가 없지만 원본 분석 텍스트가 있는 경우 (Fallback)
      // 원본 텍스트를 마크다운으로 렌더링
      let htmlContent = "";
      
      if (typeof marked !== 'undefined') {
        try {
          marked.setOptions({
            breaks: true,
            gfm: true
          });
          
          const markdownHtml = marked.parse(analysis);
          
          if (typeof DOMPurify !== 'undefined') {
            htmlContent = DOMPurify.sanitize(markdownHtml, {
              ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
              ALLOWED_ATTR: []
            });
          } else {
            htmlContent = markdownHtml;
          }
        } catch (e) {
          console.warn("[섹션 9] 마크다운 변환 실패:", e);
          htmlContent = analysis.replace(/\n/g, '<br>');
        }
      } else {
        htmlContent = analysis.replace(/\n/g, '<br>');
      }
      
      container.innerHTML = `
        <div class="strategy-card">
          <div class="strategy-card-content markdown-content">${htmlContent}</div>
        </div>
      `;
    } else {
      // 카드 데이터와 원본 텍스트 모두 없을 때
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
// AI 분석 렌더링 (공통) - 마크다운 지원
// ============================================
// 섹션 7 전용 AI 분석 렌더링 함수 (comparison-ai-content 클래스 사용)
function renderAiAnalysisForSection7(element, analysisText) {
  if (!element || !analysisText || !analysisText.trim()) {
    if (element) {
      element.innerHTML = `<div class="comparison-ai-content">분석 데이터 준비 중...</div>`;
    }
    return;
  }
  
  // 마크다운을 HTML로 변환 (marked 라이브러리 사용)
  let htmlContent = "";
  
  if (typeof marked !== 'undefined') {
    // marked 라이브러리가 로드된 경우
    try {
      // 마크다운 설정: 표(Table)는 제외 (시스템 프롬프트 요구사항)
      marked.setOptions({
        breaks: true,  // 줄바꿈 지원
        gfm: false     // GitHub Flavored Markdown 비활성화 (표 제외)
      });
      
      // 마크다운을 HTML로 변환
      const markdownHtml = marked.parse(analysisText);
      
      // XSS 방지를 위해 DOMPurify로 정제
      if (typeof DOMPurify !== 'undefined') {
        htmlContent = DOMPurify.sanitize(markdownHtml, {
          ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre'],
          ALLOWED_ATTR: []
        });
      } else {
        htmlContent = markdownHtml;
      }
    } catch (e) {
      console.warn("[섹션 7 AI 분석] 마크다운 변환 실패, 일반 텍스트로 표시:", e);
      // 마크다운 변환 실패 시 일반 텍스트로 표시 (줄바꿈만 처리)
      htmlContent = analysisText.replace(/\n/g, '<br>');
    }
  } else {
    // marked 라이브러리가 없는 경우 줄바꿈만 처리
    htmlContent = analysisText.replace(/\n/g, '<br>');
  }
  
  element.innerHTML = `<div class="comparison-ai-content markdown-content">${htmlContent}</div>`;
}

function renderAiAnalysis(elementId, analysisText) {
  const element = document.getElementById(elementId);
  if (!element) {
    console.warn(`[AI 분석] 요소를 찾을 수 없습니다: ${elementId}`);
    return;
  }
  
  if (analysisText && analysisText.trim()) {
    // 에러 메시지 감지
    if (analysisText.includes("[AI 분석 오류:") || analysisText.includes("AI 분석 오류")) {
      element.innerHTML = `
        <div class="ai-analysis-error">
          <div class="error-icon">⚠️</div>
          <div class="error-text">${analysisText.replace(/\[AI 분석 오류:.*?\]/g, "").trim() || "AI 분석 중 오류가 발생했습니다."}</div>
        </div>
      `;
      return;
    }
    
    // 마크다운을 HTML로 변환 (marked 라이브러리 사용)
    let htmlContent = "";
    
    if (typeof marked !== 'undefined') {
      // marked 라이브러리가 로드된 경우
      try {
        // 마크다운 설정: 표(Table) 지원 활성화
        marked.setOptions({
          breaks: true,  // 줄바꿈 지원
          gfm: true      // GitHub Flavored Markdown 활성화 (표 지원)
        });
        
        // 마크다운을 HTML로 변환
        const markdownHtml = marked.parse(analysisText);
        
        // XSS 방지를 위해 DOMPurify로 정제 (표 관련 태그 포함)
        if (typeof DOMPurify !== 'undefined') {
          htmlContent = DOMPurify.sanitize(markdownHtml, {
            ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
            ALLOWED_ATTR: []
          });
        } else {
          htmlContent = markdownHtml;
        }
      } catch (e) {
        console.warn("[AI 분석] 마크다운 변환 실패, 일반 텍스트로 표시:", e);
        // 마크다운 변환 실패 시 일반 텍스트로 표시 (줄바꿈만 처리)
        htmlContent = analysisText.replace(/\n/g, '<br>');
      }
    } else {
      // marked 라이브러리가 없는 경우 줄바꿈만 처리
      htmlContent = analysisText.replace(/\n/g, '<br>');
    }
    
    element.innerHTML = `<div class="ai-analysis-text markdown-content">${htmlContent}</div>`;
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
