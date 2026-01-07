@echo off
REM query-sales-prev-month-job 배포 스크립트 (Windows)

REM 2-1. 변수 설정
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%-%datetime:~8,6%
set PROJECT=winged-precept-443218-v8
set IMAGE=asia-northeast1-docker.pkg.dev/%PROJECT%/ngn-dashboard/query-sales-prev-month-job:manual-%TIMESTAMP%

REM 2-2. Dockerfile을 루트로 복사
copy docker\Dockerfile-sales-prev-month Dockerfile

REM 2-3. 빌드 및 업데이트 실행
gcloud builds submit --tag="%IMAGE%" --project="%PROJECT%" . && ^
gcloud run jobs update query-sales-prev-month-job --image="%IMAGE%" --region="asia-northeast3" --project="%PROJECT%" --service-account="439320386143-compute@developer.gserviceaccount.com" --memory=1Gi --cpu=1 --max-retries=2 --task-timeout=3600s

REM 2-4. 임시 파일 삭제
del Dockerfile

