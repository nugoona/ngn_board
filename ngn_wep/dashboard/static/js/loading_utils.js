/**
 * 지연 로딩 및 성능 최적화 유틸리티
 * Intersection Observer API를 사용한 스마트 로딩
 */

class LazyLoadManager {
    constructor() {
        this.observers = new Map();
        this.loadedWidgets = new Set();
        this.loadingQueue = [];
        this.isProcessingQueue = false;
        this.loadPriority = {
            'performance-summary': 1,    // 최우선
            'cafe24-sales': 2,
            'cafe24-product-sales': 3,
            'monthly-chart': 4,
            'ga4-source': 5,
            'viewitem-summary': 6,       // 낮은 우선순위
            'platform-sales': 7
        };
        
        this.init();
    }

    init() {
        // Intersection Observer 설정
        this.createObserver();
        
        // 페이지 로드 완료 후 초기화
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializeWidgets());
        } else {
            this.initializeWidgets();
        }

        // 네트워크 상태 감지
        this.setupNetworkOptimization();
    }

    createObserver() {
        const options = {
            root: null,
            rootMargin: '50px 0px 100px 0px', // 뷰포트 진입 전 미리 로딩
            threshold: [0, 0.1, 0.5]
        };

        this.intersectionObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && entry.intersectionRatio > 0) {
                    const widgetId = entry.target.dataset.widgetId;
                    if (widgetId && !this.loadedWidgets.has(widgetId)) {
                        this.scheduleWidgetLoad(widgetId, entry.target);
                    }
                }
            });
        }, options);
    }

    initializeWidgets() {
        // 모든 위젯 컨테이너 찾기
        const widgets = document.querySelectorAll('[data-widget-id]');
        
        widgets.forEach(widget => {
            const widgetId = widget.dataset.widgetId;
            
            // 스켈레톤 로더 표시
            this.showSkeletonLoader(widget);
            
            // Intersection Observer 등록
            this.intersectionObserver.observe(widget);
            
            // 우선순위가 높은 위젯은 즉시 로딩
            if (this.loadPriority[widgetId] <= 2) {
                this.scheduleWidgetLoad(widgetId, widget, true);
            }
        });
    }

    scheduleWidgetLoad(widgetId, element, highPriority = false) {
        if (this.loadedWidgets.has(widgetId)) return;

        const loadTask = {
            widgetId,
            element,
            priority: this.loadPriority[widgetId] || 999,
            timestamp: Date.now()
        };

        if (highPriority) {
            this.loadingQueue.unshift(loadTask);
        } else {
            this.loadingQueue.push(loadTask);
        }

        // 우선순위 정렬
        this.loadingQueue.sort((a, b) => a.priority - b.priority);

        this.processLoadingQueue();
    }

    async processLoadingQueue() {
        if (this.isProcessingQueue || this.loadingQueue.length === 0) return;

        this.isProcessingQueue = true;

        while (this.loadingQueue.length > 0) {
            const task = this.loadingQueue.shift();
            
            if (!this.loadedWidgets.has(task.widgetId)) {
                try {
                    await this.loadWidget(task.widgetId, task.element);
                    this.loadedWidgets.add(task.widgetId);
                    
                    // 로딩 간격 (동시 요청 제한)
                    await this.delay(100);
                } catch (error) {
                    console.error(`[LazyLoad] 위젯 로딩 실패: ${task.widgetId}`, error);
                }
            }
        }

        this.isProcessingQueue = false;
    }

    async loadWidget(widgetId, element) {
        console.log(`[LazyLoad] 위젯 로딩 시작: ${widgetId}`);
        
        const startTime = performance.now();
        
        try {
            // 위젯별 로딩 로직
            switch (widgetId) {
                case 'performance-summary':
                    await this.loadPerformanceSummary();
                    break;
                case 'cafe24-sales':
                    await this.loadCafe24Sales();
                    break;
                case 'cafe24-product-sales':
                    await this.loadCafe24ProductSales();
                    break;
                case 'monthly-chart':
                    await this.loadMonthlyChart();
                    break;
                case 'ga4-source':
                    await this.loadGA4Source();
                    break;
                case 'viewitem-summary':
                    await this.loadViewItemSummary();
                    break;
                case 'platform-sales':
                    await this.loadPlatformSales();
                    break;
                default:
                    console.warn(`[LazyLoad] 알 수 없는 위젯: ${widgetId}`);
            }

            // 스켈레톤 로더 제거
            this.hideSkeletonLoader(element);
            
            const loadTime = performance.now() - startTime;
            console.log(`[LazyLoad] 위젯 로딩 완료: ${widgetId} (${loadTime.toFixed(2)}ms)`);
            
        } catch (error) {
            this.showErrorState(element, widgetId);
            throw error;
        }
    }

    // 개별 위젯 로딩 함수들
    async loadPerformanceSummary() {
        if (typeof fetchPerformanceSummaryData === 'function') {
            return await fetchPerformanceSummaryData();
        }
    }

    async loadCafe24Sales() {
        if (typeof fetchCafe24SalesData === 'function') {
            const request = getRequestData(1, {
                data_type: "cafe24_sales",
                date_type: $("input[name='dateType']:checked").val() || "summary",
                date_sort: $("#dateSort").val() || "desc",
                limit: 30,
            });
            return await fetchCafe24SalesData(request);
        }
    }

    async loadCafe24ProductSales() {
        if (typeof fetchCafe24ProductSalesData === 'function') {
            const request = getRequestData(1, {
                data_type: "cafe24_product_sales",
                sort_by: $("input[name='productSortType']:checked").val() || "item_product_sales",
                limit: 15,
            });
            return await fetchCafe24ProductSalesData(request);
        }
    }

    async loadMonthlyChart() {
        if (typeof fetchMonthlyNetSalesVisitors === 'function') {
            return await fetchMonthlyNetSalesVisitors();
        }
    }

    async loadGA4Source() {
        if (typeof fetchGA4SourceSummary === 'function') {
            return await fetchGA4SourceSummary();
        }
    }

    async loadViewItemSummary() {
        if (typeof fetchViewItemSummary === 'function') {
            return await fetchViewItemSummary();
        }
    }

    async loadPlatformSales() {
        if (typeof fetchPlatformSalesSummary === 'function') {
            return await fetchPlatformSalesSummary();
        }
    }

    // UI 상태 관리
    showSkeletonLoader(element) {
        // 기존 DOM을 보존하고, 오버레이 방식의 스켈레톤을 추가
        if (!element.querySelector('.skeleton-overlay')) {
            // 최초 호출 시, 원본 HTML을 data 속성에 저장 → 이후 복원에 사용
            if (!element.dataset.originalHtml) {
                element.dataset.originalHtml = element.innerHTML;
            }

            // 오버레이 컨테이너 생성
            const overlay = document.createElement('div');
            overlay.className = 'skeleton-overlay';
            overlay.innerHTML = this.createSkeletonLoader();
            overlay.style.position = 'absolute';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.width = '100%';
            overlay.style.height = '100%';
            overlay.style.zIndex = '10';

            // 부모 위치 기준 배치 위해 relative 보장
            if (getComputedStyle(element).position === 'static') {
                element.style.position = 'relative';
            }

            element.appendChild(overlay);
            element.classList.add('loading');
        }
    }

    hideSkeletonLoader(element) {
        const overlay = element.querySelector('.skeleton-overlay');
        if (overlay) overlay.remove();
        element.classList.remove('loading');
    }
    
    // 로딩 오버레이가 DOM을 바꾸는 구 버전에서 복원용 - 호출 시 원본 HTML 복구
    restoreOriginalHtml(element) {
        if (element.dataset.originalHtml) {
            element.innerHTML = element.dataset.originalHtml;
            delete element.dataset.originalHtml;
        }
    }

    showErrorState(element, widgetId) {
        element.innerHTML = `
            <div class="error-state">
                <div class="error-icon">⚠️</div>
                <div class="error-message">위젯 로딩에 실패했습니다</div>
                <button class="retry-btn" onclick="lazyLoader.retryWidget('${widgetId}', this.closest('[data-widget-id]'))">
                    다시 시도
                </button>
            </div>
        `;
        element.classList.add('error');
    }

    createSkeletonLoader() {
        return `
            <div class="skeleton-loader">
                <div class="skeleton-header"></div>
                <div class="skeleton-content">
                    <div class="skeleton-line"></div>
                    <div class="skeleton-line"></div>
                    <div class="skeleton-line short"></div>
                </div>
            </div>
        `;
    }

    // 네트워크 최적화
    setupNetworkOptimization() {
        // 연결 상태 감지
        if ('connection' in navigator) {
            const connection = navigator.connection;
            
            // 느린 연결에서는 로딩 전략 조정
            if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
                this.adjustForSlowConnection();
            }
            
            connection.addEventListener('change', () => {
                if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
                    this.adjustForSlowConnection();
                }
            });
        }
    }

    adjustForSlowConnection() {
        console.log('[LazyLoad] 느린 연결 감지 - 로딩 전략 조정');
        
        // 우선순위가 낮은 위젯들의 로딩 지연
        this.loadingQueue = this.loadingQueue.filter(task => task.priority <= 3);
        
        // 로딩 간격 증가
        this.delay = (ms) => new Promise(resolve => setTimeout(resolve, ms * 2));
    }

    // 유틸리티 함수들
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    retryWidget(widgetId, element) {
        this.loadedWidgets.delete(widgetId);
        element.classList.remove('error');
        this.scheduleWidgetLoad(widgetId, element, true);
    }

    // 수동 위젯 로딩 (긴급한 경우)
    forceLoadWidget(widgetId) {
        const element = document.querySelector(`[data-widget-id="${widgetId}"]`);
        if (element && !this.loadedWidgets.has(widgetId)) {
            this.scheduleWidgetLoad(widgetId, element, true);
        }
    }

    // 성능 모니터링
    getLoadingStats() {
        return {
            loadedWidgets: Array.from(this.loadedWidgets),
            queueLength: this.loadingQueue.length,
            isProcessing: this.isProcessingQueue
        };
    }
}

// 전역 인스턴스 생성
const lazyLoader = new LazyLoadManager();

// 전역 함수로 노출
window.lazyLoader = lazyLoader;

// ✅ 로딩 오버레이 헬퍼 (모듈 export + 글로벌 노출)
export function showLoading(target) {
    const element = typeof target === 'string' ? document.querySelector(target) : target;
    if (!element) return;
    element.style.display = 'flex'; // overlay 보이기
    const loadingIndicator = element.querySelector('.loading-indicator, .spinner');
    if (loadingIndicator) loadingIndicator.style.display = 'block';
    const loadingText = element.querySelector('.loading-text');
    if (loadingText) loadingText.style.display = 'block';
    element.classList.add('loading');
}

export function hideLoading(target) {
    const element = typeof target === 'string' ? document.querySelector(target) : target;
    if (!element) return;
    const loadingIndicator = element.querySelector('.loading-indicator, .spinner');
    if (loadingIndicator) loadingIndicator.style.display = 'none';
    const loadingText = element.querySelector('.loading-text');
    if (loadingText) loadingText.style.display = 'none';
    element.style.display = 'none'; // overlay 숨기기
    element.classList.remove('loading');
}

// 과거 코드 호환성을 위해 window 객체에도 등록
window.showLoading = showLoading;
window.hideLoading = hideLoading;
