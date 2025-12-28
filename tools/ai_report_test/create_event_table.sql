-- ============================================
-- sheets_event_data 테이블 생성
-- ============================================
-- Google Sheets의 event 시트 데이터를 저장하는 테이블
-- ============================================

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
PARTITION BY DATE(date)
CLUSTER BY mall, event;

-- 인덱스 생성 (클러스터링으로 대체됨)
-- CLUSTER BY는 이미 위에서 설정됨

-- 설명 추가
ALTER TABLE `winged-precept-443218-v8.ngn_dataset.sheets_event_data`
SET OPTIONS (
  description = "Google Sheets event 시트 데이터. mall별 이벤트 정보를 저장합니다."
);

