@echo off
REM daily_cafe24_sales_handler.py 관련 Cloud Run Jobs 재배포 스크립트 (Windows)

set REGION_RUN=asia-northeast3
set REGION_AR=asia-northeast1
set REPO=ngn-dashboard
set PROJECT=winged-precept-443218-v8
set SA=439320386143-compute@developer.gserviceaccount.com

REM 타임스탬프 생성 (YYYYMMDD-HHMMSS)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%-%datetime:~8,6%

REM ============================================
REM query-sales-today-job
REM ============================================
echo ============================================
echo 🚀 Deploying query-sales-today-job...
echo ============================================

set JOB=query-sales-today-job
set DOCKERFILE=docker/Dockerfile-sales-today
set IMAGE=%REGION_AR%-docker.pkg.dev/%PROJECT%/%REPO%/%JOB%:manual-%TIMESTAMP%

echo Building image for %JOB%...
gcloud builds submit --tag "%IMAGE%" --dockerfile="%DOCKERFILE%" .

echo Updating Cloud Run Job %JOB%...
gcloud run jobs update "%JOB%" ^
  --image "%IMAGE%" ^
  --region="%REGION_RUN%" ^
  --service-account="%SA%" ^
  --memory=512Mi ^
  --cpu=1 ^
  --max-retries=3 ^
  --task-timeout=600s

echo ✅ Deployment completed for %JOB%!
echo.

REM ============================================
REM query-sales-yesterday-job
REM ============================================
echo ============================================
echo 🚀 Deploying query-sales-yesterday-job...
echo ============================================

set JOB=query-sales-yesterday-job
set DOCKERFILE=docker/Dockerfile-sales-yesterday
set IMAGE=%REGION_AR%-docker.pkg.dev/%PROJECT%/%REPO%/%JOB%:manual-%TIMESTAMP%

echo Building image for %JOB%...
gcloud builds submit --tag "%IMAGE%" --dockerfile="%DOCKERFILE%" .

echo Updating Cloud Run Job %JOB%...
gcloud run jobs update "%JOB%" ^
  --image "%IMAGE%" ^
  --region="%REGION_RUN%" ^
  --service-account="%SA%" ^
  --memory=512Mi ^
  --cpu=1 ^
  --max-retries=3 ^
  --task-timeout=600s

echo ✅ Deployment completed for %JOB%!
echo.
echo 🎉 All sales jobs deployed successfully!

