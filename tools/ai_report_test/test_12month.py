#!/usr/bin/env python3
import sys
sys.path.insert(0, '/path/to/ngn_board')  # 프로젝트 루트 경로로 변경

from tools.ai_report_test.bq_monthly_snapshot import run

run(
    company_name="piscess",
    year=2025,
    month=12,
    upsert_flag=False,
    save_to_gcs_flag=True,
    load_from_gcs_flag=False
)
