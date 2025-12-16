import os, sys, logging
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery
from dotenv import load_dotenv

# ✅ 환경설정 --------------------------------------------------------------
load_dotenv("/app/.env")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
client = bigquery.Client()

# ✅ 날짜 ------------------------------------------------------------------
KST       = timezone(timedelta(hours=9))
now       = datetime.now(timezone.utc).astimezone(KST)
today     = now.strftime("%Y-%m-%d")
yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

# ✅ 로깅 ------------------------------------------------------------------
logging.basicConfig(stream=sys.stdout,
                    level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

def run_merge(query: str, label: str):
    logging.info(f"⚡  MERGE 시작 → {label}")
    client.query(query).result()
    logging.info(f"✅  MERGE 완료  → {label}")

# -------------------------------------------------------------------------
def main(target_date: str):
    # 공통 계산식 ----------------------------------------------------------
    def pv_expr() -> str:
        return """SUM(CASE
                       WHEN ad.purchase_value = 0 AND ad.shared_purchase_value > 0
                       THEN ad.shared_purchase_value
                       ELSE ad.purchase_value
                     END)"""

    def base_expr() -> str:
        return f"""{pv_expr()} AS purchase_value,
                    CAST(SAFE_DIVIDE(SUM(ad.spend), NULLIF(SUM(ad.clicks),      0)) AS INT64) AS CPC,
                    ROUND(SAFE_DIVIDE(SUM(ad.clicks), NULLIF(SUM(ad.impressions),0))*100,2) AS CTR,
                    CAST(SAFE_DIVIDE(SUM(ad.spend), NULLIF(SUM(ad.impressions),0))*1000 AS INT64) AS CPM,
                    ROUND(SAFE_DIVIDE(SUM(ad.purchases), NULLIF(SUM(ad.clicks),  0))*100,2) AS CVR,
                    ROUND(SAFE_DIVIDE({pv_expr()},        NULLIF(SUM(ad.spend),  0))*100,2) AS ROAS,
                    IFNULL(SAFE_DIVIDE({pv_expr()},       NULLIF(SUM(ad.purchases),0)),0)     AS CT"""

    updated_ts = "CURRENT_TIMESTAMP() AS updated_at"

    # 이름·상태의 “가장 최신 값”을 얻는 공통 helper -------------------------
    def latest_names_sub(level: str, key_cols: list[str], fields: list[str]) -> str:
        """
        level : 'account' | 'campaign' | 'adset' | 'ad'
        key_cols : ID 컬럼 리스트
        fields   : 최신값을 뽑아올 문자열 컬럼 리스트
        """
        keys   = ", ".join(key_cols)
        select_f = ",\n         ".join(fields)

        return f"""
          SELECT {keys},
                 {select_f},
                 updated_at
          FROM (
              SELECT {keys},
                     {select_f},
                     updated_at,
                     ROW_NUMBER() OVER (PARTITION BY {keys} ORDER BY updated_at DESC) AS rn
              FROM `ngn_dataset.meta_ads_ad_level`
              WHERE updated_at IS NOT NULL
          )
          WHERE rn = 1
        """

    # ------------------- MERGE 쿼리 dict ---------------------------------
    queries: dict[str, str] = {
        # account_summary ··· (기존 그대로) -------------------------------
        "account_summary": f"""
          MERGE `ngn_dataset.meta_ads_account_summary` T
          USING (
            WITH latest AS (
              {latest_names_sub("account", ["account_id"], ["account_name"])}
            )
            SELECT ad.date,
                   acc.company_name,
                   ad.account_id,
                   SUM(ad.spend)       AS spend,
                   SUM(ad.impressions) AS impressions,
                   SUM(ad.clicks)      AS clicks,
                   SUM(ad.purchases)   AS purchases,
                   {base_expr()},
                   {updated_ts},
                   l.account_name
            FROM `ngn_dataset.meta_ads_ad_level` ad
            LEFT JOIN `ngn_dataset.metaAds_acc`   acc ON ad.account_id = acc.meta_acc_id
            LEFT JOIN latest l                     ON ad.account_id = l.account_id
            WHERE ad.date = '{target_date}' AND ad.ad_id IS NOT NULL
            GROUP BY ad.date, acc.company_name, ad.account_id, l.account_name
          ) S
          ON  T.date = S.date 
              AND T.account_id = S.account_id
              AND T.date = DATE('{target_date}')
          WHEN MATCHED THEN UPDATE SET
               company_name   = S.company_name,
               account_name   = S.account_name,
               spend          = S.spend,
               impressions    = S.impressions,
               clicks         = S.clicks,
               purchases      = S.purchases,
               purchase_value = S.purchase_value,
               CPC = S.CPC, CTR = S.CTR, CPM = S.CPM, CVR = S.CVR,
               ROAS = S.ROAS, CT = S.CT, updated_at = S.updated_at
          WHEN NOT MATCHED THEN INSERT (
               date, company_name, account_id, account_name,
               spend, impressions, clicks, purchases, purchase_value,
               CPC, CTR, CPM, CVR, ROAS, CT, updated_at
          ) VALUES (
               date, company_name, account_id, account_name,
               spend, impressions, clicks, purchases, purchase_value,
               CPC, CTR, CPM, CVR, ROAS, CT, updated_at
          );
        """,

        # campaign_summary ··· (기존 그대로) ------------------------------
        "campaign_summary": f"""
          MERGE `ngn_dataset.meta_ads_campaign_summary` T
          USING (
            WITH latest AS (
              {latest_names_sub("campaign", ["campaign_id"], ["campaign_name"])}
            )
            SELECT ad.date,
                   acc.company_name,
                   ad.account_id,
                   ad.campaign_id,
                   SUM(ad.spend)       AS spend,
                   SUM(ad.impressions) AS impressions,
                   SUM(ad.clicks)      AS clicks,
                   SUM(ad.purchases)   AS purchases,
                   {base_expr()},
                   {updated_ts},
                   l.campaign_name
            FROM `ngn_dataset.meta_ads_ad_level` ad
            LEFT JOIN `ngn_dataset.metaAds_acc` acc ON ad.account_id = acc.meta_acc_id
            LEFT JOIN latest l                     ON ad.campaign_id = l.campaign_id
            WHERE ad.date = '{target_date}' AND ad.ad_id IS NOT NULL
            GROUP BY ad.date, acc.company_name, ad.account_id, ad.campaign_id, l.campaign_name
          ) S
          ON  T.date = S.date 
              AND T.account_id = S.account_id 
              AND T.campaign_id = S.campaign_id
              AND T.date = DATE('{target_date}')
          WHEN MATCHED THEN UPDATE SET
               company_name   = S.company_name,
               campaign_name  = S.campaign_name,
               spend          = S.spend,
               impressions    = S.impressions,
               clicks         = S.clicks,
               purchases      = S.purchases,
               purchase_value = S.purchase_value,
               CPC = S.CPC, CTR = S.CTR, CPM = S.CPM, CVR = S.CVR,
               ROAS = S.ROAS, CT = S.CT, updated_at = S.updated_at
          WHEN NOT MATCHED THEN INSERT (
               date, company_name, account_id, campaign_id, campaign_name,
               spend, impressions, clicks, purchases, purchase_value,
               CPC, CTR, CPM, CVR, ROAS, CT, updated_at
          ) VALUES (
               date, company_name, account_id, campaign_id, campaign_name,
               spend, impressions, clicks, purchases, purchase_value,
               CPC, CTR, CPM, CVR, ROAS, CT, updated_at
          );
        """,

        # adset_summary ··· (기존 그대로) ---------------------------------
        "adset_summary": f"""
          MERGE `ngn_dataset.meta_ads_adset_summary` T
          USING (
            WITH latest AS (
              {latest_names_sub("adset", ["adset_id"], ["adset_name"])}
            )
            SELECT ad.date,
                   acc.company_name,
                   ad.account_id,
                   ad.campaign_id,
                   ad.adset_id,
                   SUM(ad.spend)       AS spend,
                   SUM(ad.impressions) AS impressions,
                   SUM(ad.clicks)      AS clicks,
                   SUM(ad.purchases)   AS purchases,
                   {base_expr()},
                   {updated_ts},
                   l.adset_name
            FROM `ngn_dataset.meta_ads_ad_level` ad
            LEFT JOIN `ngn_dataset.metaAds_acc` acc ON ad.account_id = acc.meta_acc_id
            LEFT JOIN latest l                     ON ad.adset_id   = l.adset_id
            WHERE ad.date = '{target_date}' AND ad.ad_id IS NOT NULL
            GROUP BY ad.date, acc.company_name, ad.account_id, ad.campaign_id, ad.adset_id, l.adset_name
          ) S
          ON  T.date = S.date 
              AND T.account_id = S.account_id
              AND T.campaign_id = S.campaign_id 
              AND T.adset_id = S.adset_id
              AND T.date = DATE('{target_date}')
          WHEN MATCHED THEN UPDATE SET
               company_name   = S.company_name,
               adset_name     = S.adset_name,
               spend          = S.spend,
               impressions    = S.impressions,
               clicks         = S.clicks,
               purchases      = S.purchases,
               purchase_value = S.purchase_value,
               CPC = S.CPC, CTR = S.CTR, CPM = S.CPM, CVR = S.CVR,
               ROAS = S.ROAS, CT = S.CT, updated_at = S.updated_at
          WHEN NOT MATCHED THEN INSERT (
               date, company_name, account_id, campaign_id, adset_id, adset_name,
               spend, impressions, clicks, purchases, purchase_value,
               CPC, CTR, CPM, CVR, ROAS, CT, updated_at
          ) VALUES (
               date, company_name, account_id, campaign_id, adset_id, adset_name,
               spend, impressions, clicks, purchases, purchase_value,
               CPC, CTR, CPM, CVR, ROAS, CT, updated_at
          );
        """,

        # 🆕 ad_summary ----------------------------------------------------
        "ad_summary": f"""
          MERGE `ngn_dataset.meta_ads_ad_summary` T
          USING (
            WITH latest AS (
              SELECT * EXCEPT(rn) FROM (
                  SELECT ad_id,
                         account_id,
                         campaign_id,
                         adset_id,
                         account_name,
                         campaign_name,
                         adset_name,
                         ad_name,
                         ad_status,
                         updated_at,
                         ROW_NUMBER() OVER (PARTITION BY ad_id ORDER BY updated_at DESC) AS rn
                  FROM `ngn_dataset.meta_ads_ad_level`
                  WHERE ad_id IS NOT NULL AND updated_at IS NOT NULL
              )
              WHERE rn = 1
            )
            SELECT ad.date,
                   acc.company_name,
                   ad.account_id,
                   ad.campaign_id,
                   ad.adset_id,
                   ad.ad_id,
                   SUM(ad.spend)       AS spend,
                   SUM(ad.impressions) AS impressions,
                   SUM(ad.clicks)      AS clicks,
                   SUM(ad.purchases)   AS purchases,
                   {base_expr()},
                   {updated_ts},
                   l.account_name,
                   l.campaign_name,
                   l.adset_name,
                   l.ad_name,
                   l.ad_status
            FROM `ngn_dataset.meta_ads_ad_level` ad
            LEFT JOIN `ngn_dataset.metaAds_acc` acc ON ad.account_id = acc.meta_acc_id
            LEFT JOIN latest l                     ON ad.ad_id      = l.ad_id
            WHERE ad.date = '{target_date}'
              AND ad.ad_id IS NOT NULL
            GROUP BY ad.date, acc.company_name,
                     ad.account_id, ad.campaign_id, ad.adset_id, ad.ad_id,
                     l.account_name, l.campaign_name, l.adset_name, l.ad_name, l.ad_status
          ) S
          ON  T.date        = S.date
              AND T.account_id  = S.account_id
              AND T.campaign_id = S.campaign_id
              AND T.adset_id    = S.adset_id
              AND T.ad_id       = S.ad_id
              AND T.date        = DATE('{target_date}')
          WHEN MATCHED THEN UPDATE SET
               company_name   = S.company_name,
               account_name   = S.account_name,
               campaign_name  = S.campaign_name,
               adset_name     = S.adset_name,
               ad_name        = S.ad_name,
               ad_status      = S.ad_status,
               spend          = S.spend,
               impressions    = S.impressions,
               clicks         = S.clicks,
               purchases      = S.purchases,
               purchase_value = S.purchase_value,
               CPC = S.CPC, CTR = S.CTR, CPM = S.CPM, CVR = S.CVR,
               ROAS = S.ROAS, CT = S.CT, updated_at = S.updated_at
          WHEN NOT MATCHED THEN INSERT (
               date, company_name, account_id, campaign_id, adset_id, ad_id,
               account_name, campaign_name, adset_name, ad_name, ad_status,
               spend, impressions, clicks, purchases, purchase_value,
               CPC, CTR, CPM, CVR, ROAS, CT, updated_at
          ) VALUES (
               date, company_name, account_id, campaign_id, adset_id, ad_id,
               account_name, campaign_name, adset_name, ad_name, ad_status,
               spend, impressions, clicks, purchases, purchase_value,
               CPC, CTR, CPM, CVR, ROAS, CT, updated_at
          );
        """
    }

    # ----------------- 실행 루프 ----------------------------------------
    for label, q in queries.items():
        run_merge(q, label)


# -------------------------------------------------------------------------
if __name__ == "__main__":
    mode   = sys.argv[1] if len(sys.argv) > 1 else "today"
    target = today if mode == "today" else yesterday
    logging.info(f"✨ Meta Ads Summary MERGE — {target}")
    main(target)
