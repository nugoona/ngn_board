import { metaAdsState } from "./meta_ads_state.js";
import { renderSelectedTags } from "./meta_ads_tags.js";
// showLoading/hideLoading 함수는 common.js에서 정의됨
import {
  fetchMetaAdsInsight,
  renderMetaAdsInsightTable,
  bindCampaignAdsetCheckboxEvents,
} from "./meta_ads_utils.js";
import { showInlinePopup } from "./common_ui.js";
import { fetchMetaAdsPreviewList } from "./meta_ads_preview.js";
import { fetchMetaAdsAdsetSummaryByType } from "./meta_ads_adset_summary_by_type.js";

$(document).ready(function () {
  if (window.location.pathname !== "/ads") return;

  const savedLevel = metaAdsState.tabLevel || "account";
  $(".tab-btn[data-level='" + savedLevel + "']").addClass("active");

  fetchMetaAccountList();

  // ✅ 탭 클릭 이벤트
  $(".meta-ads-tabs .tab-btn").on("click", function () {
    const level = $(this).data("level");
    if ($(this).hasClass("active")) return;

    if (["campaign", "adset", "ad"].includes(level) && !metaAdsState.accountId) {
      showInlinePopup("계정을 먼저 선택해 주세요.");
      return;
    }

    $(".tab-btn").removeClass("active");
    $(this).addClass("active");
    metaAdsState.tabLevel = level;

    renderSelectedTags();
    showMetaAdsTableHeader(level);
    fetchMetaAdsInsight(level);
  });

  // ✅ 캠페인 목표별 성과 보기 버튼 클릭
  $("#toggleTypeSummary").on("click", function () {
    if (!metaAdsState.accountId) {
      $("#typeSummaryContainer").hide();
      $(this).text("캠페인 목표별 성과 보기");
      showInlinePopup("계정을 먼저 선택해 주세요.");
      return;
    }

    const $container = $("#typeSummaryContainer");
    const isVisible = $container.is(":visible");

    $container.toggle();
    $(this).text(isVisible ? "캠페인 목표별 성과 보기" : "캠페인 목표별 성과 숨기기");

    if (!isVisible) {
      fetchMetaAdsAdsetSummaryByType({
        account_id: metaAdsState.accountId,
        period: metaAdsState.period,
        start_date: metaAdsState.startDate,
        end_date: metaAdsState.endDate
      });
    }
  });

  // ✅ 날짜 타입 변경
  $("input[name='metaDateType']").on("change", () => {
    metaAdsState.dateType = $("input[name='metaDateType']:checked").val();
    fetchMetaAdsInsight(metaAdsState.tabLevel);
  });
});


/* ------------------------------------------------------------------
 * Meta Ads – 광고 계정 셀렉터 + 상태 동기화
 * ----------------------------------------------------------------*/
export function fetchMetaAccountList() {
  $.ajax({
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify({
      data_type: "meta_account_list",
      company_name: metaAdsState.company || "all",
    }),
    success(res) {
      /* ---------- 1) 셀렉터 초기화 ---------- */
      const list = res?.meta_accounts ?? [];
      const $selector = $("#metaAccountSelector")
        .empty()
        .append('<option value="">모든 계정</option>');

      /* ---------- 2) catalogMap · companyMap 구성 & 옵션 렌더 ---------- */
      metaAdsState.catalogMap  = {};   // { accId -> catalogId }
      metaAdsState.companyMap  = {};   // { accId -> company_name }

      list.forEach((it) => {
        const id   = it.meta_acc_id   || it.account_id   || "unknown_id";
        const name = it.meta_acc_name || it.account_name || id;
        const comp = it.company_name  || "-";

        // catalog_id null·"null" 정리
        const rawCatalog = it.catalog_id;
        const cat = rawCatalog != null && String(rawCatalog).toLowerCase() !== "null"
          ? String(rawCatalog)
          : null;

        metaAdsState.catalogMap[id] = cat;
        metaAdsState.companyMap[id] = comp;

        $selector.append(/*html*/`
          <option value="${id}"
                  data-catalog="${cat ?? ''}"
                  data-company="${comp}">${name}</option>
        `);
      });

      /* ---------- 3) 상태 기본값 ---------- */
      metaAdsState.accountId ??= null;
      $selector.val("");

      /* ---------- 4) 계정 change 이벤트 ---------- */
      $selector
        .off("change.metaInsight")
        .on("change.metaInsight", function () {
          const selId = $(this).val() || null;
          metaAdsState.accountId = selId;

          // catalogId & company 동기화 (없으면 null / "all")
          metaAdsState.catalogId = metaAdsState.catalogMap[selId] || null;
          metaAdsState.company   = selId ? (metaAdsState.companyMap[selId] || "-")
                                         : "all";

          updateAfterAccountChange();
        });

      /* ---------- 5) 계정 1개면 자동 선택 ---------- */
      if (list.length === 1) {
        const onlyId = list[0].meta_acc_id || list[0].account_id;
        $selector.val(onlyId).trigger("change");
      }

      /* ---------- 6) 최초 테이블 표시 ---------- */
      showMetaAdsTableHeader(metaAdsState.tabLevel);
      fetchMetaAdsInsight(metaAdsState.tabLevel);
    },
    error() {
      console.error("[ERROR] Meta 광고 계정 목록 불러오기 실패");
    },
  });

  /* ----------------------------------------------------------------
   * 내부 헬퍼 : 계정 변경 이후 후처리
   * ----------------------------------------------------------------*/
  function updateAfterAccountChange() {
    if (metaAdsState.accountId) {
      try { fetchMetaAdsPreviewList(); } catch {}
      try {
        if (typeof fetchSlideCollectionAds === "function") {
          fetchSlideCollectionAds(metaAdsState.accountId);
        }
      } catch (e) {
        console.error(e);
      }
    } else {
      $("#previewCardContainer").html(
        '<p style="text-align:center; color:#999;">계정을 선택하면 광고 미리보기를 볼 수 있습니다.</p>'
      );
      $("#slideCollectionTableBody").html(
        '<tr><td colspan="2">계정을 선택하면 슬라이드 광고를 확인할 수 있습니다.</td></tr>'
      );
    }

    // 태그·필터 상태 초기화
    metaAdsState.campaignIds   = [];
    metaAdsState.campaignNames = [];
    metaAdsState.adsetIds      = [];
    metaAdsState.adsetNames    = [];

    renderSelectedTags();
    showMetaAdsTableHeader(metaAdsState.tabLevel);
    fetchMetaAdsInsight(metaAdsState.tabLevel);
  }
}

window.fetchMetaAccountList = fetchMetaAccountList;


function showMetaAdsTableHeader(level) {
  const $thead = $("#metaAdsInsightTableHeader").empty();
  const headers = ["날짜"];

  if (level === "account") headers.push("계정명");
  if (level === "campaign") headers.push("캠페인명");
  if (level === "adset") headers.push("광고세트명");
  if (level === "ad") headers.push("광고명");

  headers.push(
    "지출", "노출", "클릭", "클릭당비용", "클릭률", "노출당비용",
    "구매", "구매 금액", "전환율", "객단가", "ROAS"
  );

  if (level === "ad") {
    headers.push("STATUS", "URL");
  }

  headers.forEach((h, index) => {
    const th = $("<th>").text(h).attr("data-index", index).addClass("sortable");
    $thead.append(th);
  });

  $thead.off("click").on("click", "th.sortable", function () {
    const colIndex = $(this).data("index");
    const ascending = !$(this).hasClass("asc");

    $("#metaAdsInsightTableHeader th").removeClass("asc desc");
    $(this).addClass(ascending ? "asc" : "desc");

    const $body = $("#metaAdsInsightBody");
    const $rows = $body.find("tr").not("#metaAdsTotalRow").get();
    const $totalRow = $body.find("#metaAdsTotalRow");

    $rows.sort(function (a, b) {
      const A = $(a).children("td").eq(colIndex).text().replace(/,/g, "");
      const B = $(b).children("td").eq(colIndex).text().replace(/,/g, "");
      const valA = isNaN(A) ? A : parseFloat(A);
      const valB = isNaN(B) ? B : parseFloat(B);

      if (valA < valB) return ascending ? -1 : 1;
      if (valA > valB) return ascending ? 1 : -1;
      return 0;
    });

    $body.empty().append($rows).append($totalRow);
  });
}
