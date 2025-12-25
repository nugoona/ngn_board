# tools/ai_report_test/judgement_guardrails.py
# 목적:
# - 리포트 생성 단계에서 "판단 가능한지"만 결정한다.
# - 문장 생성/수치 계산은 여기서 하지 않는다.
#
# 설계 원칙:
# - False면: 해석/판단 문장 금지, 사실 요약 + 전제형 질문만 허용
# - True면: "평균 대비/비교 기반"의 보수적 해석 문장만 허용 (잘했다/못했다 금지)

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


# ---- 기본 임계값(필요하면 여기만 조정) ----
# 매출: 볼륨 너무 작으면 판단 단어 사용 금지
MIN_NET_SALES_FOR_JUDGE = 1_000_000  # 100만원

# 광고: 월간 기준 최소 10만원 이상 소진(변별력 하한)
MIN_AD_SPEND_FOR_JUDGE = 100_000

# 광고: 광고비/몰매출 비율이 10% 미만이면 "광고 해석"은 제한
MIN_AD_SPEND_RATIO_FOR_JUDGE = 0.10

# 전환(Conversion): 구매수가 너무 작으면 변동이 우연일 수 있음
MIN_PURCHASES_FOR_CONVERSION_JUDGE = 10


@dataclass(frozen=True)
class GuardrailResult:
    ok: bool
    reason: str


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default


def can_judge_sales(mall_sales: Dict[str, Any]) -> GuardrailResult:
    """
    mall_sales expected:
      {
        "this": {"net_sales": ...},
        "prev": {"net_sales": ...},
        "yoy":  {"net_sales": ...},   # optional
      }
    """
    this_net = _safe_float((mall_sales.get("this") or {}).get("net_sales"))
    prev_net = _safe_float((mall_sales.get("prev") or {}).get("net_sales"))

    if this_net < MIN_NET_SALES_FOR_JUDGE:
        return GuardrailResult(
            ok=False,
            reason=f"매출 볼륨이 작아 판단 제한(this.net_sales<{MIN_NET_SALES_FOR_JUDGE})",
        )

    # prev가 0이면 % 비교가 왜곡되기 쉬움 → 판단 문장 제한
    if prev_net <= 0:
        return GuardrailResult(
            ok=False,
            reason="전월 매출이 0이거나 매우 작아 비교 판단 제한(prev.net_sales<=0)",
        )

    return GuardrailResult(ok=True, reason="매출 판단 조건 충족")


def can_judge_ads_account(meta_ads: Dict[str, Any], mall_sales: Dict[str, Any]) -> GuardrailResult:
    """
    meta_ads expected:
      {
        "this": {"spend": ...},
        "prev": {"spend": ...},
      }

    판단 조건:
      - 월 광고비 >= 10만원
      - AND (광고비/순매출) >= 10% (순매출이 0이면 ratio 판단 불가 → 제한)
    """
    this_spend = _safe_float((meta_ads.get("this") or {}).get("spend"))
    this_net = _safe_float((mall_sales.get("this") or {}).get("net_sales"))

    if this_spend < MIN_AD_SPEND_FOR_JUDGE:
        return GuardrailResult(
            ok=False,
            reason=f"광고비가 작아 광고 해석 제한(this.spend<{MIN_AD_SPEND_FOR_JUDGE})",
        )

    # 순매출이 0이면 광고비 비율 기반 변별력 판단 불가 → 보수적으로 제한
    if this_net <= 0:
        return GuardrailResult(
            ok=False,
            reason="순매출이 0이거나 매우 작아 광고비 비율 판단 불가(this.net_sales<=0)",
        )

    ratio = this_spend / this_net
    if ratio < MIN_AD_SPEND_RATIO_FOR_JUDGE:
        return GuardrailResult(
            ok=False,
            reason=f"광고비/매출 비율이 낮아 해석 제한(spend_ratio<{MIN_AD_SPEND_RATIO_FOR_JUDGE:.2f})",
        )

    return GuardrailResult(ok=True, reason="광고 계정 판단 조건 충족")


def can_judge_goal(goal_type: str, goal_data: Dict[str, Any]) -> GuardrailResult:
    """
    goal_type: "traffic" | "conversion" | "awareness" (기타는 unknown 취급)
    goal_data minimal:
      {
        "spend": ...,
        "clicks": ...,
        "purchases": ...,
        # ctr/cpc/cvr/roas 등은 있어도 되고 없어도 됨
      }

    규칙:
      - awareness: 판단 금지(지출 비중만)
      - 공통: spend >= 10만원
      - conversion: purchases >= 10
      - traffic: spend >= 10만원이면 CTR/CPC를 '현상'으로만 비교 가능
    """
    gt = (goal_type or "").strip().lower()
    spend = _safe_float(goal_data.get("spend"))
    purchases = _safe_int(goal_data.get("purchases"))

    if gt == "awareness":
        return GuardrailResult(ok=False, reason="도달/인지 캠페인은 성과 판단 대상 아님")

    if spend < MIN_AD_SPEND_FOR_JUDGE:
        return GuardrailResult(ok=False, reason=f"목표별 광고비가 작아 판단 제한(spend<{MIN_AD_SPEND_FOR_JUDGE})")

    if gt == "conversion":
        if purchases < MIN_PURCHASES_FOR_CONVERSION_JUDGE:
            return GuardrailResult(
                ok=False,
                reason=f"전환(구매) 표본이 작아 판단 제한(purchases<{MIN_PURCHASES_FOR_CONVERSION_JUDGE})",
            )
        return GuardrailResult(ok=True, reason="전환 목표 판단 조건 충족")

    if gt == "traffic":
        # traffic은 purchases 조건 없이도 "현상 비교"는 가능하되, 문장은 보수적으로
        return GuardrailResult(ok=True, reason="유입 목표 판단 조건 충족(현상 비교 한정)")

    # unknown goal: 보수적으로 제한
    return GuardrailResult(ok=False, reason="목표 분류가 불명확하여 판단 제한(goal=unknown)")


def build_guardrail_flags(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    snapshot_json 전체를 넣으면, 리포트 생성기가 쓰기 좋은 flags를 만들어준다.

    기대 구조(현재 스냅샷 기준):
      snapshot["facts"]["mall_sales"]
      snapshot["facts"]["meta_ads"]

    반환 예:
      {
        "sales": {"ok": True, "reason": "..."},
        "ads_account": {"ok": False, "reason": "..."}
      }
    """
    facts = snapshot.get("facts") or {}
    mall_sales = facts.get("mall_sales") or {}
    meta_ads = facts.get("meta_ads") or {}

    sales_r = can_judge_sales(mall_sales)
    ads_r = can_judge_ads_account(meta_ads, mall_sales)

    return {
        "sales": {"ok": sales_r.ok, "reason": sales_r.reason},
        "ads_account": {"ok": ads_r.ok, "reason": ads_r.reason},
    }
