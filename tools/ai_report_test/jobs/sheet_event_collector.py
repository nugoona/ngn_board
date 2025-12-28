import os
import sys
import pandas as pd
import gspread
import google.auth
from google.cloud import bigquery
from datetime import datetime, timezone, timedelta, date

# ✅ 한국 시간대 설정
KST = timezone(timedelta(hours=9))

# ✅ 상수
SPREADSHEET_ID = "1s6QN0-XwUy9BsnPH2euISpNkR9RxHy9oz8HTY8Ld8bQ"  # NGN-CUSTOM-API
SHEET_NAME = "event"  # 시트명
BQ_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
BQ_DATASET = os.environ.get("BQ_DATASET", "ngn_dataset")
BQ_TABLE = "sheets_event_data"

# ✅ 인증 설정 (BigQuery 및 Sheets)
credentials, project = google.auth.default(
    scopes=[
        "https://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com/auth/bigquery",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)
gc = gspread.authorize(credentials)
bq_client = bigquery.Client(project=BQ_PROJECT)


def parse_date(date_str):
    """날짜 문자열 파싱 (YYYY-MM 형식 또는 MM/DD 형식)"""
    if not date_str or pd.isna(date_str):
        return None
    
    date_str = str(date_str).strip()
    
    # YYYY-MM 형식 (예: 2025-12)
    if len(date_str) == 7 and date_str[4] == '-':
        try:
            year, month = map(int, date_str.split('-'))
            return date(year, month, 1)  # 월의 첫날
        except:
            return None
    
    # MM/DD 형식 (예: 12/6, 12/11)
    if '/' in date_str:
        try:
            parts = date_str.split('/')
            if len(parts) == 2:
                month, day = map(int, parts)
                # 현재 연도 사용 (또는 date 컬럼에서 연도 추출)
                current_year = datetime.now(KST).year
                return date(current_year, month, day)
        except:
            return None
    
    return None


def collect_event_data():
    """event 시트 데이터 수집 및 BigQuery 저장"""
    try:
        # 시트 열기
        sheet = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sheet.worksheet(SHEET_NAME)
        
        # 모든 데이터 가져오기
        data = worksheet.get_all_records()
        
        if not data:
            print(f"⚠️ {SHEET_NAME} 시트에 데이터가 없습니다.")
            return
        
        # DataFrame으로 변환
        df = pd.DataFrame(data)
        
        print(f"📊 시트에서 {len(df)}개 행 수집됨")
        
        # 컬럼명 정리 (소문자로 통일)
        df.columns = df.columns.str.lower().str.strip()
        
        # 필수 컬럼 확인
        required_cols = ['mall', 'date', 'event']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"❌ 필수 컬럼 누락: {missing_cols}")
            print(f"   현재 컬럼: {list(df.columns)}")
            return
        
        # 날짜 파싱
        # date 컬럼: YYYY-MM 형식
        df['date_parsed'] = df['date'].apply(lambda x: parse_date(str(x)) if pd.notna(x) else None)
        
        # event_first, event_end 파싱
        df['event_first_parsed'] = df.get('event_first', pd.Series()).apply(
            lambda x: parse_date(str(x)) if pd.notna(x) else None
        )
        df['event_end_parsed'] = df.get('event_end', pd.Series()).apply(
            lambda x: parse_date(str(x)) if pd.notna(x) else None
        )
        
        # 데이터 정리
        df_clean = pd.DataFrame({
            'mall': df['mall'].astype(str).str.strip(),
            'date': df['date_parsed'],
            'event': df['event'].astype(str).str.strip(),
            'event_first': df.get('event_first_parsed', None),
            'event_end': df.get('event_end_parsed', None),
            'memo': df.get('memo', '').astype(str).str.strip() if 'memo' in df.columns else '',
        })
        
        # 빈 행 제거
        df_clean = df_clean[df_clean['mall'].notna() & (df_clean['mall'] != '')]
        df_clean = df_clean[df_clean['event'].notna() & (df_clean['event'] != '')]
        
        if df_clean.empty:
            print(f"⚠️ 정리 후 데이터가 없습니다.")
            return
        
        print(f"✅ 정리 완료: {len(df_clean)}개 행")
        
        # BigQuery에 저장
        temp_table_id = f"{BQ_PROJECT}.{BQ_DATASET}._temp_event_upload_{datetime.now(KST).strftime('%Y%m%d%H%M%S')}"
        
        job_config = bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("mall", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("date", "DATE", mode="NULLABLE"),
                bigquery.SchemaField("event", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("event_first", "DATE", mode="NULLABLE"),
                bigquery.SchemaField("event_end", "DATE", mode="NULLABLE"),
                bigquery.SchemaField("memo", "STRING", mode="NULLABLE"),
            ],
            write_disposition="WRITE_TRUNCATE"
        )
        
        load_job = bq_client.load_table_from_dataframe(df_clean, temp_table_id, job_config=job_config)
        load_job.result()
        
        print(f"✅ 임시 테이블에 로드 완료: {temp_table_id}")
        
        # MERGE 쿼리 실행
        merge_sql = f"""
        MERGE `{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}` T
        USING `{temp_table_id}` S
        ON T.mall = S.mall 
           AND T.date = S.date 
           AND T.event = S.event
        WHEN MATCHED THEN
          UPDATE SET 
            T.event_first = S.event_first,
            T.event_end = S.event_end,
            T.memo = S.memo
        WHEN NOT MATCHED THEN
          INSERT (mall, date, event, event_first, event_end, memo)
          VALUES (S.mall, S.date, S.event, S.event_first, S.event_end, S.memo)
        """
        
        bq_client.query(merge_sql).result()
        print(f"✅ MERGE 완료: {len(df_clean)}개 행 처리됨")
        
        # 임시 테이블 삭제
        bq_client.delete_table(temp_table_id, not_found_ok=True)
        print(f"✅ 임시 테이블 삭제 완료")
        
    except gspread.exceptions.WorksheetNotFound:
        print(f"❌ 시트를 찾을 수 없습니다: {SHEET_NAME}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print(f"🚀 event 시트 수집 시작...")
    print(f"   Spreadsheet ID: {SPREADSHEET_ID}")
    print(f"   Sheet Name: {SHEET_NAME}")
    print(f"   BigQuery Table: {BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}")
    print()
    
    collect_event_data()
    
    print()
    print("✅ 수집 완료!")

