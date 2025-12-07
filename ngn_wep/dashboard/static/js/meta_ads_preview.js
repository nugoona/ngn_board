// File: static/js/meta_ads_preview.js

import { metaAdsState } from "./meta_ads_state.js";
// showLoading/hideLoading 함수는 common.js에서 정의됨
import { latestAjaxRequest } from "./request_utils.js";

// ✅ 미리보기 카드 렌더링
function renderMetaAdsPreviewCards(adList) {
  const $container = $("#previewCardContainer");
  $container.empty();

  if (!adList.length) {
    $container.append(`<p style="text-align:center; color:#777;">미리볼 광고가 없습니다.</p>`);
    return;
  }

  adList.forEach(ad => {
    const template = document.getElementById("previewCardTemplate");
    const clone = document.importNode(template.content, true);

    // ✅ 동적 데이터 삽입
    $(clone).find(".insta-account-name").text(ad.instagram_acc_name || "No Name");
    $(clone).find(".cta-link").attr("href", ad.link || "#");

    // 비디오 URL이 있으면 비디오 태그 사용, 없으면 이미지 태그 사용
    const $imageElement = $(clone).find(".ad-image");
    const $videoElement = $(clone).find(".ad-video");
    
    if (ad.video_url) {
      // 비디오 광고
      $imageElement.hide();
      $videoElement.find("source").attr("src", ad.video_url);
      if (ad.image_url) {
        $videoElement.attr("poster", ad.image_url); // 썸네일로 이미지 사용
      }
      $videoElement.show();
      $videoElement.on("loadeddata", function() {
        $(this).show();
      });
      $videoElement.on("error", function() {
        // 비디오 로딩 실패 시 이미지로 폴백
        $(this).hide();
        if (ad.image_url) {
          $imageElement.attr("src", ad.image_url).show();
        }
      });
      $videoElement[0].load(); // 비디오 로딩 시작
      $(clone).find(".play-overlay").css("display", "flex");
    } else {
      // 이미지 광고
      $videoElement.hide();
      $imageElement.attr("src", ad.image_url || "").show();
      if (ad.is_video) {
        $(clone).find(".play-overlay").css("display", "flex");
      } else {
        $(clone).find(".play-overlay").css("display", "none");
      }
    }

    // ✅ 문구 더보기/접기 기능 구현
    const $caption = $(clone).find(".ad-caption");
    const fullMessage = ad.message || "(문구 없음)";
    const firstLine = fullMessage.split("\n")[0];

    const accountNameHTML = `<span style='font-weight:bold;'>${ad.instagram_acc_name || "No Name"}</span>`;
    const shortCaption = `${accountNameHTML} ${firstLine} <span class='more-toggle' style='color: #737373; font-size: 13px; cursor: pointer; white-space: nowrap;'>... more</span>`;
    const fullCaption = `${accountNameHTML} ${fullMessage} <span class='less-toggle' style='color: #737373; font-size: 13px; cursor: pointer; white-space: nowrap;'>... less</span>`;

    $caption.html(shortCaption);

    $caption.off("click").on("click", function (e) {
      if (e.target.classList.contains("more-toggle")) {
        $caption.html(fullCaption);
      } else if (e.target.classList.contains("less-toggle")) {
        $caption.html(shortCaption);
      }
    });

    $container.append(clone);
  });
}

// ✅ 광고 미리보기 데이터 요청
export function fetchMetaAdsPreviewList() {
  const accountId = metaAdsState.accountId;
  if (!accountId) {
    console.warn("[PREVIEW] 계정이 선택되지 않았습니다.");
    $("#previewCardContainer").empty();
    return;
  }

  showLoading("#loadingOverlayAdsPreview");

  latestAjaxRequest("meta_ads_preview_list", {
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify({
      data_type: "meta_ads_preview_list",
      account_id: accountId
    }),
    success: function (res) {
      if (res.status === "success") {
        renderMetaAdsPreviewCards(res.meta_ads_preview_list || []);
      } else {
        console.error("[PREVIEW] 데이터 불러오기 실패");
      }
      hideLoading("#loadingOverlayAdsPreview");
    },
    error: function () {
      console.error("[PREVIEW] AJAX 오류");
      hideLoading("#loadingOverlayAdsPreview");
    }
  }, () => {});
}
