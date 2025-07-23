// File: static/js/loading_utils.js

export function showLoading(target) {
  $(target).css({ display: "flex" });
  $(target).closest(".table-wrapper, .performance-summary-wrapper").addClass("loading");
}

export function hideLoading(target) {
  $(target).css({ display: "none" });
  $(target).closest(".table-wrapper, .performance-summary-wrapper").removeClass("loading");
}
