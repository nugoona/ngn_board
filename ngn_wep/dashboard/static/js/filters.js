import { metaAdsState } from "./meta_ads_state.js";
import { fetchMetaAdsInsight } from "./meta_ads_utils.js";
import { resolveDateRange } from "./meta_ads_utils.js";
import { fetchMetaAdsAdsetSummaryByType } from "./meta_ads_adset_summary_by_type.js";
import { fetchMetaAdsPreviewList } from "./meta_ads_preview.js";
import { fetchSlideCollectionAds } from "./meta_ads_slide_collection.js";



// ✅ 새로고침 시 세션스토리지 초기화
if (performance.navigation.type === 1) {
  sessionStorage.clear();
}

let isLoading = false;

window.onload = async function () {
  try {
    initializeFilters();           // ✅ 필터 상태(metaAdsState) 먼저 세팅
    await fetchMetaAccountList();  // ✅ 그 다음 계정 목록 요청 + fetch 함수 실행
  } catch (e) {
    console.error("[ERROR] 초기 계정 목록 로딩 실패:", e);
  }
};

let isRestoringFilter = false;  // 🔹 전역 플래그
let startDatePicker, endDatePicker;  // 🔹 Flatpickr 인스턴스

function safelyRestoreSelect($select, prevValue) {
  isRestoringFilter = true;
  $select.val("");
  setTimeout(() => {
    $select.val(prevValue).trigger("change");
    isRestoringFilter = false;
  }, 10);
}

// ✅ Flatpickr 초기화 함수
function initializeFlatpickr() {
  // Flatpickr가 로드되었는지 확인
  if (typeof flatpickr === 'undefined') {
    console.warn('Flatpickr not loaded, retrying in 100ms...');
    setTimeout(initializeFlatpickr, 100);
    return;
  }

  const commonConfig = {
    locale: 'ko',
    dateFormat: 'Y-m-d',
    allowInput: false,
    clickOpens: true,
    theme: 'material_blue',
    disableMobile: false,
    onChange: function(selectedDates, dateStr, instance) {
      // 날짜 변경 시 기존 로직 실행
      if (instance.element.id === 'startDate') {
        $("#startDate").trigger('change');
      } else if (instance.element.id === 'endDate') {
        $("#endDate").trigger('change');
      }
    }
  };

  // 기존 인스턴스가 있으면 제거
  if (startDatePicker) {
    startDatePicker.destroy();
  }
  if (endDatePicker) {
    endDatePicker.destroy();
  }

  // 시작일 Flatpickr
  startDatePicker = flatpickr("#startDate", {
    ...commonConfig,
    maxDate: new Date(),
    onOpen: function(selectedDates, dateStr, instance) {
      // 종료일이 선택되어 있으면 최대 날짜 제한
      const endDate = endDatePicker?.selectedDates[0];
      if (endDate) {
        instance.set('maxDate', endDate);
      }
    }
  });

  // 종료일 Flatpickr
  endDatePicker = flatpickr("#endDate", {
    ...commonConfig,
    maxDate: new Date(),
    onOpen: function(selectedDates, dateStr, instance) {
      // 시작일이 선택되어 있으면 최소 날짜 제한
      const startDate = startDatePicker?.selectedDates[0];
      if (startDate) {
        instance.set('minDate', startDate);
      }
    }
  });
}

function initializeFilters() {
  const savedCompany = sessionStorage.getItem("selectedCompany") || "all";
  const savedPeriod = sessionStorage.getItem("selectedPeriod") || "today";

  // ✅ Flatpickr 초기화
  initializeFlatpickr();

  const $accountFilter = $("#accountFilter").empty();
  const isDemoUser = currentUserId === "demo";

  if (isDemoUser) {
    $accountFilter.append(`<option value="demo" selected>demo</option>`);
    $("#accountDropdown .selected-text").text("demo");
  } else {
    const filteredList = userCompanyList.filter(name => name.toLowerCase() !== "demo");

    if (filteredList.length > 1) {
      $accountFilter.append(`<option value="all" ${savedCompany === "all" ? "selected" : ""}>모든 업체</option>`);
    }

    filteredList.forEach(company => {
      const value = company.toLowerCase();
      const selected = savedCompany === value ? "selected" : "";
      $accountFilter.append(`<option value="${value}" ${selected}>${company}</option>`);
    });

    const selectedText = $("#accountFilter option:selected").text() || "모든 업체";
    $("#accountDropdown .selected-text").text(selectedText);
  }

  // ✅ 업체 필터
  $("#accountFilter").off("change").on("change", function () {
    if (isRestoringFilter) return;

    if (isLoading) {
      const prevValue = sessionStorage.getItem("selectedCompany") || "all";
      showBlockingAlert(() => {
        safelyRestoreSelect($(this), prevValue);
      });
      return;
    }

    const selectedValue = $(this).val();
    const selectedText = $("#accountFilter option:selected").text() || "모든 업체";

    metaAdsState.company = selectedValue;
    sessionStorage.setItem("selectedCompany", selectedValue);
    $("#accountDropdown .selected-text").text(selectedText);

    metaAdsState.accountId = null;
    $("#metaAccountSelector").val("");

    fetchMetaAccountList();
    fetchFilteredData();
  });

  // ✅ 기간 필터
  $("#periodFilter").off("change").on("change", function () {
  if (isRestoringFilter) return;

  if (isLoading) {
    const prevValue = sessionStorage.getItem("selectedPeriod") || "today";
    showBlockingAlert(() => {
      safelyRestoreSelect($(this), prevValue);
    });
    return;
  }

  const selectedValue = $(this).val();
  const selectedText = $("#periodFilter option:selected").text() || "기간";

  metaAdsState.period = selectedValue;
  sessionStorage.setItem("selectedPeriod", selectedValue);
  $("#periodDropdown .selected-text").text(selectedText);

  if (selectedValue === "manual") {
    $("#dateRangeContainer").fadeIn().css("display", "flex");
    // Flatpickr 인스턴스 재활성화
    startDatePicker?.enable();
    endDatePicker?.enable();
  } else {
    $("#dateRangeContainer").fadeOut();
    startDatePicker?.clear();
    endDatePicker?.clear();
    $("#startDate").val("");
    $("#endDate").val("");

    // ✅ 카페24 테이블 대상일 경우, 항상 "기간합"으로 되돌리기
    if (window.location.pathname === "/" || window.location.pathname === "/dashboard") {
      $("input[name='dateType'][value='summary']").prop("checked", true).trigger("change");
    }
  }

  fetchFilteredData();
});


  // ✅ 시작일
  $("#startDate").off("change").on("change", function () {
    const startDate = $("#startDate").val()?.trim();
    const endDate = $("#endDate").val()?.trim();
    const selectedPeriod = $("#periodFilter").val();

    if (selectedPeriod === "manual" && (!startDate || !endDate)) {
      console.warn("[BLOCKED] 직접 선택: 종료일 누락 → 실행 안함");
      return;
    }

    if (window.location.pathname === "/ads") {
      metaAdsState.startDate = startDate;
      metaAdsState.endDate = endDate;
    }

    if (isLoading) {
      showBlockingAlert();
      return;
    }

    fetchFilteredData();
  });

  // ✅ 종료일
  $("#endDate").off("change").on("change", function () {
    const startDate = $("#startDate").val()?.trim();
    const endDate = $("#endDate").val()?.trim();
    const selectedPeriod = $("#periodFilter").val();

    if (selectedPeriod === "manual" && (!startDate || !endDate)) {
      console.warn("[BLOCKED] 직접 선택: 시작일 누락 → 실행 안함");
      return;
    }

    if (window.location.pathname === "/ads") {
      metaAdsState.startDate = startDate;
      metaAdsState.endDate = endDate;
    }

    if (isLoading) {
      showBlockingAlert();
      return;
    }

    fetchFilteredData();
  });

  // ✅ 초기화 버튼
  $("#applyDateFilter").off("click").on("click", function () {
    if (isLoading) {
      showBlockingAlert();
      return;
    }

    // Flatpickr 인스턴스 초기화
    startDatePicker?.clear();
    endDatePicker?.clear();
    
    $("#startDate").val("");
    $("#endDate").val("");
    $("#periodFilter").val("manual").trigger("change");
  });

  // ✅ 초기 상태 세팅
  metaAdsState.company = savedCompany;
  metaAdsState.period = savedPeriod;
  metaAdsState.tabLevel = metaAdsState.tabLevel || "account";

  fetchFilteredData();
}

// ✅ 로딩 차단 팝업 함수
function showBlockingAlert(afterPopup) {
  if (window.Swal) {
    Swal.fire({
      title: "로딩 중입니다",
      text: "잠시만 기다려주세요...",
      icon: "info",
      showConfirmButton: false,
      timer: 2000,
      didOpen: () => {
        // 팝업이 열릴 때 즉시 실행 가능
      },
      didClose: () => {
        if (typeof afterPopup === "function") {
          afterPopup();  // 팝업이 닫힌 직후 실행
        }
      },
      width: "320px",
      padding: "1.5em",
      background: "#fefefe",
      color: "#333",
      customClass: {
        popup: 'compact-loading-popup',
        title: 'compact-loading-title',
        htmlContainer: 'compact-loading-text'
      }
    });
  } else {
    alert("로딩 중입니다. 잠시만 기다려주세요.");
    if (typeof afterPopup === "function") {
      setTimeout(afterPopup, 10);  // fallback
    }
  }
}

async function fetchFilteredData() {
  if (isLoading) return;
  isLoading = true;

  const pathname = window.location.pathname;
  const selectedPeriod = $("#periodFilter").val();
  const selectedCompany = $("#accountFilter").val() || "all";
  const startDate = $("#startDate").val()?.trim();
  const endDate = $("#endDate").val()?.trim();

  // ✅ company_name 가공
  let companyName;
  if (selectedCompany === "all") {
    companyName = userCompanyList
      .filter(name => name.toLowerCase() !== "demo")
      .map(name => name.toLowerCase());
  } else {
    companyName = selectedCompany;
  }

  const isAllCompany = Array.isArray(companyName) && companyName.length > 1;
  const isDateMissing = selectedPeriod === "manual" && (!startDate || !endDate);

  if (isAllCompany && isDateMissing) {
    console.warn("[BLOCKED] '모든 업체 + 날짜 없음' 조합으로 get_data 요청 차단됨");
    isLoading = false;
    return;
  }

  const requestData = {
    company_name: companyName,
    period: selectedPeriod,
  };

  if (selectedPeriod === "manual") {
    requestData.start_date = startDate;
    requestData.end_date = endDate;
  }

  console.log("[DEBUG] filters.js → requestData for all widgets:", requestData);

  try {
    if (pathname === "/" || pathname === "/dashboard") {
      // updateAllData 함수가 정의되어 있는지 확인하고 호출
      if (typeof updateAllData === 'function') {
        console.log("🔄 filters.js에서 updateAllData() 호출");
        await updateAllData();
      } else {
        console.warn("[WARN] updateAllData 함수가 정의되지 않음 - 개별 함수 호출로 대체");
        // 순차적으로 실행하여 abort 방지
        const requests = [
          () => fetchCafe24SalesData?.(requestData),
          () => fetchCafe24ProductSalesData?.(requestData),
          () => fetchPerformanceSummaryData?.(requestData),
          () => fetchMonthlyNetSalesVisitors?.(requestData),
          () => fetchProductSalesRatio?.(requestData),
          () => fetchPlatformSalesSummary?.(requestData),
          () => fetchPlatformSalesRatio?.(requestData),
          () => fetchGa4SourceSummaryData?.(requestData),
          () => fetchGa4ViewItemSummaryData?.(requestData),
          () => fetchMonthlyPlatformSalesData?.(requestData)
        ].filter(Boolean);

        // 순차 실행
        for (const request of requests) {
          try {
            await request();
          } catch (error) {
            console.warn("[WARN] 요청 실패:", error);
          }
        }
      }
    } else if (pathname === "/ads") {
      metaAdsState.period = selectedPeriod;

      if (selectedPeriod !== "manual") {
        const resolved = resolveDateRange(selectedPeriod);  // ✅ 구조 분해 대신 객체로 접근
        metaAdsState.startDate = resolved.start;
        metaAdsState.endDate = resolved.end;
      } else {
        metaAdsState.startDate = startDate || "";
        metaAdsState.endDate = endDate || "";
      }

      const accountId = metaAdsState.accountId;
      await fetchMetaAdsInsight(metaAdsState.tabLevel || "account");

      if (accountId) {
        await fetchMetaAdsAdsetSummaryByType({
          account_id: accountId,
          period: metaAdsState.period,
          start_date: metaAdsState.startDate,
          end_date: metaAdsState.endDate
        });

        await fetchMetaAdsPreviewList();
        await fetchSlideCollectionAds(accountId);
      }
    }
  } catch (e) {
    console.error("[ERROR] fetchFilteredData 순차 요청 중 오류 발생:", e);
  } finally {
    isLoading = false;
  }
}


// ✅ 메타 계정 목록 요청 함수 (Promise 반환)
function fetchMetaAccountList() {
  return new Promise((resolve, reject) => {
    const requestData = {
      data_type: "meta_account_list",
      company_name: metaAdsState.company || "all",
      period: metaAdsState.period || "today"
    };

    $.ajax({
      url: "/dashboard/get_data",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify(requestData),
      success: function (res) {
        const accounts = res.meta_accounts || [];
        const $selector = $("#metaAccountSelector").empty();

        if (accounts.length === 1) {
          const acc = accounts[0];
          metaAdsState.accountId = acc.account_id;
          $selector.append(`<option value="${acc.account_id}" selected>${acc.account_name}</option>`);
          $("#accountSelectorDropdown .selected-text").text(acc.account_name);

          // ✅ 계정이 1개일 경우에도 데이터 호출 강제 실행
          fetchFilteredData();

          fetchMetaAdsAdsetSummaryByType({
            account_id: acc.account_id,
            period: metaAdsState.period,
            start_date: metaAdsState.startDate,
            end_date: metaAdsState.endDate
          });

          fetchMetaAdsPreviewList();
          fetchSlideCollectionAds(acc.account_id);
        } else if (accounts.length > 1) {
          $selector.append(`<option value="">모든 계정</option>`);
          accounts.forEach(acc => {
            $selector.append(`<option value="${acc.account_id}">${acc.account_name}</option>`);
          });
          metaAdsState.accountId = "";
          $("#accountSelectorDropdown .selected-text").text("모든 계정");
        } else {
          metaAdsState.accountId = "";
          $selector.append(`<option value="">계정 없음</option>`);
          $("#accountSelectorDropdown .selected-text").text("계정 없음");
        }

        // ✅ 계정 변경 이벤트 등록
        $("#metaAccountSelector").off("change").on("change", function () {
          const accountId = $(this).val();
          const accountName = $("#metaAccountSelector option:selected").text();

          metaAdsState.accountId = accountId;
          $("#accountSelectorDropdown .selected-text").text(accountName);

          fetchFilteredData();

          // ✅ account_id만 필요한 데이터 호출
          if (accountId) {
            fetchMetaAdsAdsetSummaryByType({
              account_id: accountId,
              period: metaAdsState.period,
              start_date: metaAdsState.startDate,
              end_date: metaAdsState.endDate
            });

            fetchMetaAdsPreviewList();
            fetchSlideCollectionAds(accountId);
          }
        });

        console.log("[DEBUG] Meta Ads 계정 목록 로딩 완료:", accounts.length);
        resolve();
      },
      error: function (err) {
        console.error("[ERROR] Meta Ads 계정 목록 요청 실패", err);
        reject(err);
      }
    });
  });
}

export { fetchMetaAccountList };
