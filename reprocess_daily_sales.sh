#!/bin/bash
# daily_cafe24_sales 재처리 스크립트
# 삭제된 날짜들을 다시 처리

# 재처리할 날짜 목록 (Step 2에서 확인한 날짜들)
dates=(
    "2025-12-23"
    "2025-12-12"
    "2025-12-05"
    "2025-10-10"
    "2025-08-20"
    "2025-07-14"
    "2025-03-31"
    "2024-12-05"
)

cd ~/ngn_board

for date in "${dates[@]}"; do
    echo "Processing $date..."
    python ngn_wep/cafe24_api/daily_cafe24_sales_handler.py "$date"
    if [ $? -eq 0 ]; then
        echo "✅ $date 처리 완료"
    else
        echo "❌ $date 처리 실패"
    fi
    echo ""
done

echo "모든 날짜 처리 완료!"













