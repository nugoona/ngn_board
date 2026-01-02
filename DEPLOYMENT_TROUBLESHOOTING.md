# 배포 문제 해결 가이드

## 현재 상황
- 로컬 코드는 이미 수정됨 (`gzip.GzipFile` 사용)
- 배포 후에도 여전히 같은 오류 발생
- `_GzipDecoder.decompress() got an unexpected keyword argument 'max_length'`

## 가능한 원인

### 1. 배포가 제대로 안 되었을 수 있음
- 새 이미지가 빌드되지 않았을 수 있음
- Cloud Run이 이전 이미지를 사용 중일 수 있음

### 2. 확인 방법

#### 배포 스크립트 재실행
```bash
set -euo pipefail
cd ~/ngn_board

# 1️⃣ 반드시 최신 코드
git pull origin main

PROJECT="winged-precept-443218-v8"
REGION_AR="asia-northeast1"
REGION_RUN="asia-northeast1"
REPO="ngn-dashboard"
SERVICE="ngn-wep"
SA="439320386143-compute@developer.gserviceaccount.com"

IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/ngn-dashboard:deploy-$(date +%Y%m%d-%H%M%S)"

# 2️⃣ env 로드
set -a
source config/ngn.env
set +a

# 3️⃣ Dockerfile 복사
cp docker/Dockerfile-dashboard ./Dockerfile

# 4️⃣ 빌드 (--no-cache 옵션 추가하여 강제 재빌드)
gcloud builds submit --tag "$IMAGE" . --no-cache

# 3️⃣에서 복사한 Dockerfile 정리
rm ./Dockerfile

# 5️⃣ 배포
gcloud run deploy "$SERVICE" \
  --image="$IMAGE" \
  --region="$REGION_RUN" \
  --platform=managed \
  --allow-unauthenticated \
  --service-account="$SA" \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --cpu-boost \
  --execution-environment=gen2 \
  --update-env-vars="META_SYSTEM_TOKEN=${META_SYSTEM_TOKEN:-},META_SYSTEM_USER_TOKEN=${META_SYSTEM_USER_TOKEN:-},CRAWL_FUNCTION_URL=https://asia-northeast3-winged-precept-443218-v8.cloudfunctions.net/crawl_catalog"
```

#### Cloud Run 서비스 확인
```bash
# 현재 배포된 이미지 확인
gcloud run services describe ngn-wep \
  --region=asia-northeast1 \
  --project=winged-precept-443218-v8 \
  --format="value(spec.template.spec.containers[0].image)"
```

#### 로그 확인
```bash
# 최근 로그 확인
gcloud run services logs read ngn-wep \
  --region=asia-northeast1 \
  --project=winged-precept-443218-v8 \
  --limit=50
```

### 3. 강제 재배포 방법

#### 방법 1: --no-cache 옵션 사용
```bash
gcloud builds submit --tag "$IMAGE" . --no-cache
```

#### 방법 2: 이미지 태그에 타임스탬프 포함 (이미 사용 중)
```bash
IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/ngn-dashboard:deploy-$(date +%Y%m%d-%H%M%S)"
```

#### 방법 3: Cloud Run 서비스 강제 업데이트
```bash
gcloud run services update ngn-wep \
  --region=asia-northeast1 \
  --project=winged-precept-443218-v8 \
  --image="$IMAGE" \
  --no-traffic
```

### 4. 코드 확인

#### 로컬 파일 확인
```bash
# 수정된 코드가 있는지 확인
grep -n "gzip.GzipFile" ngn_wep/dashboard/handlers/data_handler.py
grep -n "gzip.decompress" ngn_wep/dashboard/handlers/data_handler.py
```

#### 예상 결과
- `gzip.GzipFile` 있어야 함
- `gzip.decompress` 없어야 함

### 5. 배포 후 확인

#### 브라우저 캐시 클리어
- 하드 리프레시: `Ctrl+Shift+R` (Windows) / `Cmd+Shift+R` (Mac)
- 또는 개발자 도구에서 "Disable cache" 체크

#### 서버 로그 확인
- Cloud Run 로그에서 실제 오류 메시지 확인
- 스택 트레이스 확인

## 빠른 해결 방법

1. **배포 스크립트에 `--no-cache` 추가하여 재배포**
2. **배포 후 브라우저 캐시 클리어**
3. **Cloud Run 로그 확인하여 실제 오류 확인**

