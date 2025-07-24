// File: static/js/meta_ads_slide_collection.js

// showLoading/hideLoading 함수는 common.js에서 정의됨

const $ = window.$;

let slideCollectionRequest = null;

export function fetchSlideCollectionAds(accountId = null) {
  // 순차 실행이므로 abort 제거
  // if (slideCollectionRequest) {
  //   slideCollectionRequest.abort();
  // }

  console.log("[DEBUG] fetchSlideCollectionAds 호출됨 - accountId:", accountId);

  showLoading("#slideCollectionLoading");

  if (!accountId || accountId === "null" || accountId === "") {
    hideLoading("#slideCollectionLoading");
    $("#slideCollectionTableBody").html('<tr><td colspan="2">계정이 선택되지 않았습니다.</td></tr>');
    return;
  }

  slideCollectionRequest = $.ajax({
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify({
      data_type: "slide_collection_ads",
      account_id: accountId,
    }),
    success: function (res) {
      hideLoading("#slideCollectionLoading");
      console.log("[DEBUG] 슬라이드/콜렉션 서버 응답:", res);

      if (res.slide_collection_ads && res.slide_collection_ads.length > 0) {
        renderSlideCollectionTable(res.slide_collection_ads);
      } else {
        $("#slideCollectionTableBody").html('<tr><td colspan="2">데이터가 없습니다.</td></tr>');
      }
    },
    error: function (err, textStatus) {
      hideLoading("#slideCollectionLoading");
    
      if (textStatus === "abort") {
        // ✅ 요청이 중단(abort)된 경우 무시 (다음 요청이 올 것이므로)
        console.warn("[SKIP] 중복 요청으로 이전 요청 중단됨 → 무시");
        return;
      }
    
      if (err.status === 200 || err.readyState === 4) {
        console.warn("[WARNING] 슬라이드 광고 로드는 응답은 왔지만 처리 중 문제가 있음", err);
      } else {
        console.error("[ERROR] 슬라이드/콜렉션 광고 로드 실패", err);
      }
    
      $("#slideCollectionTableBody").html("<tr><td colspan='2'>데이터를 불러오는 중 오류가 발생했습니다.</td></tr>");
    }       
  });
}

window.fetchSlideCollectionAds = fetchSlideCollectionAds;

function renderSlideCollectionTable(data) {
  const $tbody = $("#slideCollectionTableBody");
  $tbody.empty();

  data.forEach(row => {
    const tr = `
      <tr>
        <td style="text-align: center;">
          <a href="https://adsmanager.facebook.com/adsmanager/manage/ads/edit/standalone?act=${row.account_id}&selected_ad_ids=${row.ad_id}&business_id=${row.meta_business_id}&nav_source=no_referrer#"
             target="_blank"
             style="text-decoration: none;">
            <i class="fas fa-circle-play" style="
              font-size: 24px;
              color: #2A7EC6;
              filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.4));
            "></i>
          </a>
        </td>
        <td style="text-align: left;">${row.ad_name || "-"}</td>
      </tr>
    `;
    $tbody.append(tr);
  });
}

// ✅ 드롭다운과 연동 (네임스페이스 적용하여 충돌 방지)
$(document).ready(function () {
  console.log("[DEBUG] document.ready - metaAccountSelector 존재 여부:", $("#metaAccountSelector").length);

  setTimeout(() => {
    console.log("[DEBUG] setTimeout 안 - metaAccountSelector 길이:", $("#metaAccountSelector").length);

    $("#metaAccountSelector")
      .off("change.metaSlideCollection")
      .on("change.metaSlideCollection", function () {
        const selectedAccountId = $(this).val();
        console.log("[DEBUG] 드롭다운 선택된 accountId:", selectedAccountId);

        if (selectedAccountId && selectedAccountId !== "null" && selectedAccountId !== "") {
          console.log("[DEBUG] 드롭다운 선택된 계정 fetch 시작:", selectedAccountId);
          fetchSlideCollectionAds(selectedAccountId);
        } else {
          console.log("[DEBUG] 드롭다운 선택 없음 - 슬라이드 초기화");
          hideLoading("#slideCollectionLoading");
          $("#slideCollectionTableBody").html('<tr><td colspan="2">계정이 선택되지 않았습니다.</td></tr>');
        }
      });

    console.log("[DEBUG] 초기 로딩시 change() 트리거!");
    $("#metaAccountSelector").trigger("change");
  }, 100);
});
