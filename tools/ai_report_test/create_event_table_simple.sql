-- ============================================
-- sheets_event_data 테이블 생성 (간단 버전)
-- ============================================
-- 파티션 없이 먼저 생성

CREATE TABLE IF NOT EXISTS `winged-precept-443218-v8.ngn_dataset.sheets_event_data` (
  mall STRING NOT NULL,
  date DATE,
  event STRING NOT NULL,
  event_first DATE,
  event_end DATE,
  memo STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
OPTIONS (
  description = "Google Sheets event 시트 데이터. mall별 이벤트 정보를 저장합니다."
);

