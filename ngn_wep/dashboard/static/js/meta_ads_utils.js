// File: static/js/meta_ads_utils.js

import { metaAdsState } from "./meta_ads_state.js";
import { renderSelectedTags } from "./meta_ads_tags.js";

// ✅ 기간 문자열을 기준으로 시작일과 종료일을 계산
export function resolveDateRange(period) {
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, "0");
  const dd = String(today.getDate()).padStart(2, "0");

  let start = `${yyyy}-${mm}-${dd}`;
  let end = start;  // ✅ const → let 으로 수정

  if (period === "yesterday") {
    const y = new Date(today);
    y.setDate(y.getDate() - 1);
    start = y.toISOString().slice(0, 10);
    end = y.toISOString().slice(0, 10);
  } else if (period === "last7days") {
    const s = new Date(today);
    s.setDate(s.getDate() - 7);
    start = s.toISOString().slice(0, 10);
  } else if (period === "last_month") {
    const s = new Date(today);
    s.setMonth(s.getMonth() - 1);
    s.setDate(1);
    const e = new Date(s.getFullYear(), s.getMonth() + 1, 0);
    start = s.toISOString().slice(0, 10);
    end = e.toISOString().slice(0, 10);
  }

  return { start, end };
}



// ✅ 숫자 포맷 함수
function cleanData(value, decimalPlaces = 0) {
  if (value === undefined || value === null || value === "-" || value === "") {
    return (0).toLocaleString('en-US', {
      minimumFractionDigits: decimalPlaces,
      maximumFractionDigits: decimalPlaces
    });
  }
  if (!isNaN(value)) {
    return parseFloat(value).toLocaleString('en-US', {
      minimumFractionDigits: decimalPlaces,
      maximumFractionDigits: decimalPlaces
    });
  }
  return value;
}

// showLoading/hideLoading 함수는 common.js에서 정의됨

export function showInlinePopup(message) {
  const popup = $(`<div class="custom-popup">${message}</div>`);
  $("body").append(popup);
  setTimeout(() => popup.fadeOut(300, () => popup.remove()), 3000);
}

// ✅ 업데이트 시간 텍스트
export function updateUpdatedAtText(text) {
  const utc = new Date(text);

  // 시간만 보정 (날짜는 그대로 유지)
  const hours = utc.getUTCHours() + 9;
  const adjustedHour = hours % 24;
  const carryDate = hours >= 24 ? 1 : 0;

  const year = utc.getUTCFullYear();
  const month = utc.getUTCMonth() + 1;
  const date = utc.getUTCDate();  // 날짜는 그대로 유지
  const finalDate = date + carryDate;

  // 🔥 날짜 유효성 검사 및 수정
  let finalYear = year;
  let finalMonth = month;
  let finalDay = finalDate;
  
  // 월별 최대 일수 확인
  const daysInMonth = new Date(year, month, 0).getDate();
  if (finalDay > daysInMonth) {
    finalDay = finalDay - daysInMonth;
    finalMonth = finalMonth + 1;
    if (finalMonth > 12) {
      finalMonth = 1;
      finalYear = finalYear + 1;
    }
  }

  const minutes = utc.getUTCMinutes().toString().padStart(2, '0');

  const formatted = `${finalYear}년 ${finalMonth}월 ${finalDay}일 ${adjustedHour}시 ${minutes}분`;
  $("#updatedAtText").text(`최종 업데이트: ${formatted}`);
}


// ✅ 데이터 요청
export function fetchMetaAdsInsight(level) {
  console.log("[DEBUG] fetchMetaAdsInsight 호출됨!", level);
  showLoading("#loadingOverlayMetaAdsInsight");

  const requestData = {
    data_type: "meta_ads_insight_table",
    level,
    company_name: metaAdsState.company,
    period: metaAdsState.period,
    start_date: metaAdsState.startDate,
    end_date: metaAdsState.endDate,
    date_type: metaAdsState.dateType,
    account_id: metaAdsState.accountId,
  };

  // ✅ level별로 campaign_id, adset_id 조건부 추가
  if (level === "campaign" || level === "adset" || level === "ad") {
    if (metaAdsState.campaignIds.length > 0) {
      requestData.campaign_id = metaAdsState.campaignIds.join(",");
    }
  }

  if (level === "adset" || level === "ad") {
    if (metaAdsState.adsetIds.length > 0) {
      requestData.adset_id = metaAdsState.adsetIds.join(",");
    }
  }

  $.ajax({
    url: "/dashboard/get_data",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(requestData),
    success: function (res) {
      hideLoading("#loadingOverlayMetaAdsInsight");
      const rows = res?.meta_ads_insight_table || [];
      if (res.updated_at) updateUpdatedAtText(res.updated_at);

      if (res.status === "success") {
        renderMetaAdsInsightTable(level, rows);
      } else {
        $("#metaAdsInsightBody").html("<tr><td colspan='20'>데이터가 없습니다</td></tr>");
      }
    },
    error: function () {
      console.error("[ERROR] Meta Ads Insight 요청 실패 - level:", level);
      hideLoading("#loadingOverlayMetaAdsInsight");
      showInlinePopup("데이터 요청 실패");
    }
  });
}


// ✅ 테이블 렌더링
export function renderMetaAdsInsightTable(level, rows) {
  const $tbody = $("#metaAdsInsightBody").empty();
  if (!rows || rows.length === 0) {
    $tbody.html("<tr><td colspan='20'>데이터가 없습니다</td></tr>");
    return;
  }

  let total = { spend: 0, impressions: 0, clicks: 0, purchases: 0, purchase_value: 0 };

  rows.forEach(row => {
    const spend = row.spend || 0;
    const impressions = row.impressions || 0;
    const clicks = row.clicks || 0;
    const purchases = row.purchases || 0;
    const purchase_value = row.purchase_value || 0;
  
    const CPC = clicks > 0 ? spend / clicks : 0;
    const CTR = impressions > 0 ? (clicks / impressions) * 100 : 0;
    const CPM = impressions > 0 ? (spend / impressions) * 1000 : 0;
    const CVR = clicks > 0 ? (purchases / clicks) * 100 : 0;
    const ROAS = spend > 0 ? (purchase_value / spend) * 100 : 0;
    const AOV = purchases > 0 ? purchase_value / purchases : 0;
  
    total.spend += spend;
    total.impressions += impressions;
    total.clicks += clicks;
    total.purchases += purchases;
    total.purchase_value += purchase_value;
  
    const cells = [];
    cells.push(`<td>${row.report_date || row.date || "-"}</td>`);
  
    if (level === "account") {
      cells.push(`<td style="text-align:left;">${row.account_name}</td>`);
    }
  
    if (level === "campaign") {
      const isChecked = metaAdsState.campaignIds.includes(row.campaign_id) ? "checked" : "";
      cells.push(`<td style="text-align:left;">
        <label>
          <input type="checkbox" name="campaign_check" value="${row.campaign_id}" data-name="${row.campaign_name}" ${isChecked}>
          <span style="margin-left: 6px;">${row.campaign_name}</span>
        </label>
      </td>`);
    }
  
    if (level === "adset") {
      const isChecked = metaAdsState.adsetIds.includes(row.adset_id) ? "checked" : "";
      cells.push(`<td style="text-align:left;">
        <label>
          <input type="checkbox" name="adset_check" value="${row.adset_id}" data-name="${row.adset_name}" ${isChecked}>
          <span style="margin-left: 6px;">${row.adset_name}</span>
        </label>
      </td>`);
    }
  
    if (level === "ad") {
      cells.push(`<td style="text-align:left;">${row.ad_name || "-"}</td>`);
    }



  
    cells.push(
      `<td>${cleanData(spend)}</td>`,
      `<td>${cleanData(impressions)}</td>`,
      `<td>${cleanData(clicks)}</td>`,
      `<td>${cleanData(CPC)}</td>`,
      `<td>${cleanData(CTR ,2)}%</td>`,
      `<td>${cleanData(CPM)}</td>`,
      `<td>${cleanData(purchases)}</td>`,
      `<td>${cleanData(purchase_value)}</td>`,
      `<td>${cleanData(CVR ,2)}%</td>`,
      `<td>${cleanData(AOV)}</td>`,
      `<td>${cleanData(ROAS)}%</td>`
    );
  
    if (level === "ad") {
      cells.push(`<td>${row.ad_status}</td>`, `<td><a href="${row.ad_url}" target="_blank">바로가기</a></td>`);
    }
  
    $tbody.append(`<tr>${cells.join("")}</tr>`);
  });
  

  const CPC = total.clicks > 0 ? total.spend / total.clicks : 0;
  const CTR = total.impressions > 0 ? (total.clicks / total.impressions) * 100 : 0;
  const CPM = total.impressions > 0 ? (total.spend / total.impressions) * 1000 : 0;
  const CVR = total.clicks > 0 ? (total.purchases / total.clicks) * 100 : 0;
  const ROAS = total.spend > 0 ? (total.purchase_value / total.spend) * 100 : 0;
  const AOV = total.purchases > 0 ? total.purchase_value / total.purchases : 0;

  const sumCells = [];
  sumCells.push(`<td>총합</td>`);
  if (["account", "campaign", "adset", "ad"].includes(level)) {
    sumCells.push(`<td>-</td>`);
  }

  sumCells.push(
    `<td>${cleanData(total.spend)}</td>`,
    `<td>${cleanData(total.impressions)}</td>`,
    `<td>${cleanData(total.clicks)}</td>`,
    `<td>${cleanData(CPC)}</td>`,
    `<td>${cleanData(CTR, 2)}%</td>`, 
    `<td>${cleanData(CPM)}</td>`,
    `<td>${cleanData(total.purchases)}</td>`,
    `<td>${cleanData(total.purchase_value)}</td>`,
    `<td>${cleanData(CVR, 2)}%</td>`,
    `<td>${cleanData(AOV)}</td>`,
    `<td>${cleanData(ROAS)}%</td>`
  );

  if (level === "ad") {
    sumCells.push(`<td>-</td>`, `<td>-</td>`);
  }

  $tbody.append(`<tr id="metaAdsTotalRow" style="font-weight:bold; background:#e2efff;">${sumCells.join("")}</tr>`);
  bindCampaignAdsetCheckboxEvents(level);
}

// ✅ 체크박스 이벤트 + 태그 즉시 반영
export function bindCampaignAdsetCheckboxEvents(level) {
  if (level === "campaign") {
    $("input[name='campaign_check']").on("change", function () {
      const id = $(this).val();
      const name = $(this).data("name");

      if (this.checked) {
        if (!metaAdsState.campaignIds.includes(id)) {
          metaAdsState.campaignIds.push(id);
          metaAdsState.campaignNames.push(name);
        }
      } else {
        const index = metaAdsState.campaignIds.indexOf(id);
        if (index > -1) {
          metaAdsState.campaignIds.splice(index, 1);
          metaAdsState.campaignNames.splice(index, 1);
          metaAdsState.adsetIds = [];
          metaAdsState.adsetNames = [];
        }
      }

      renderSelectedTags();
      //fetchMetaAdsInsight("campaign");
    });
  }

  if (level === "adset") {
    $("input[name='adset_check']").on("change", function () {
      const id = $(this).val();
      const name = $(this).data("name");

      if (this.checked) {
        if (!metaAdsState.adsetIds.includes(id)) {
          metaAdsState.adsetIds.push(id);
          metaAdsState.adsetNames.push(name);
        }
      } else {
        const index = metaAdsState.adsetIds.indexOf(id);
        if (index > -1) {
          metaAdsState.adsetIds.splice(index, 1);
          metaAdsState.adsetNames.splice(index, 1);
        }
      }

      renderSelectedTags();
      //fetchMetaAdsInsight("adset");
    });
  }
}
