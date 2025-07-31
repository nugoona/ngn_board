import os
import pandas as pd
import gspread
from google.oauth2 import service_account
from google.cloud import bigquery
from datetime import datetime, timezone, timedelta

# ✅ 한국 시간대 설정
KST = timezone(timedelta(hours=9))

# ✅ 환경 변수 기반 인증 설정
GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "/home/oscar/ngn_board/config/service-account.json"
)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

# ✅ 상수
SPREADSHEET_ID = "1s6QN0-XwUy9BsnPH2euISpNkR9RxHy9oz8HTY8Ld8bQ"
BQ_PROJECT = "winged-precept-443218-v8"
BQ_DATASET = "ngn_dataset"
BQ_TABLE = "sheets_platform_sales_data"

# ✅ 인증 설정 (BigQuery 및 Sheets)
credentials = service_account.Credentials.from_service_account_file(
    GOOGLE_APPLICATION_CREDENTIALS,
    scopes=[
        "https://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com/auth/bigquery",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)
gc = gspread.authorize(credentials)
bq_client = bigquery.Client(credentials=credentials, project=BQ_PROJECT)


def get_date_range(days=7):
    today = datetime.now(KST).date()
    return [(today - timedelta(days=i)) for i in range(days)]


def run_sheet_update_for_range(date_obj):
    target_date_str = date_obj.strftime("%Y-%m-%d")
    sheet = gc.open_by_key(SPREADSHEET_ID)
    worksheet_list = sheet.worksheets()
    company_names = [ws.title for ws in worksheet_list]

    all_rows = []

    for company in company_names:
        try:
            worksheet = sheet.worksheet(company)
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)

            df = df[df["DATE"] == target_date_str]
            if df.empty:
                continue

            df["company_name"] = company
            df_melted = df.melt(
                id_vars=["DATE", "company_name"],
                var_name="platform",
                value_name="sales_amount"
            )

            # ✅ null만 제외, 0은 포함
            df_melted = df_melted[df_melted["sales_amount"].notnull()]
            df_melted["DATE"] = pd.to_datetime(df_melted["DATE"]).dt.date
            df_melted["sales_amount"] = df_melted["sales_amount"].astype(int)
            all_rows.append(df_melted)

        except gspread.exceptions.WorksheetNotFound:
            print(f"❌ 시트 없음: {company}")
            continue

    if all_rows:
        final_df = pd.concat(all_rows)
        temp_table_id = f"{BQ_PROJECT}.{BQ_DATASET}._temp_upload_{target_date_str.replace('-', '')}"

        job_config = bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("DATE", "DATE"),
                bigquery.SchemaField("company_name", "STRING"),
                bigquery.SchemaField("platform", "STRING"),
                bigquery.SchemaField("sales_amount", "INTEGER"),
            ],
            write_disposition="WRITE_TRUNCATE"
        )
        load_job = bq_client.load_table_from_dataframe(final_df, temp_table_id, job_config=job_config)
        load_job.result()

        merge_sql = f"""
        MERGE `{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}` T
        USING `{temp_table_id}` S
        ON T.DATE = S.DATE AND T.company_name = S.company_name AND T.platform = S.platform
        WHEN MATCHED AND T.sales_amount != S.sales_amount THEN
          UPDATE SET T.sales_amount = S.sales_amount
        WHEN NOT MATCHED THEN
          INSERT (DATE, company_name, platform, sales_amount)
          VALUES (S.DATE, S.company_name, S.platform, S.sales_amount)
        """
        bq_client.query(merge_sql).result()
        bq_client.delete_table(temp_table_id, not_found_ok=True)

        print(f"✅ {target_date_str} 수집 완료: {len(final_df)}건 MERGE됨")
    else:
        print(f"⚠️ {target_date_str} 수집 대상 없음.")


# ✅ 실행 시작점
if __name__ == "__main__":
    date_range = get_date_range(days=7)  # 오늘 포함 최근 7일

    print(f"▶ 최근 {len(date_range)}일 수집 시작:")
    for date_obj in reversed(date_range):  # 과거부터 오늘 순으로
        run_sheet_update_for_range(date_obj)
