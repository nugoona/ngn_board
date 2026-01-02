# 배포 스크립트 문제점 및 수정 사항

## 발견된 문제점

### 1. 환경 변수 로드 방식의 문제 ⚠️
**원본 코드:**
```bash
export $(grep -v '^#' .env | grep GEMINI_API_KEY | xargs)
```

**문제점:**
- `xargs`는 공백으로 구분하므로 API 키에 공백이나 특수문자가 있으면 잘못 파싱됩니다
- `export $(...)` 방식은 값에 특수문자가 있으면 쉘에서 오류가 발생할 수 있습니다

**수정:**
```bash
GEMINI_API_KEY=$(grep -v '^#' .env | grep "^GEMINI_API_KEY=" | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs)
export GEMINI_API_KEY
```

### 2. Job 생성/업데이트 로직 누락 ⚠️
**원본 코드:**
```bash
gcloud run jobs update "$JOB" ...
```

**문제점:**
- Job이 존재하지 않으면 `update` 명령이 실패합니다
- 첫 배포는 성공했지만, 두 번째 배포에서 Job이 삭제되었거나 다른 문제가 있을 수 있습니다

**수정:**
```bash
if gcloud run jobs describe "$JOB" --region="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  # 업데이트
  gcloud run jobs update "$JOB" ...
else
  # 생성
  gcloud run jobs create "$JOB" ...
fi
```

### 3. 환경 변수 업데이트 플래그 문제 ⚠️
**원본 코드:**
```bash
--set-env-vars="..."
```

**문제점:**
- `--set-env-vars`는 기존 환경 변수를 모두 덮어씁니다
- 업데이트 시에는 `--update-env-vars`를 사용하는 것이 더 안전합니다

**수정:**
- 생성 시: `--set-env-vars`
- 업데이트 시: `--update-env-vars`

### 4. 경로 확인 누락 ⚠️
**원본 코드:**
```bash
cd ~/ngn_board
```

**문제점:**
- 디렉토리가 존재하지 않으면 스크립트가 계속 실행되어 혼란을 야기할 수 있습니다

**수정:**
```bash
cd ~/ngn_board || {
  echo "❌ [ERROR] ~/ngn_board 디렉토리로 이동할 수 없습니다."
  exit 1
}
```

### 5. Dockerfile 존재 확인 누락 ⚠️
**원본 코드:**
```bash
cp docker/Dockerfile-monthly-ai-analysis ./Dockerfile
```

**문제점:**
- 파일이 없으면 복사가 실패하지만 명확한 오류 메시지가 없습니다

**수정:**
```bash
if [ ! -f "docker/Dockerfile-monthly-ai-analysis" ]; then
  echo "❌ [ERROR] docker/Dockerfile-monthly-ai-analysis 파일을 찾을 수 없습니다."
  exit 1
fi
```

## 수정된 스크립트 사용 방법

1. **수정된 스크립트 사용:**
   ```bash
   bash tools/ai_report_test/jobs/deploy_analysis_fixed.sh
   ```

2. **또는 기존 스크립트를 수정된 버전으로 교체:**
   ```bash
   cp tools/ai_report_test/jobs/deploy_analysis_fixed.sh tools/ai_report_test/jobs/deploy_monthly_ai_analysis.sh
   ```

## 추가 디버깅 팁

### 환경 변수 확인
```bash
# .env 파일 확인
cat .env | grep GEMINI_API_KEY

# 환경 변수 로드 확인
source <(grep -v '^#' .env | grep GEMINI_API_KEY)
echo "API Key 길이: ${#GEMINI_API_KEY}"
```

### Job 상태 확인
```bash
gcloud run jobs describe monthly-ai-analysis-job \
  --region=asia-northeast3 \
  --project=winged-precept-443218-v8
```

### 수동 실행 테스트
```bash
gcloud run jobs execute monthly-ai-analysis-job \
  --region=asia-northeast3 \
  --project=winged-precept-443218-v8
```

