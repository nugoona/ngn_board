// File: static/js/meta_ads_tags.js
import { metaAdsState } from "./meta_ads_state.js";
import { fetchMetaAdsInsight } from "./meta_ads_utils.js";

// ✅ 태그 렌더링
export function renderSelectedTags() {
  const update = (level, names) => {
    const $btn = $(`.tab-btn[data-level='${level}']`);
    if (names.length > 0) {
      $btn.html(`
        ${level === "campaign" ? "캠페인" : "광고세트"}
        <span class="filter-tag">(${names.length}개 선택됨)
          <span class="remove-tag" data-level="${level}">×</span>
        </span>`);
    } else {
      $btn.text(level === "campaign" ? "캠페인" : "광고세트");
    }
  };

  update("campaign", metaAdsState.campaignNames);
  update("adset", metaAdsState.adsetNames);

  $(".remove-tag").off("click").on("click", function () {
    const level = $(this).data("level");

    // ✅ 상태 초기화
    if (level === "campaign") {
      metaAdsState.campaignIds = [];
      metaAdsState.campaignNames = [];
      metaAdsState.adsetIds = [];
      metaAdsState.adsetNames = [];
    }

    if (level === "adset") {
      metaAdsState.adsetIds = [];
      metaAdsState.adsetNames = [];
    }

    renderSelectedTags();

    // ✅ 자동 탭 전환 + 데이터 재요청 (초기화)
    if (level === "campaign") {
      $(`.tab-btn[data-level='campaign']`).click();
      fetchMetaAdsInsight("campaign"); // 캠페인 전체 다시 불러오기
    } 
    else if (level === "adset") {
      $(`.tab-btn[data-level='adset']`).click();
      fetchMetaAdsInsight("adset"); // 광고세트 전체 다시 불러오기
    }
  });
}

// ✅ 세션 저장 (선택 유지용)
export function persistSelections() {
  sessionStorage.setItem("selectedCampaignIds", JSON.stringify(metaAdsState.campaignIds));
  sessionStorage.setItem("selectedCampaignNames", JSON.stringify(metaAdsState.campaignNames));
  sessionStorage.setItem("selectedAdsetIds", JSON.stringify(metaAdsState.adsetIds));
  sessionStorage.setItem("selectedAdsetNames", JSON.stringify(metaAdsState.adsetNames));
}

// ✅ 전체 초기화
export function clearSelections() {
  metaAdsState.campaignIds = [];
  metaAdsState.campaignNames = [];
  metaAdsState.adsetIds = [];
  metaAdsState.adsetNames = [];
  renderSelectedTags();
}

