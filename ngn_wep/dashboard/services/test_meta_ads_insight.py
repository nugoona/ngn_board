# File: test_meta_ads_insight.py

import os
from services.meta_ads_insight import get_meta_ads_insight_table

# ✅ GCP 인증: ADC 사용 (로컬 개발 시 gcloud auth application-default login 필요)

# ✅ 공통 파라미터
company_name = "acoc"
start_date = "2025-01-01"
end_date = "2025-02-01"

def print_sample(title, rows):
    print(f"\n🟦 {title} 결과: {len(rows)}건")
    if rows:
        print("예시:")
        for row in rows[:3]:
            print(row)
    else:
        print("결과 없음.")

if __name__ == "__main__":

    # 🔹 1. Account level
    account_rows = get_meta_ads_insight_table(
        level="account",
        company_name=company_name,
        start_date=start_date,
        end_date=end_date
    )
    print_sample("📊 Account", account_rows)

    # 🔹 2. Campaign level
    if account_rows:
        account_id = account_rows[0]["account_id"]
        campaign_rows = get_meta_ads_insight_table(
            level="campaign",
            company_name=company_name,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id
        )
        print_sample("📊 Campaign", campaign_rows)
    else:
        print("\n⚠️ Account 데이터 없음 → Campaign 테스트 생략")

    # 🔹 3. Adset level
    if 'campaign_rows' in locals() and campaign_rows:
        campaign_id = campaign_rows[0]["campaign_id"]
        adset_rows = get_meta_ads_insight_table(
            level="adset",
            company_name=company_name,
            start_date=start_date,
            end_date=end_date,
            campaign_id=campaign_id
        )
        print_sample("📊 Adset", adset_rows)
    else:
        print("\n⚠️ Campaign 데이터 없음 → Adset 테스트 생략")

    # 🔹 4. Ad level
    if 'adset_rows' in locals() and adset_rows:
        adset_id = adset_rows[0]["adset_id"]
        ad_rows = get_meta_ads_insight_table(
            level="ad",
            company_name=company_name,
            start_date=start_date,
            end_date=end_date,
            adset_id=adset_id
        )
        print_sample("📊 Ad", ad_rows)
    else:
        print("\n⚠️ Adset 데이터 없음 → Ad 테스트 생략")
