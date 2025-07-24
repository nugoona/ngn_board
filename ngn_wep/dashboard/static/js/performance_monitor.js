/**
 * 성능 모니터링 시스템
 * 로딩 시간, 캐시 히트율, 위젯 성능 추적
 */

class PerformanceMonitor {
    constructor() {
        this.metrics = {
            pageLoadStart: performance.now(),
            widgetLoadTimes: new Map(),
            cacheStats: { hits: 0, misses: 0 },
            apiCalls: [],
            errorCount: 0,
            totalRequests: 0
        };
        
        this.observers = {
            performance: new PerformanceObserver(this.handlePerformanceEntry.bind(this)),
            intersection: null
        };
        
        this.isEnabled = this.shouldEnable();
        
        if (this.isEnabled) {
            this.init();
        }
    }

    shouldEnable() {
        // 개발 환경에서만 활성화
        return (
            window.location.hostname === 'localhost' ||
            window.location.hostname.includes('dev') ||
            window.location.search.includes('debug=true') ||
            localStorage.getItem('performance_monitor') === 'enabled'
        );
    }

    init() {
        this.createMonitorUI();
        this.startObserving();
        this.interceptNetworkRequests();
        this.trackPagePerformance();
        
        // 주기적 업데이트
        setInterval(() => this.updateMonitorDisplay(), 1000);
        
        console.log('[PerformanceMonitor] 성능 모니터링 시작됨');
    }

    createMonitorUI() {
        const monitor = document.createElement('div');
        monitor.id = 'performanceMonitor';
        monitor.className = 'performance-monitor show';
        monitor.innerHTML = `
            <div class="monitor-header">
                <span>🔍 성능 모니터</span>
                <button class="monitor-toggle" onclick="performanceMonitor.toggleExpanded()">
                    <span id="monitorToggleIcon">▼</span>
                </button>
            </div>
            <div class="monitor-content" id="monitorContent">
                <div class="monitor-section">
                    <div class="monitor-title">페이지 성능</div>
                    <div class="monitor-item">
                        <span>로딩 시간:</span>
                        <span id="pageLoadTime">측정 중...</span>
                    </div>
                    <div class="monitor-item">
                        <span>FCP:</span>
                        <span id="fcpTime">-</span>
                    </div>
                    <div class="monitor-item">
                        <span>LCP:</span>
                        <span id="lcpTime">-</span>
                    </div>
                </div>

                <div class="monitor-section">
                    <div class="monitor-title">위젯 성능</div>
                    <div class="monitor-item">
                        <span>로딩된 위젯:</span>
                        <span id="loadedWidgetCount">0</span>
                    </div>
                    <div class="monitor-item">
                        <span>대기 중:</span>
                        <span id="queueLength">0</span>
                    </div>
                    <div class="monitor-item">
                        <span>평균 로딩 시간:</span>
                        <span id="avgLoadTime">-</span>
                    </div>
                </div>

                <div class="monitor-section">
                    <div class="monitor-title">캐시 성능</div>
                    <div class="monitor-item">
                        <span>캐시 히트율:</span>
                        <span id="cacheHitRate">-</span>
                    </div>
                    <div class="monitor-item">
                        <span>캐시 키 수:</span>
                        <span id="cacheKeyCount">-</span>
                    </div>
                    <div class="monitor-item">
                        <span>메모리 사용량:</span>
                        <span id="cacheMemoryUsage">-</span>
                    </div>
                </div>

                <div class="monitor-section">
                    <div class="monitor-title">네트워크</div>
                    <div class="monitor-item">
                        <span>API 호출:</span>
                        <span id="apiCallCount">0</span>
                    </div>
                    <div class="monitor-item">
                        <span>평균 응답 시간:</span>
                        <span id="avgResponseTime">-</span>
                    </div>
                    <div class="monitor-item">
                        <span>에러 수:</span>
                        <span id="errorCount">0</span>
                    </div>
                </div>

                <div class="monitor-actions">
                    <button onclick="performanceMonitor.exportMetrics()">📊 내보내기</button>
                    <button onclick="performanceMonitor.clearMetrics()">🗑️ 초기화</button>
                    <button onclick="performanceMonitor.toggleConsoleLogging()">
                        <span id="consoleToggleText">콘솔 로깅 켜기</span>
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(monitor);
    }

    startObserving() {
        // Performance Observer 시작
        try {
            this.observers.performance.observe({ 
                entryTypes: ['navigation', 'paint', 'largest-contentful-paint', 'first-input'] 
            });
        } catch (e) {
            console.warn('[PerformanceMonitor] Performance Observer 지원하지 않음:', e);
        }
    }

    handlePerformanceEntry(list) {
        const entries = list.getEntries();
        
        entries.forEach(entry => {
            switch (entry.entryType) {
                case 'paint':
                    if (entry.name === 'first-contentful-paint') {
                        this.updateMetric('fcpTime', `${entry.startTime.toFixed(0)}ms`);
                    }
                    break;
                case 'largest-contentful-paint':
                    this.updateMetric('lcpTime', `${entry.startTime.toFixed(0)}ms`);
                    break;
                case 'navigation':
                    const loadTime = entry.loadEventEnd - entry.fetchStart;
                    this.updateMetric('pageLoadTime', `${loadTime.toFixed(0)}ms`);
                    break;
            }
        });
    }

    interceptNetworkRequests() {
        const originalFetch = window.fetch;
        const self = this;

        window.fetch = function(...args) {
            const startTime = performance.now();
            self.metrics.totalRequests++;

            return originalFetch.apply(this, args)
                .then(response => {
                    const endTime = performance.now();
                    const duration = endTime - startTime;
                    
                    self.metrics.apiCalls.push({
                        url: args[0],
                        method: args[1]?.method || 'GET',
                        status: response.status,
                        duration: duration,
                        timestamp: Date.now()
                    });

                    // 캐시 히트/미스 감지
                    if (args[0].includes('/dashboard/get_data')) {
                        self.detectCacheHit(response, duration);
                    }

                    return response;
                })
                .catch(error => {
                    self.metrics.errorCount++;
                    console.error('[PerformanceMonitor] API 호출 실패:', error);
                    throw error;
                });
        };
    }

    detectCacheHit(response, duration) {
        // 빠른 응답 시간 = 캐시 히트 가능성
        if (duration < 100) {
            this.metrics.cacheStats.hits++;
        } else {
            this.metrics.cacheStats.misses++;
        }
    }

    trackPagePerformance() {
        // 페이지 로드 완료 시점 측정
        window.addEventListener('load', () => {
            const loadTime = performance.now() - this.metrics.pageLoadStart;
            this.updateMetric('pageLoadTime', `${loadTime.toFixed(0)}ms`);
        });

        // 메모리 사용량 추적 (지원하는 브라우저에서만)
        if ('memory' in performance) {
            setInterval(() => {
                const memory = performance.memory;
                const usedMB = (memory.usedJSHeapSize / 1024 / 1024).toFixed(1);
                this.updateMetric('memoryUsage', `${usedMB}MB`);
            }, 5000);
        }
    }

    updateMonitorDisplay() {
        if (!this.isEnabled) return;

        // 위젯 통계 업데이트
        if (window.lazyLoader) {
            const stats = lazyLoader.getLoadingStats();
            this.updateMetric('loadedWidgetCount', stats.loadedWidgets.length);
            this.updateMetric('queueLength', stats.queueLength);

            // 평균 로딩 시간 계산
            if (this.metrics.widgetLoadTimes.size > 0) {
                const times = Array.from(this.metrics.widgetLoadTimes.values());
                const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
                this.updateMetric('avgLoadTime', `${avgTime.toFixed(0)}ms`);
            }
        }

        // 캐시 통계 업데이트
        this.updateCacheStats();

        // 네트워크 통계 업데이트
        this.updateNetworkStats();
    }

    async updateCacheStats() {
        try {
            const response = await fetch('/dashboard/cache/stats');
            const data = await response.json();
            
            if (data.status === 'success' && data.cache_stats) {
                const stats = data.cache_stats;
                this.updateMetric('cacheKeyCount', stats.keys_count || 0);
                this.updateMetric('cacheMemoryUsage', stats.memory_used || 'N/A');
            }

            // 히트율 계산
            const total = this.metrics.cacheStats.hits + this.metrics.cacheStats.misses;
            if (total > 0) {
                const hitRate = ((this.metrics.cacheStats.hits / total) * 100).toFixed(1);
                this.updateMetric('cacheHitRate', `${hitRate}%`);
            }
        } catch (error) {
            this.updateMetric('cacheHitRate', '오류');
        }
    }

    updateNetworkStats() {
        this.updateMetric('apiCallCount', this.metrics.apiCalls.length);
        this.updateMetric('errorCount', this.metrics.errorCount);

        if (this.metrics.apiCalls.length > 0) {
            const avgResponseTime = this.metrics.apiCalls.reduce((sum, call) => sum + call.duration, 0) / this.metrics.apiCalls.length;
            this.updateMetric('avgResponseTime', `${avgResponseTime.toFixed(0)}ms`);
        }
    }

    updateMetric(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }

    recordWidgetLoadTime(widgetId, loadTime) {
        this.metrics.widgetLoadTimes.set(widgetId, loadTime);
    }

    toggleExpanded() {
        const content = document.getElementById('monitorContent');
        const icon = document.getElementById('monitorToggleIcon');
        
        if (content.style.display === 'none') {
            content.style.display = 'block';
            icon.textContent = '▼';
        } else {
            content.style.display = 'none';
            icon.textContent = '▶';
        }
    }

    exportMetrics() {
        const metrics = {
            timestamp: new Date().toISOString(),
            pagePerformance: {
                loadTime: this.metrics.pageLoadStart,
                widgetLoadTimes: Object.fromEntries(this.metrics.widgetLoadTimes)
            },
            cacheStats: this.metrics.cacheStats,
            networkStats: {
                totalRequests: this.metrics.totalRequests,
                apiCalls: this.metrics.apiCalls.slice(-10), // 최근 10개만
                errorCount: this.metrics.errorCount
            }
        };

        const blob = new Blob([JSON.stringify(metrics, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `performance-metrics-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    clearMetrics() {
        this.metrics = {
            pageLoadStart: performance.now(),
            widgetLoadTimes: new Map(),
            cacheStats: { hits: 0, misses: 0 },
            apiCalls: [],
            errorCount: 0,
            totalRequests: 0
        };

        console.log('[PerformanceMonitor] 메트릭 초기화됨');
    }

    toggleConsoleLogging() {
        const isEnabled = localStorage.getItem('performance_console_logging') === 'true';
        localStorage.setItem('performance_console_logging', !isEnabled);
        
        const toggleText = document.getElementById('consoleToggleText');
        toggleText.textContent = isEnabled ? '콘솔 로깅 켜기' : '콘솔 로깅 끄기';
    }

    log(message, data = null) {
        if (localStorage.getItem('performance_console_logging') === 'true') {
            console.log(`[PerformanceMonitor] ${message}`, data);
        }
    }
}

// 전역 인스턴스 생성
const performanceMonitor = new PerformanceMonitor();

// 전역 함수로 노출
window.performanceMonitor = performanceMonitor; 