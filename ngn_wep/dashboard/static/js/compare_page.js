/**
 * 29CM 경쟁사 비교 페이지 JavaScript
 */
(function() {
    'use strict';
    
    // 전역 변수
    let currentCompanyName = null;
    let currentRunId = null;
    let currentBrandId = null;  // brandId 기반으로 변경
    let ownBrandId = null;  // 자사몰 브랜드 ID
    let allBrands = [];  // 경쟁사 브랜드 목록
    let currentResults = [];
    let allResultsCache = {};  // 모든 브랜드 데이터 캐시
    let snapshotCreatedAt = null;  // 스냅샷 수집 시간
    let currentPage = 1;
    const ITEMS_PER_PAGE = 10;
    
    // DOM 요소
    const compareToggleBtn = document.getElementById('trendCompareToggleBtn');
    const compareSidebar = document.getElementById('compareSidebar');
    const closeCompareBtn = document.getElementById('closeCompareSidebarBtn');
    const compareTabs = document.getElementById('compareTabs');
    const compareCardsContainer = document.getElementById('compareCardsContainer');
    const comparePagination = document.getElementById('comparePagination');
    const comparePrevBtn = document.getElementById('comparePrevBtn');
    const compareNextBtn = document.getElementById('compareNextBtn');
    const comparePageInfo = document.getElementById('comparePageInfo');
    
    // 리뷰 모달
    const reviewModal = document.getElementById('compareReviewModal');
    const closeReviewModalBtn = document.getElementById('closeCompareReviewModalBtn');
    const reviewModalTitle = document.getElementById('compareReviewModalTitle');
    const reviewModalBody = document.getElementById('compareReviewModalBody');
    
    /**
     * 초기화
     */
    function init() {
        // URL에서 company_name 가져오기
        const urlParams = new URLSearchParams(window.location.search);
        currentCompanyName = urlParams.get('company_name');
        
        if (!currentCompanyName) {
            console.warn('[Compare] company_name이 없습니다.');
            return;
        }
        
        // 이벤트 리스너 등록
        setupEventListeners();
    }
    
    /**
     * 이벤트 리스너 설정
     */
    function setupEventListeners() {
        // Compare 버튼 클릭
        if (compareToggleBtn) {
            compareToggleBtn.addEventListener('click', function() {
                openCompareSidebar();
            });
        }
        
        // 사이드바 닫기
        if (closeCompareBtn) {
            closeCompareBtn.addEventListener('click', function() {
                closeCompareSidebar();
            });
        }
        
        // 리뷰 모달 닫기
        if (closeReviewModalBtn) {
            closeReviewModalBtn.addEventListener('click', function() {
                closeReviewModal();
            });
        }
        
        // 모달 오버레이 클릭 시 닫기
        const modalOverlay = reviewModal?.querySelector('.compare-review-modal-overlay');
        if (modalOverlay) {
            modalOverlay.addEventListener('click', function() {
                closeReviewModal();
            });
        }
        
        // 페이지네이션 버튼
        if (comparePrevBtn) {
            comparePrevBtn.addEventListener('click', function() {
                if (currentPage > 1) {
                    currentPage--;
                    renderCards();
                }
            });
        }
        
        if (compareNextBtn) {
            compareNextBtn.addEventListener('click', function() {
                const maxPage = Math.ceil(currentResults.length / ITEMS_PER_PAGE);
                if (currentPage < maxPage) {
                    currentPage++;
                    renderCards();
                }
            });
        }
    }
    
    /**
     * Compare 사이드바 열기
     */
    async function openCompareSidebar() {
        if (!currentCompanyName) {
            alert('업체를 먼저 선택해주세요.');
            return;
        }
        
        // 이미 열려있으면 데이터만 새로고침
        if (compareSidebar && compareSidebar.classList.contains('active')) {
            await loadCompareData();
            return;
        }
        
        // Insights 사이드바가 열려있으면 닫기
        const insightsSidebar = document.getElementById('trendAnalysisSidebar');
        if (insightsSidebar && insightsSidebar.classList.contains('active')) {
            insightsSidebar.classList.remove('active');
            setTimeout(() => {
                insightsSidebar.classList.add('hidden');
            }, 300);
        }
        
        // Compare 사이드바 열기
        compareSidebar.classList.remove('hidden');
        setTimeout(() => {
            compareSidebar.classList.add('active');
        }, 10);
        
        // 데이터 로드
        await loadCompareData();
    }
    
    /**
     * Compare 사이드바 닫기
     */
    function closeCompareSidebar() {
        compareSidebar.classList.remove('active');
        setTimeout(() => {
            compareSidebar.classList.add('hidden');
        }, 300);
    }
    
    /**
     * 비교 데이터 로드
     */
    async function loadCompareData() {
        try {
            showLoading();

            // 1. 경쟁사 브랜드 목록 조회 (brandId 기반)
            const brandsResponse = await fetch(`/dashboard/compare/29cm/brands?company_name=${encodeURIComponent(currentCompanyName)}`);
            const brandsData = await brandsResponse.json();

            if (brandsData.status !== 'success') {
                throw new Error(brandsData.message || '브랜드 목록 조회 실패');
            }

            ownBrandId = brandsData.own_brand_id;  // 자사몰 브랜드 ID
            allBrands = brandsData.brands || [];  // 경쟁사 브랜드 목록
            
            // 2. run_id 조회 (최신 주차) - 최적화된 API 사용
            const runIdResponse = await fetch('/dashboard/compare/29cm/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    company_name: currentCompanyName,
                    get_run_id_only: true
                })
            });
            const runIdData = await runIdResponse.json();
            
            if (runIdData.status !== 'success' || !runIdData.run_id) {
                throw new Error('주차 정보를 찾을 수 없습니다.');
            }
            
            currentRunId = runIdData.run_id;
            
            // 3. 기준 정보 업데이트
            updateInfoBar();
            
            // 4. 탭 렌더링
            renderTabs();
            
            // 5. 모든 검색어 데이터를 한 번에 로드 (초기 로드 최적화)
            await loadAllSearchResults();
            
            // 6. 첫 번째 탭 선택 (자사몰)
            await selectOwnCompanyTab();
            
        } catch (error) {
            console.error('[Compare] 데이터 로드 실패:', error);
            showError(error.message || '데이터를 불러오는 중 오류가 발생했습니다.');
        }
    }
    
    /**
     * 탭 렌더링
     */
    function renderTabs() {
        if (!compareTabs) return;

        // 기존 탭 모두 제거 (중복 방지)
        compareTabs.innerHTML = '';

        // 자사몰 탭 추가 (첫 번째)
        const companyTab = document.createElement('button');
        companyTab.className = 'compare-tab-btn active';
        companyTab.dataset.brandId = ownBrandId || 'own';
        companyTab.textContent = getCompanyDisplayName();
        companyTab.addEventListener('click', function() {
            selectOwnCompanyTab();
        });
        compareTabs.appendChild(companyTab);

        // 경쟁사 탭 추가 (brandId 기반)
        allBrands.forEach((brand, index) => {
            const tab = document.createElement('button');
            tab.className = 'compare-tab-btn';
            tab.dataset.brandId = brand.brand_id;
            tab.textContent = brand.display_name || brand.brand_name || `브랜드 ${brand.brand_id}`;
            tab.addEventListener('click', function() {
                selectTab(brand.brand_id, brand.display_name || brand.brand_name);
            });
            compareTabs.appendChild(tab);
        });
    }
    
    /**
     * 자사몰 표시명 가져오기
     */
    function getCompanyDisplayName() {
        // company_mapping에서 한글명 가져오기
        // 임시로 company_name 사용
        return currentCompanyName || '자사몰';
    }
    
    /**
     * 자사몰 탭 선택
     */
    async function selectOwnCompanyTab() {
        // 탭 활성화
        const tabs = compareTabs.querySelectorAll('.compare-tab-btn');
        tabs.forEach(tab => {
            const tabBrandId = tab.dataset.brandId;
            if (tabBrandId === String(ownBrandId) || tabBrandId === 'own') {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        currentBrandId = ownBrandId || 'own';
        currentPage = 1;

        // 자사몰 검색 (brand_id 사용)
        await loadSearchResults(currentBrandId, true);
    }

    /**
     * 탭 선택 (brandId 기반)
     */
    async function selectTab(brandId, displayName) {
        // 탭 활성화
        const tabs = compareTabs.querySelectorAll('.compare-tab-btn');
        tabs.forEach(tab => {
            if (String(tab.dataset.brandId) === String(brandId)) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        currentBrandId = brandId;
        currentPage = 1;

        // 검색 결과 로드
        await loadSearchResults(brandId, false);
    }
    
    /**
     * 모든 검색어 데이터를 한 번에 로드 (초기 로드 최적화)
     */
    async function loadAllSearchResults() {
        try {
            // 캐시 키 생성
            const cacheKey = `${currentCompanyName}_${currentRunId}`;
            
            // 캐시에 있으면 재사용
            if (allResultsCache[cacheKey]) {
                return;
            }
            
            // 모든 검색어 데이터를 한 번에 로드 (search_keyword 없이 호출하면 전체 반환)
            const response = await fetch('/dashboard/compare/29cm/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    company_name: currentCompanyName,
                    run_id: currentRunId
                    // search_keyword 없음 = 전체 데이터 요청
                })
            });
            
            const data = await response.json();
            
            if (data.status !== 'success') {
                throw new Error(data.message || '검색 결과 조회 실패');
            }
            
            // 전체 결과를 캐시에 저장
            allResultsCache[cacheKey] = data.results || {};
            
            // 수집 시간 저장
            if (data.created_at) {
                snapshotCreatedAt = data.created_at;
                updateInfoBar();  // 수집 시간으로 정보 바 업데이트
            }
            
        } catch (error) {
            console.error('[Compare] 전체 검색 결과 로드 실패:', error);
            // 에러가 나도 계속 진행 (개별 로드로 fallback)
        }
    }
    
    /**
     * 검색 결과 로드 (brandId 기반, 캐시 우선 사용)
     */
    async function loadSearchResults(brandId, isOwnMall = false) {
        try {
            showLoading();

            // 캐시 키 생성
            const cacheKey = `${currentCompanyName}_${currentRunId}`;
            const brandKey = String(brandId);

            // 캐시에서 먼저 확인
            if (allResultsCache[cacheKey] && allResultsCache[cacheKey][brandKey]) {
                currentResults = allResultsCache[cacheKey][brandKey];
                renderCards();
                return;
            }

            // 캐시에 없으면 API 호출 (brand_id 기반)
            const requestBody = {
                company_name: currentCompanyName,
                run_id: currentRunId
            };

            // brand_id 또는 'own' 전달
            if (isOwnMall && (brandId === 'own' || !brandId)) {
                requestBody.brand_id = 'own';
            } else {
                requestBody.brand_id = brandId;
            }

            const response = await fetch('/dashboard/compare/29cm/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();

            if (data.status !== 'success') {
                throw new Error(data.message || '검색 결과 조회 실패');
            }

            currentResults = data.results || [];

            // 수집 시간 저장
            if (data.created_at) {
                snapshotCreatedAt = data.created_at;
                updateInfoBar();
            }

            // 캐시에 저장
            if (!allResultsCache[cacheKey]) {
                allResultsCache[cacheKey] = {};
            }
            allResultsCache[cacheKey][brandKey] = currentResults;

            // 카드 렌더링
            renderCards();

        } catch (error) {
            console.error('[Compare] 검색 결과 로드 실패:', error);
            showError(error.message || '검색 결과를 불러오는 중 오류가 발생했습니다.');
        }
    }
    
    /**
     * 기준 정보 업데이트
     */
    function updateInfoBar() {
        const infoBar = document.getElementById('compareInfoBar');
        const infoText = document.getElementById('compareInfoText');
        
        if (!infoBar || !infoText) return;
        
        let dateTimeStr;
        
        // 수집 시간이 있으면 사용, 없으면 현재 시간 사용
        if (snapshotCreatedAt) {
            // ISO 형식의 날짜 문자열을 파싱 (자동으로 로컬 시간으로 변환됨)
            const collectedDate = new Date(snapshotCreatedAt);
            
            const year = collectedDate.getFullYear();
            const month = String(collectedDate.getMonth() + 1).padStart(2, '0');
            const day = String(collectedDate.getDate()).padStart(2, '0');
            const hours = collectedDate.getHours();
            const minutes = String(collectedDate.getMinutes()).padStart(2, '0');
            
            const ampm = hours < 12 ? '오전' : '오후';
            const displayHours = hours % 12 || 12;
            
            dateTimeStr = `${year}년 ${month}-${day} ${ampm} ${displayHours}시${minutes !== '00' ? minutes + '분' : ''}`;
        } else {
            // 현재 날짜/시간 포맷팅 (fallback)
            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            
            const ampm = now.getHours() < 12 ? '오전' : '오후';
            const displayHours = now.getHours() % 12 || 12;
            
            dateTimeStr = `${year}년 ${month}-${day} ${ampm} ${displayHours}시${minutes !== '00' ? minutes + '분' : ''}`;
        }
        
        infoText.innerHTML = `<span class="compare-info-date">${dateTimeStr} 기준</span> - <span class="compare-info-type">판매순 TOP20 / 주간 베스트 상품</span>`;
    }
    
    /**
     * 카드 렌더링
     */
    function renderCards() {
        if (!compareCardsContainer) return;
        
        const startIdx = (currentPage - 1) * ITEMS_PER_PAGE;
        const endIdx = startIdx + ITEMS_PER_PAGE;
        const itemsToShow = currentResults.slice(startIdx, endIdx);
        
        if (itemsToShow.length === 0) {
            compareCardsContainer.innerHTML = '<div class="compare-empty">표시할 상품이 없습니다.</div>';
            comparePagination.style.display = 'none';
            return;
        }
        
        // 카드 HTML 생성
        const cardsHTML = itemsToShow.map((item, index) => {
            const rank = startIdx + index + 1;
            const price = item.price ? `${Math.round(item.price).toLocaleString()}원` : '가격 정보 없음';
            
            // 베스트 뱃지: 카테고리 정보 포함
            let bestRankBadge = '';
            if (item.best_rank && item.best_category) {
                const categoryName = item.best_category || '전체';
                bestRankBadge = `<span class="compare-best-badge">${categoryName} ${item.best_rank}위</span>`;
            } else if (item.best_rank) {
                bestRankBadge = `<span class="compare-best-badge">전체 ${item.best_rank}위</span>`;
            }
            
            const itemUrl = item.item_url || `https://29cm.co.kr/products/${item.item_id}`;
            
            return `
                <div class="compare-card">
                    <div class="compare-card-rank">${rank}</div>
                    ${bestRankBadge}
                    <div class="compare-card-image">
                        <img src="${item.thumbnail_url || ''}" alt="${item.product_name || ''}" loading="lazy" />
                    </div>
                    <div class="compare-card-info">
                        <div class="compare-card-brand">${item.brand_name || ''}</div>
                        <div class="compare-card-name">${item.product_name || ''}</div>
                        <div class="compare-card-price">${price}</div>
                        ${item.like_count ? `<div class="compare-card-like">❤️ ${item.like_count.toLocaleString()}</div>` : ''}
                    </div>
                    <div class="compare-card-actions">
                        <a href="${itemUrl}" target="_blank" class="compare-card-link-btn">바로가기</a>
                        <button class="compare-card-review-btn" data-item-id="${item.item_id}" data-product-name="${(item.product_name || '').replace(/"/g, '&quot;')}">최신 리뷰 10</button>
                    </div>
                </div>
            `;
        }).join('');
        
        compareCardsContainer.innerHTML = `
            <div class="compare-cards-grid">
                ${cardsHTML}
            </div>
        `;
        
        // 리뷰 버튼 이벤트
        const reviewButtons = compareCardsContainer.querySelectorAll('.compare-card-review-btn');
        reviewButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                const itemId = this.dataset.itemId;
                const productName = this.dataset.productName;
                openReviewModal(itemId, productName);
            });
        });
        
        // 페이지네이션 업데이트
        updatePagination();
    }
    
    /**
     * 페이지네이션 업데이트
     */
    function updatePagination() {
        const maxPage = Math.ceil(currentResults.length / ITEMS_PER_PAGE);
        
        if (maxPage <= 1) {
            comparePagination.style.display = 'none';
            return;
        }
        
        comparePagination.style.display = 'flex';
        comparePageInfo.textContent = `${currentPage} / ${maxPage}`;
        
        comparePrevBtn.disabled = currentPage === 1;
        compareNextBtn.disabled = currentPage === maxPage;
    }
    
    /**
     * 리뷰 모달 열기
     */
    async function openReviewModal(itemId, productName) {
        reviewModalTitle.textContent = productName || '상품 리뷰';
        reviewModalBody.innerHTML = '<div class="compare-review-loading">리뷰를 불러오는 중...</div>';
        reviewModal.style.display = 'block';
        
        try {
            const response = await fetch(`/dashboard/compare/29cm/reviews?item_id=${itemId}`);
            const data = await response.json();
            
            if (data.status !== 'success') {
                throw new Error(data.message || '리뷰 조회 실패');
            }
            
            const reviews = data.reviews || [];
            
            if (reviews.length === 0) {
                reviewModalBody.innerHTML = '<div class="compare-review-empty">리뷰가 없습니다.</div>';
                return;
            }
            
            const reviewsHTML = reviews.map(review => {
                const rating = '⭐'.repeat(review.rating || 0);
                const option = review.option ? `<div class="compare-review-option">옵션: ${review.option}</div>` : '';
                const createdAt = review.created_at ? `<div class="compare-review-date">${review.created_at}</div>` : '';
                
                return `
                    <div class="compare-review-item">
                        <div class="compare-review-header">
                            <div class="compare-review-rating">${rating}</div>
                            ${createdAt}
                        </div>
                        ${option}
                        <div class="compare-review-content">${review.content || ''}</div>
                    </div>
                `;
            }).join('');
            
            reviewModalBody.innerHTML = `
                <div class="compare-review-list">
                    ${reviewsHTML}
                </div>
            `;
            
        } catch (error) {
            console.error('[Compare] 리뷰 로드 실패:', error);
            reviewModalBody.innerHTML = `<div class="compare-review-error">리뷰를 불러오는 중 오류가 발생했습니다: ${error.message}</div>`;
        }
    }
    
    /**
     * 리뷰 모달 닫기
     */
    function closeReviewModal() {
        reviewModal.style.display = 'none';
    }
    
    /**
     * 로딩 표시
     */
    function showLoading() {
        if (compareCardsContainer) {
            compareCardsContainer.innerHTML = '<div class="compare-loading">데이터를 불러오는 중...</div>';
        }
        if (comparePagination) {
            comparePagination.style.display = 'none';
        }
    }
    
    /**
     * 에러 표시
     */
    function showError(message) {
        if (compareCardsContainer) {
            compareCardsContainer.innerHTML = `<div class="compare-error">${message}</div>`;
        }
        if (comparePagination) {
            comparePagination.style.display = 'none';
        }
    }
    
    /**
     * 주차 번호 계산 (ISO 8601 기준)
     */
    function getWeekNumber(date) {
        const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        const dayNum = d.getUTCDay() || 7;
        d.setUTCDate(d.getUTCDate() + 4 - dayNum);
        const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
        return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
    }
    
    // 초기화
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

