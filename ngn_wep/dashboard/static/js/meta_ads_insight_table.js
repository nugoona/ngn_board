console.log("[DEBUG] 🔥 meta_ads_insight_table.js 로드됨");

import { metaAdsState } from "./meta_ads_state.js";
import { renderSelectedTags } from "./meta_ads_tags.js";
// showLoading/hideLoading 함수는 common.js에서 정의됨
import {
  fetchMetaAdsInsight,
  renderMetaAdsInsightTable,
  bindCampaignAdsetCheckboxEvents,
} from "./meta_ads_utils.js";
// showInlinePopup 함수를 전역에서 가져오거나 직접 정의
const showInlinePopup = window.showInlinePopup || function(message = "알 수 없는 오류입니다") {
  // 기존 팝업이 있으면 제거
  const existing = document.querySelector(".custom-popup");
  if (existing) existing.remove();

  // 팝업 생성
  const popup = document.createElement("div");
  popup.className = "custom-popup";
  popup.innerText = message;

  // body에 추가
  document.body.appendChild(popup);

  // 클릭 시 즉시 제거
  popup.addEventListener("click", () => popup.remove());

  // 3초 후 페이드아웃 및 제거
  setTimeout(() => {
    popup.style.opacity = "0";
    setTimeout(() => popup.remove(), 500);
  }, 3000);
};
import { fetchMetaAdsPreviewList } from "./meta_ads_preview.js";
import { fetchMetaAdsAdsetSummaryByType } from "./meta_ads_adset_summary_by_type.js";

$(document).ready(function () {
  console.log("[DEBUG] 🔥 meta_ads_insight_table.js document.ready 시작");
  if (window.location.pathname !== "/ads") {
    console.log("[DEBUG] 현재 페이지가 /ads가 아님, 종료");
    return;
  }
  console.log("[DEBUG] 현재 페이지가 /ads임, 계속 진행");

  const savedLevel = metaAdsState.tabLevel || "account";
  $(".tab-btn[data-level='" + savedLevel + "']").addClass("active");

  // 초기 버튼 상태 설정 (계정이 선택되지 않은 상태)
  $("#toggleTypeSummary").addClass("disabled").prop("disabled", true);
  $("#openCatalogSidebarBtn").addClass("disabled").prop("disabled", true);

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
    console.log("[DEBUG] 🔥 toggleTypeSummary 버튼 클릭됨");
    console.log("[DEBUG] metaAdsState.accountId:", metaAdsState.accountId);
    console.log("[DEBUG] 버튼 disabled 상태:", $(this).prop("disabled"));
    console.log("[DEBUG] 버튼 disabled 클래스:", $(this).hasClass("disabled"));
    
    // 계정 선택 체크
    if (!metaAdsState.accountId) {
      console.log("[DEBUG] 계정이 선택되지 않음 - 팝업 표시");
      $("#typeSummaryContainer").hide();
      $(this).text("캠페인 목표별 성과 보기");
      showInlinePopup("좌측에서 Meta 광고 계정을 먼저 선택해 주세요.");
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
  console.log("[DEBUG] 🔥 fetchMetaAccountList 함수 호출됨");
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
      console.log("[DEBUG] 계정 선택 이벤트 바인딩 시작");
      $selector
        .off("change.metaInsight")
        .on("change.metaInsight", function () {
          console.log("[DEBUG] 🔥 계정 change 이벤트 발생!");
          const selId = $(this).val() || null;
          const selName = $(this).find("option:selected").text();
          console.log("[DEBUG] 선택된 계정 ID:", selId);
          console.log("[DEBUG] 선택된 계정 이름:", selName);
          console.log("[DEBUG] 이벤트 타입:", event.type);
          console.log("[DEBUG] 이벤트 타겟:", event.target);
          
          metaAdsState.accountId = selId;

          // catalogId & company 동기화 (없으면 null / "all")
          metaAdsState.catalogId = metaAdsState.catalogMap[selId] || null;
          metaAdsState.company   = selId ? (metaAdsState.companyMap[selId] || "-")
                                         : "all";

          console.log("[DEBUG] metaAdsState 업데이트:", {
            accountId: metaAdsState.accountId,
            catalogId: metaAdsState.catalogId,
            company: metaAdsState.company
          });

          console.log("[DEBUG] updateAfterAccountChange 호출 직전");
          updateAfterAccountChange();
          console.log("[DEBUG] updateAfterAccountChange 호출 완료");
        });
      console.log("[DEBUG] 계정 선택 이벤트 바인딩 완료");

      /* ---------- 5) 계정 1개면 자동 선택 ---------- */
      if (list.length === 1) {
        const onlyId = list[0].meta_acc_id || list[0].account_id;
        console.log("[DEBUG] 계정 1개 자동 선택:", onlyId);
        $selector.val(onlyId).trigger("change");
      } else if (list.length > 1) {
        // 계정이 여러 개인 경우에도 첫 번째 계정을 자동 선택 (임시 해결책)
        const firstId = list[0].meta_acc_id || list[0].account_id;
        console.log("[DEBUG] 계정 여러 개 - 첫 번째 계정 자동 선택:", firstId);
        $selector.val(firstId).trigger("change");
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
    console.log("[DEBUG] updateAfterAccountChange 호출됨, accountId:", metaAdsState.accountId);
    
    if (metaAdsState.accountId) {
      console.log("[DEBUG] 계정이 선택됨 - 버튼 활성화");
      try { fetchMetaAdsPreviewList(); } catch {}
      try {
        if (typeof fetchSlideCollectionAds === "function") {
          fetchSlideCollectionAds(metaAdsState.accountId);
        }
      } catch (e) {
        console.error(e);
      }
      
      // 계정이 선택되었을 때 버튼 활성화
      console.log("[DEBUG] 🔥 버튼 활성화 시작");
      console.log("[DEBUG] toggleTypeSummary 버튼 찾기:", $("#toggleTypeSummary").length);
      console.log("[DEBUG] openCatalogSidebarBtn 버튼 찾기:", $("#openCatalogSidebarBtn").length);
      
      const $toggleBtn = $("#toggleTypeSummary");
      const $catalogBtn = $("#openCatalogSidebarBtn");
      
      console.log("[DEBUG] 버튼 활성화 전 상태:");
      console.log("[DEBUG] toggleTypeSummary disabled:", $toggleBtn.prop("disabled"));
      console.log("[DEBUG] toggleTypeSummary has disabled class:", $toggleBtn.hasClass("disabled"));
      console.log("[DEBUG] openCatalogSidebarBtn disabled:", $catalogBtn.prop("disabled"));
      console.log("[DEBUG] openCatalogSidebarBtn has disabled class:", $catalogBtn.hasClass("disabled"));
      
      $toggleBtn.removeClass("disabled").prop("disabled", false);
      $catalogBtn.removeClass("disabled").prop("disabled", false);
      
      console.log("[DEBUG] 버튼 활성화 후 상태:");
      console.log("[DEBUG] toggleTypeSummary disabled:", $toggleBtn.prop("disabled"));
      console.log("[DEBUG] toggleTypeSummary has disabled class:", $toggleBtn.hasClass("disabled"));
      console.log("[DEBUG] openCatalogSidebarBtn disabled:", $catalogBtn.prop("disabled"));
      console.log("[DEBUG] openCatalogSidebarBtn has disabled class:", $catalogBtn.hasClass("disabled"));
      console.log("[DEBUG] ✅ 버튼 활성화 완료");
    } else {
      $("#previewCardContainer").html(
        '<p style="text-align:center; color:#999;">계정을 선택하면 광고 미리보기를 볼 수 있습니다.</p>'
      );
      $("#slideCollectionTableBody").html(
        '<tr><td colspan="2">계정을 선택하면 슬라이드 광고를 확인할 수 있습니다.</td></tr>'
      );
      
      // 계정이 선택되지 않았을 때 버튼 비활성화
      $("#toggleTypeSummary").addClass("disabled").prop("disabled", true);
      $("#openCatalogSidebarBtn").addClass("disabled").prop("disabled", true);
      
      // 캠페인 목표별 성과 컨테이너 숨기기
      $("#typeSummaryContainer").hide();
      $("#toggleTypeSummary").text("캠페인 목표별 성과 보기");
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
