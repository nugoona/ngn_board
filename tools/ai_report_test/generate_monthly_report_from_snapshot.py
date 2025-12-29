import os
import sys
import json
from google.cloud import bigquery

from tools.ai_report_test.judgement_guardrails import build_guardrail_flags

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
DATASET = "ngn_dataset"


def load_snapshot(company_name: str, month_key: str) -> dict:
    """
    month_key: 'YYYY-MM-01' (월 시작일)
    """
    client = bigquery.Client(project=PROJECT_ID)
    q = f"""
    SELECT TO_JSON_STRING(snapshot_json) AS snapshot_json, snapshot_hash
    FROM `{PROJECT_ID}.{DATASET}.report_monthly_snapshot`
    WHERE company_name = @company_name AND month = DATE(@month_key)
    ORDER BY updated_at DESC
    LIMIT 1
    """
    rows = list(
        client.query(
            q,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                    bigquery.ScalarQueryParameter("month_key", "STRING", month_key),
                ]
            ),
        ).result()
    )
    if not rows:
        raise RuntimeError(f"No snapshot found for {company_name} {month_key}")

    snap = json.loads(rows[0].snapshot_json)
    snap["snapshot_hash"] = rows[0].snapshot_hash
    return snap


def fmt_money(x: float) -> str:
    try:
        return f"{int(round(float(x))):,}원"
    except Exception:
        return f"{x}원"


def fmt_pct(x):
    if x is None:
        return "비교불가"
    try:
        return f"{float(x):.1f}%"
    except Exception:
        return str(x)


def main():
    # Usage:
    # python3 tools/ai_report_test/generate_monthly_report_from_snapshot.py piscess 2025-01-01
    if len(sys.argv) != 3:
        print("Usage: python3 generate_monthly_report_from_snapshot.py <company_name> <month_key YYYY-MM-01>")
        sys.exit(1)

    company = sys.argv[1]
    month_key = sys.argv[2]

    snap = load_snapshot(company, month_key)

    meta = snap["report_meta"]
    facts = snap["facts"]

    ms = facts["mall_sales"]
    ads = facts["meta_ads"]

    this_label = meta["period_this"]["label"]
    prev_label = meta["period_prev"]["label"]
    yoy_label = meta["period_yoy"]["label"]

    # Guardrails (판단 통제)
    flags = build_guardrail_flags(snap)
    sales_ok = flags["sales"]["ok"]
    ads_ok = flags["ads_account"]["ok"]

    # YoY 데이터가 0이면 "없음" 처리
    has_yoy_sales = (ms.get("yoy", {}).get("net_sales", 0) or 0) > 0
    has_yoy_ads = (ads.get("yoy", {}).get("spend", 0) or 0) > 0

    # ============================================
    # 비용 0원 계산 로직 (In-Memory Calculation)
    # ============================================
    sales_this = ms.get("this", {}).get("net_sales", 0) or 0
    sales_prev = ms.get("prev", {}).get("net_sales", 0) or 0
    orders_this = ms.get("this", {}).get("total_orders", 0) or 0
    orders_prev = ms.get("prev", {}).get("total_orders", 0) or 0
    
    # 매출 증감률
    sales_growth = ((sales_this - sales_prev) / sales_prev * 100) if sales_prev > 0 else 0.0
    sales_growth_str = f"{sales_growth:.1f}%"
    
    # 주문 증감률
    order_growth = ((orders_this - orders_prev) / orders_prev * 100) if orders_prev > 0 else 0.0
    order_growth_str = f"{order_growth:.1f}%"
    
    # 객단가 (AOV)
    aov = (sales_this / orders_this) if orders_this > 0 else 0.0
    aov_str = fmt_money(aov)
    
    # 광고 의존도 (Paid 매체 유입수 / 전체 유입수)
    ga4_this = facts.get("ga4_traffic", {}).get("this", {})
    ga4_totals = ga4_this.get("totals", {})
    total_users = ga4_totals.get("total_users", 0) or 0
    
    # Paid 매체 유입수 계산 (meta_ad, ig, tiktok 등)
    top_sources = ga4_this.get("top_sources", [])
    paid_users = 0
    paid_source_names = ["meta_ad", "ig", "tiktok", "facebook", "instagram", "meta"]
    for source in top_sources:
        source_name = source.get("source", "").lower()
        if any(paid_name in source_name for paid_name in paid_source_names):
            paid_users += source.get("total_users", 0) or 0
    
    ad_dependency = (paid_users / total_users * 100) if total_users > 0 else 0.0
    ad_dependency_str = f"{ad_dependency:.1f}%"

    report_lines = []

    # ============================================
    # AI 프롬프트에 '계산된 정답' 주입하기
    # ============================================
    report_lines.append("## [Context: Calculated Facts]")
    report_lines.append("> **Warning: 아래 수치는 정확한 팩트이므로, 분석 시 이 숫자를 그대로 인용할 것.**")
    report_lines.append(f"> * 매출 증감: **{sales_growth_str}**")
    report_lines.append(f"> * 주문 증감: **{order_growth_str}**")
    report_lines.append(f"> * 객단가 (AOV): **{aov_str}**")
    report_lines.append(f"> * 현재 광고 의존도: **{ad_dependency_str}**")
    report_lines.append("")

    report_lines.append(f"# 📊 {this_label} 월간 성과 리포트 ({company})")
    report_lines.append(f"- 비교 기준(시스템 고정): **{this_label} vs {prev_label}**")
    report_lines.append(f"- 전년 동월({yoy_label})은 데이터 존재 시 참고")
    report_lines.append("")

    # Guardrails 상태 표시 (클라이언트 안심용)
    report_lines.append("## 0️⃣ 해석 가능 범위(시스템 체크)")
    report_lines.append(f"- 매출 해석 가능: **{('가능' if sales_ok else '제한') }** ({flags['sales']['reason']})")
    report_lines.append(f"- 광고 해석 가능: **{('가능' if ads_ok else '제한') }** ({flags['ads_account']['reason']})")
    report_lines.append("")

    # 1) 사실 요약
    report_lines.append("## 1️⃣ 사실 요약 (데이터)")
    report_lines.append("### 몰 매출(광고비 제외 순매출)")
    report_lines.append(f"- 이번 달 순매출: **{fmt_money(ms['this']['net_sales'])}**")
    report_lines.append(f"- 전월 순매출: **{fmt_money(ms['prev']['net_sales'])}**")
    report_lines.append(f"- 전월 대비 변화: **{fmt_pct(ms.get('net_sales_change_pct'))}**")
    if has_yoy_sales:
        report_lines.append(f"- 전년 동월 순매출: **{fmt_money(ms['yoy']['net_sales'])}**")
        report_lines.append(f"- 전년 동월 대비 변화: **{fmt_pct(ms.get('net_sales_yoy_change_pct'))}**")
    else:
        report_lines.append(f"- 전년 동월({yoy_label}) 데이터가 없어 YoY 비교는 보류합니다.")
    report_lines.append("")

    report_lines.append("### 주문 구조")
    report_lines.append(
        f"- 이번 달 주문수: {ms['this']['total_orders']}건 / 첫구매: {ms['this']['total_first_order']}건 / 취소: {ms['this']['total_canceled']}건"
    )
    report_lines.append(
        f"- 전월 주문수: {ms['prev']['total_orders']}건 / 첫구매: {ms['prev']['total_first_order']}건 / 취소: {ms['prev']['total_canceled']}건"
    )
    report_lines.append("")

    report_lines.append("### 광고(메타)")
    report_lines.append(f"- 이번 달 광고비: **{fmt_money(ads['this']['spend'])}** / 구매금액: **{fmt_money(ads['this']['purchase_value'])}**")
    report_lines.append(f"- 전월 광고비: **{fmt_money(ads['prev']['spend'])}** / 구매금액: **{fmt_money(ads['prev']['purchase_value'])}**")
    if has_yoy_ads:
        report_lines.append(f"- 전년 동월 광고비: **{fmt_money(ads['yoy']['spend'])}** / 구매금액: **{fmt_money(ads['yoy']['purchase_value'])}**")
    else:
        report_lines.append(f"- 전년 동월({yoy_label}) 데이터가 없어 YoY 비교는 보류합니다.")
    report_lines.append(f"- 이번 달 CTR: {ads['this']['ctr']:.2f}% / CVR: {ads['this']['cvr']:.2f}% / ROAS: {ads['this']['roas_percentage']:.1f}%")
    report_lines.append("")

    # 2) 판단 가능 영역 (Guardrails에 따라 분기)
    report_lines.append("## 2️⃣ 판단 가능 영역 (규칙 기반)")

    report_lines.append("- 성과 해석의 1순위 기준은 **광고비 제외 순매출**입니다.")
    report_lines.append("")

    report_lines.append("### 매출 해석")
    if sales_ok:
        # 비교 기반, 단정 금지 톤
        mom = ms.get("net_sales_change_pct")
        if mom is None:
            report_lines.append("- 전월 비교가 제한되어 이번 달은 ‘변화 관찰’ 중심으로 정리합니다.")
        elif mom > 0:
            report_lines.append("- 전월 대비 순매출이 증가했습니다. 다만 전월 매출 볼륨이 작으면 증가율이 과대해 보일 수 있어 **절대값(이번 달 순매출 규모)**도 함께 확인이 필요합니다.")
        elif mom < 0:
            report_lines.append("- 전월 대비 순매출이 감소했습니다. 이벤트/재고/공휴일 변수에 따라 해석이 달라질 수 있어 전제 확인이 필요합니다.")
        else:
            report_lines.append("- 전월 대비 순매출 변화가 크지 않아, 이번 달은 ‘유지/정체’ 관점의 관찰이 필요합니다.")
    else:
        report_lines.append("- 매출 볼륨 또는 비교 조건이 제한되어, 이번 달은 **증감 수치 공유까지만** 진행하고 해석 문장은 보류합니다.")
    report_lines.append("")

    report_lines.append("### 광고 해석(기여도 판단 금지)")
    if ads_ok:
        report_lines.append("- 이번 달 광고비는 변별력 조건을 충족하여, **광고 지표를 ‘현상’ 수준에서 비교**할 수 있습니다.")
        report_lines.append("- 다만 광고가 매출을 ‘만들었다’는 인과는 단정하지 않고, **목표(유입/전환/도달) 믹스에 따라 지표가 달라질 수 있음**을 전제로 해석합니다.")
    else:
        report_lines.append("- 이번 달 광고비/매출 비율 또는 광고비 규모가 제한되어, 광고 지표는 **사실 공유까지만** 진행하고 해석 문장은 보류합니다.")
    report_lines.append("")

    # 3) 전제형 변수
    report_lines.append("## 3️⃣ 전제형 변수 (사실 단정 금지)")
    report_lines.append("- 만약 이번 달에 **이벤트/프로모션(가격 인하 포함)**이 없었다면, 이번 매출 변화는 상품 수요/유입 구조 변화로 해석될 여지가 있습니다.")
    report_lines.append("- 만약 **재고 이슈(품절/입고 지연)**가 없었다면, 다음 달에 동일 구조 재현성 여부를 더 명확히 볼 수 있습니다.")
    report_lines.append("- 공휴일 수/배송 일정 차이가 있었다면 주문/취소 지표 해석이 달라질 수 있습니다.")
    report_lines.append("")

    # 4) 질문 (무조건)
    report_lines.append("## 4️⃣ 다음 달을 위한 질문 3개")
    report_lines.append("1) 이번 달 매출 변동은 **이벤트/프로모션 영향**이 있었나요? (있었다면 어떤 범위였나요)")
    report_lines.append("2) 이번 달 매출을 만든 상위 상품(들)은 **다음 달에도 재고/노출이 유지**되나요?")
    report_lines.append("3) 다음 달 광고비는 **매출의 10~20% 범위**에서 유지/조정(축소·확대) 계획이 있나요?")
    report_lines.append("")
    report_lines.append(f"---\n(snapshot_hash: {snap.get('snapshot_hash')})")

    print("\n".join(report_lines))


if __name__ == "__main__":
    main()
