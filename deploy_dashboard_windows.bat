@echo off
REM 대시보드 서비스 배포 스크립트 (Windows)

REM 1. 변수 설정
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%-%datetime:~8,6%
set PROJECT=winged-precept-443218-v8
set REGION_AR=asia-northeast1
set REGION_RUN=asia-northeast1
set REPO=ngn-dashboard
set SERVICE=ngn-wep
set SA=439320386143-compute@developer.gserviceaccount.com
set IMAGE=%REGION_AR%-docker.pkg.dev/%PROJECT%/%REPO%/ngn-dashboard:deploy-%TIMESTAMP%

echo ============================================
echo 🚀 대시보드 서비스 배포 시작
echo ============================================
echo 이미지 태그: %IMAGE%
echo.

REM 2. Dockerfile 복사
echo 📋 Dockerfile 복사 중...
copy docker\Dockerfile-dashboard Dockerfile
if errorlevel 1 (
    echo ❌ Dockerfile 복사 실패!
    exit /b 1
)

REM 3. Docker 이미지 빌드
echo 🔨 Docker 이미지 빌드 중... (이 작업은 몇 분 걸릴 수 있습니다)
gcloud builds submit --tag="%IMAGE%" --project="%PROJECT%" .
if errorlevel 1 (
    echo ❌ 빌드 실패!
    del Dockerfile
    exit /b 1
)

REM 4. 임시 Dockerfile 삭제
echo 🧹 임시 파일 정리 중...
del Dockerfile

REM 5. Cloud Run 서비스 배포
echo 🚀 Cloud Run 서비스 배포 중...
gcloud run deploy "%SERVICE%" ^
  --image="%IMAGE%" ^
  --region="%REGION_RUN%" ^
  --platform=managed ^
  --allow-unauthenticated ^
  --service-account="%SA%" ^
  --memory=1Gi ^
  --cpu=1 ^
  --min-instances=0 ^
  --max-instances=3 ^
  --cpu-boost ^
  --execution-environment=gen2 ^
  --update-env-vars="CRAWL_FUNCTION_URL=https://asia-northeast3-winged-precept-443218-v8.cloudfunctions.net/crawl_catalog" ^
  --project="%PROJECT%"

if errorlevel 1 (
    echo ❌ 배포 실패!
    exit /b 1
)

echo.
echo ============================================
echo ✅ 배포 완료!
echo ============================================
echo 배포된 이미지: %IMAGE%
echo.
echo 💡 배포 확인:
echo    gcloud run services describe %SERVICE% --region=%REGION_RUN% --project=%PROJECT%

