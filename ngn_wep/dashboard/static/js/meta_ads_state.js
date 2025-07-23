// File: static/js/meta_ads_state.js

export const metaAdsState = {
  company: "all",            // 업체명
  period: "today",           // 오늘, 어제, 지난 7일, manual 등
  startDate: "",             // 시작일 (manual일 경우)
  endDate: "",               // 종료일 (manual일 경우)

  accountId: null,           // 선택된 Meta 광고 계정 ID
  catalogId: null,           // ✅ 추가: 선택된 계정의 catalog_id
  catalogMap: {},            // ✅ 추가: { accountId: { catalog_id: "..." } } 형태로 저장됨

  tabLevel: "account",       // account, campaign, adset, ad 중 하나

  campaignIds: [],           // 선택된 캠페인 ID 목록
  campaignNames: [],

  adsetIds: [],              // 선택된 광고세트 ID 목록
  adsetNames: [],

  dateType: "summary",       // 기간합(summary) / 일자별(daily)
  dateSort: "desc"           // 날짜 내림차순/오름차순
};

window.metaAdsState = metaAdsState;
